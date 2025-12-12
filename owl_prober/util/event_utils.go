package util

import (
	"bytes"
	"encoding/csv"
	"fmt"
	"log/slog"
	"strings"
	"time"

	pb "owl_prober/proto" // Added for protobuf messages

	"github.com/holoplot/go-evdev"
)

// DeviceInfo holds general event device information and its supported EV_ABS axes.
func DiscoverEventDevices() ([]*pb.EventDevice, error) {
	pbDevicesFound := make([]*pb.EventDevice, 0)

	devicePaths, err := evdev.ListDevicePaths()
	if err != nil {
		return pbDevicesFound, err
	}

	for _, device := range devicePaths {
		dev, err := evdev.Open(device.Path)
		if err != nil {
			slog.Info(fmt.Sprintf("Warning: unable to open event device %s : %v", device.Path, err))
			continue
		}
		defer dev.Close() // Close device when done

		slog.Info(fmt.Sprintf("Found an input event device %s with dev file: %s", device.Name, device.Path))

		deviceType := ""
		// Determine device type
		if len(dev.CapableEvents(evdev.EV_ABS)) > 0 {
			deviceType = "accelerometer" // Assuming EV_ABS implies accelerometer
		} else if len(dev.CapableEvents(evdev.EV_KEY)) > 0 {
			deviceType = "key" // Assuming EV_KEY implies key device
		}

		devName, err := dev.Name() // Call the Name() method
		if err != nil {
			slog.Warn(fmt.Sprintf("unable to get device name for %s: %v", device.Path, err))
			devName = "Unknown" // Default to "Unknown" or handle error as appropriate
		}

		pbDevicesFound = append(pbDevicesFound, &pb.EventDevice{
			DeviceName: devName, // Use the string value			DevicePath: dev.Fn, // Fn is the device file path like /dev/input/event0
			DeviceType: deviceType,
			SysfsPath:  dev.Path(), // Path is the sysfs path like /sys/class/input/event0
		})
	}
	return pbDevicesFound, nil
}

func GetEventReportOverDuration(devicePath string, duration int32) (string, error) {
	dev, err := evdev.Open(devicePath)
	if err != nil {
		return "", fmt.Errorf("unable to open device file %s: %w", devicePath, err)
	}
	defer dev.Close()

	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)

	// Write CSV header
	header := []string{"Timestamp_FloatSec", "EventType", "EventCode", "EventValue"}
	if err := writer.Write(header); err != nil {
		return "", fmt.Errorf("error writing CSV header: %w", err)
	}

	timerDone := make(chan bool)
	go func() {
		select {
		case <-time.After(time.Duration(duration) * time.Second):
			dev.Close() // Close device to unblock ReadOne
		case <-timerDone:
			return
		}
	}()

	for {
		event, err := dev.ReadOne()

		if err != nil {
			if strings.Contains(err.Error(), "file already closed") || strings.Contains(err.Error(), "bad file descriptor") {
				break // We hit the timeout or device was closed
			}

			// If it's a different error, report it.
			select {
			case <-timerDone: // Already signaled to stop
				break
			default: // Genuine hardware error
				close(timerDone) // Stop the timer goroutine
				return "", fmt.Errorf("error reading event from %s: %w", devicePath, err)
			}
		}

		// Ignore SYN packets that are terminators.
		if event.Type == evdev.EV_SYN && event.Code == evdev.SYN_REPORT {
			continue
		}

		record := []string{
			fmt.Sprintf("%d.%06d", event.Time.Sec, event.Time.Usec),
			evdev.EVToString[event.Type],
			evdev.CodeName(event.Type, event.Code),
			fmt.Sprintf("%d", event.Value),
		}
		if err := writer.Write(record); err != nil {
			slog.Error("error writing CSV record", "error", err)
			close(timerDone)
			return "", fmt.Errorf("error writing event record to CSV: %w", err)
		}
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		return "", fmt.Errorf("error flushing CSV writer: %w", err)
	}
	return buf.String(), nil
}
