package util

import (
	"fmt"
	"log/slog"
	"os"
	"path"
	"strconv"
	"sync" // Added for mutex

	pb "owl_test_agent/proto" // Imported proto
)

var (
	configuredBatterySettings *pb.BatterySettings // Stores the battery settings configured via gRPC
	batteryMu                 sync.RWMutex        // Mutex to protect access to configuredBatterySettings
)

type BatteryDetails struct {
	// DeviceName is used in the local functions, but configuration comes from configuredBatterySettings
	// This struct is primarily used internally by GetBatteryReadings before converting to pb.GetBatteryReadingsResponse
	DeviceName  string
	Present     bool
	Millivolts  int64 // Changed from MillVolts
	Milliamps   int64 // Changed from MillAmps
	Temperature float32
}

const BATTERY_DEVICES_PATH = "/sys/class/power_supply"

// SetupBattery configures the battery settings.
func SetupBattery(settings *pb.BatterySettings) error {
	batteryMu.Lock()
	defer batteryMu.Unlock()
	configuredBatterySettings = settings
	slog.Info("Battery settings configured", "deviceName", settings.DeviceName)
	return nil
}

// readBatterySysfsValues reads raw battery values from sysfs based on the provided settings.
func readBatterySysfsValues(settings *pb.BatterySettings) (millivolts int64, milliamps int64, temperature float32, present bool, status string, err error) {
	bat_sysfs_path := path.Join(BATTERY_DEVICES_PATH, settings.DeviceName)

	// Check if battery is present
	file, err := os.Stat(bat_sysfs_path)
	if err != nil {
		return 0, 0, 0, false, "Error", err
	}
	if !file.IsDir() {
		return 0, 0, 0, false, "Error", fmt.Errorf("sysfs entry is not a directory: %s", bat_sysfs_path)
	}

	presence_str, err := readSysfsValue(path.Join(bat_sysfs_path, "present"))
	if err != nil || presence_str != "1" {
		return 0, 0, 0, false, "Not Present", nil // Not present or error reading presence
	}
	present = true

	// Read status
	status_str, err := readSysfsValue(path.Join(bat_sysfs_path, "status"))
	if err != nil {
		slog.Warn("unable to read battery status", "error", err)
		status = "Unknown"
	} else {
		status = status_str
	}

	// Read voltage
	voltageNode := "voltage_now"
	if settings.VoltageNode != "" {
		voltageNode = settings.VoltageNode
	}
	voltage_microv_str, err := readSysfsValue(path.Join(bat_sysfs_path, voltageNode))
	if err != nil {
		slog.Error("unable to read voltage from battery", "error", err)
		return 0, 0, 0, present, status, err
	}
	millivolts, err = strconv.ParseInt(voltage_microv_str, 10, 64)
	if err != nil {
		slog.Error("unable to parse battery voltage", "error", err)
		return 0, 0, 0, present, status, err
	}
	millivolts = millivolts / 1000 // Convert microvolts to millivolts

	// Read current
	currentNode := "current_now"
	if settings.CurrentNode != "" {
		currentNode = settings.CurrentNode
	}
	current_microamp_str, err := readSysfsValue(path.Join(bat_sysfs_path, currentNode))
	if err != nil {
		slog.Error("unable to read current from battery", "error", err)
		return 0, 0, 0, present, status, err
	}
	milliamps, err = strconv.ParseInt(current_microamp_str, 10, 64)
	if err != nil {
		slog.Error("unable to parse battery current", "error", err)
		return 0, 0, 0, present, status, err
	}
	milliamps = milliamps / 1000 // Convert microamps to milliamps

	// Read temperature
	tempNode := "temp"
	if settings.TempNode != "" {
		tempNode = settings.TempNode
	}
	temp_str, err := readSysfsValue(path.Join(bat_sysfs_path, tempNode))
	if err != nil {
		slog.Error("unable to read temperature from battery", "error", err)
		return 0, 0, 0, present, status, err
	}
	temp_deciCelcius, err := strconv.Atoi(temp_str)
	if err != nil {
		slog.Error("unable to parse battery temperature", "error", err)
		return 0, 0, 0, present, status, err
	}
	temperature = float32(temp_deciCelcius) / 10 // Convert deciCelsius to Celsius

	return millivolts, milliamps, temperature, present, status, nil
}

// GetBatteryReadings retrieves the current battery readings based on configured settings.
func GetBatteryReadings() (*pb.GetBatteryReadingsResponse, error) {
	batteryMu.RLock() // Use RLock for reading settings
	settings := configuredBatterySettings
	batteryMu.RUnlock()

	if settings == nil {
		return nil, fmt.Errorf("battery settings not configured. Please call ConfigureBattery first")
	}

	millivolts, milliamps, temperature, present, status, err := readBatterySysfsValues(settings)
	if err != nil {
		return nil, err
	}

	response := &pb.GetBatteryReadingsResponse{
		Millivolts:         0,
		Milliamps:          0,
		CelsiusTemperature: 0,
		Present:            false,
		Status:             "Not Present",
	}

	if present {
		response.Millivolts = float32(millivolts)
		response.Milliamps = float32(milliamps)
		response.CelsiusTemperature = temperature
		response.Present = present
		response.Status = status
	}

	return response, nil
}
