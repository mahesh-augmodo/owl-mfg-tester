package util

import (
	"bufio"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"

	pb "owl_prober/proto" // Added for protobuf messages

	"github.com/prometheus/procfs"
)

func GetCPUInfoSerial() (string, error) {
	file, err := os.Open("/proc/cpuinfo")
	if err != nil {
		return "", fmt.Errorf("unable to open /proc/cpuinfo %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "Serial") {
			parts := strings.Split(line, ":")

			if len(parts) > 1 {
				serial := strings.TrimSpace(parts[1])
				return serial, nil
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("error reading /proc/cpuinfo %w", err)
	}

	return "", fmt.Errorf("serial not found in /proc/cpuinfo")

}

func GetCPUTemperature(sysfsPath string) (float32, error) {
	temp_str, err := readSysfsValue(sysfsPath)
	if err != nil {
		slog.Error("unable to read CPU temperature", "error", err)
		return 0, err // Return error
	}
	cpu_temp, err := strconv.Atoi(temp_str)
	if err != nil {
		slog.Error("unable to parse CPU temperature", "error", err) // Changed log message
		return 0, err                                               // Return error
	}
	return (float32(cpu_temp) / 1e3), nil // Convert to Celsius from millicelsius
}

// GetCPUIdlePercentage measures the CPU idle percentage over a specified duration.
func GetCPUIdlePercentage(duration time.Duration) (float64, error) {
	// Helper function to get current total and idle times (in clock ticks/jiffies).
	// Returns float64 to match the assumed type of the procfs fields in your environment.
	getCurrentCPUTimes := func() (idle, total float64, err error) {
		fs, err := procfs.NewDefaultFS()
		if err != nil {
			return 0, 0, fmt.Errorf("failed to open procfs: %w", err)
		}
		stat, err := fs.Stat()
		if err != nil {
			return 0, 0, fmt.Errorf("failed to read /proc/stat: %w", err)
		}

		// We need the aggregate CPU stats, which is in the CPU slice (index 0)
		if len(stat.CPU) == 0 {
			return 0, 0, fmt.Errorf("no aggregate CPU stats found")
		}

		// This variable now correctly holds a single procfs.CPUStat struct
		cpuStat := stat.CPU[0]

		// IMPORTANT: Since your compiler says the sum results in float64,
		// we keep the return variables (idle, total) as float64.
		total = cpuStat.User + cpuStat.Nice + cpuStat.System + cpuStat.Idle +
			cpuStat.Iowait + cpuStat.IRQ + cpuStat.SoftIRQ + cpuStat.Steal +
			cpuStat.Guest + cpuStat.GuestNice

		idle = cpuStat.Idle + cpuStat.Iowait

		return idle, total, nil
	}

	// Sample 1
	idle0, total0, err := getCurrentCPUTimes()
	if err != nil {
		return 0, err
	}

	// Wait for the specified duration
	time.Sleep(duration)

	// Sample 2
	idle1, total1, err := getCurrentCPUTimes()
	if err != nil {
		return 0, err
	}

	// Calculate deltas
	idleDelta := idle1 - idle0
	totalDelta := total1 - total0

	if totalDelta <= 0 {
		return 0, fmt.Errorf("total CPU time delta is zero or negative, cannot calculate usage")
	}

	// Calculate percentage
	idlePercentage := (idleDelta / totalDelta) * 100.0

	return idlePercentage, nil
}

func GetAvailableSystemMemory() (uint64, error) {
	// 1. Initialize procfs filesystem access
	fs, err := procfs.NewDefaultFS()
	if err != nil {
		return 0, fmt.Errorf("failed to open procfs: %w", err)
	}

	// 2. Read and parse the memory information (/proc/meminfo)
	memInfo, err := fs.Meminfo()
	if err != nil {
		return 0, fmt.Errorf("failed to read /proc/meminfo: %w", err)
	}

	return *memInfo.MemTotal, nil
}

// GetCPULoadAverage retrieves the 1-minute load average using procfs.
func GetCPULoadAverage() (float32, error) {
	fs, err := procfs.NewDefaultFS()
	if err != nil {
		return 0, fmt.Errorf("failed to open procfs: %w", err)
	}

	load, err := fs.LoadAvg()
	if err != nil {
		return 0, fmt.Errorf("failed to read /proc/loadavg: %w", err)
	}

	return float32(load.Load1), nil // Return the 1-minute load average
}

// GetSystemState gathers various system-related information.
func GetSystemState(idleDurationSeconds int32, cpuTempSysfsPath string) (*pb.GetSystemStateResponse, error) {
	resp := &pb.GetSystemStateResponse{}

	// Get serial
	serial, err := GetCPUInfoSerial()
	if err != nil {
		slog.Warn("Failed to get CPU serial", "error", err)
		resp.Serial = "Unknown"
	} else {
		resp.Serial = serial
	}

	// Get CPU temperature in Celsius
	temp, err := GetCPUTemperature(cpuTempSysfsPath)
	if err != nil {
		slog.Warn("Failed to get CPU temperature", "error", err)
		resp.CpuTemperature = 0 // Default or error value
	} else {
		resp.CpuTemperature = temp
	}

	// Get CPU idle percentage
	idleDuration := time.Duration(idleDurationSeconds) * time.Second
	if idleDurationSeconds > 0 { // Only calculate if duration is positive
		idlePct, err := GetCPUIdlePercentage(idleDuration)
		if err != nil {
			slog.Warn("Failed to get CPU idle percentage", "error", err)
			resp.CpuIdlePercent = 0 // Default or error value
		} else {
			resp.CpuIdlePercent = float32(idlePct)
		}
	}

	// Get total memory
	totalMem, err := GetAvailableSystemMemory()
	if err != nil {
		slog.Warn("Failed to get total system memory", "error", err)
		resp.TotalMemoryKb = 0 // Default or error value
	} else {
		resp.TotalMemoryKb = totalMem
	}

	// Get CPU load average
	loadAvg, err := GetCPULoadAverage()
	if err != nil {
		slog.Warn("Failed to get CPU load average", "error", err)
		resp.CpuLoadAverage = 0 // Default or error value
	} else {
		resp.CpuLoadAverage = loadAvg
	}

	return resp, nil
}
