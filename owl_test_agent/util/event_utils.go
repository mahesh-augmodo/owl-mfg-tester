package util

import (
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/holoplot/go-evdev"
)

// DeviceInfo holds general event device information and its supported EV_ABS axes.
type DeviceInfo struct {
	DeviceName   string
	SysfsPath    string
	DeviceType   string
	AbsAxisCodes []string
}

func FindInputDevices() ([]DeviceInfo, error) {
	devices_found := make([]DeviceInfo, 0)

	devicePaths, err := evdev.ListDevicePaths()
	if err != nil {
		return devices_found, err
	}

	for _, device := range devicePaths {
		dev, err := evdev.Open(device.Path)
		if err != nil {
			// Log and continue instead of failing the entire function
			slog.Info(fmt.Sprintf("Warning: unable to open event device %s : %v", device.Path, err))
			continue
		}

		slog.Info(fmt.Sprintf("Found an input event device %s with dev file: %s", device.Name, device.Path))

		// Get all supported EV_ABS axes codes
		abs_codes := dev.CapableEvents(evdev.EV_ABS)

		if len(abs_codes) == 0 {
			deviceType := ""
			ev_types := dev.CapableEvents(evdev.EV_KEY)

			if len(ev_types) > 0 {
				deviceType = "key"
			}

			slog.Info(fmt.Sprintf("DeviceType: %s", deviceType))
			// Populate the DeviceInfo struct
			info := DeviceInfo{
				DeviceName:   device.Name,
				SysfsPath:    device.Path,
				DeviceType:   deviceType,
				AbsAxisCodes: make([]string, 0),
			}
			// Add to the map
			devices_found = append(devices_found, info)
			continue
		}

		deviceType := "accelerometer"
		slog.Info(fmt.Sprintf("DeviceType: %s", deviceType))
		slog.Info("Device reports EV_ABS capabilites for axes:")

		// Convert the slice of EvCode into the structured slice
		var abs_axis_list []string
		for _, code := range abs_codes {
			axisName := evdev.ABSToString[code]
			slog.Info(fmt.Sprintf("Code: %x, Axis : %s", code, axisName))

			abs_axis_list = append(abs_axis_list, axisName)
		}

		// Populate the DeviceInfo struct
		info := DeviceInfo{
			DeviceName:   device.Name,
			SysfsPath:    device.Path,
			DeviceType:   deviceType,
			AbsAxisCodes: abs_axis_list,
		}

		// Add to the map
		devices_found = append(devices_found, info)
	}

	return devices_found, nil
}

func CountEventsOverDuration(sysfs_path string, duration int) (string, error) {
	dev, err := evdev.Open(sysfs_path)
	var event_report strings.Builder
	if err != nil {
		return event_report.String(), fmt.Errorf("unable to open device file: %w", err)
	}
	// Since we can't set SetReadDuration on the underlying file object
	// we are going to use a go routine and a channel from a timer.
	timerDone := make(chan bool)
	go func() {
		select {
		case <-time.After(time.Duration(duration) * time.Second):
			dev.Close()
		case <-timerDone:
			return
		}
	}()

	for {

		event, err := dev.ReadOne()

		if err != nil {
			if strings.Contains(err.Error(), "file already closed") || strings.Contains(err.Error(), "bad file descriptor") {
				break // We hit the timeout
			}

			// If it's a different error, we report it.
			// (Only return error if we haven't already finished via timeout)
			select {
			case <-time.After(0):
				// Check if we effectively timed out just now
				break
			default:
				// Genuine hardware error
				close(timerDone) // Stop the timer goroutine
				return event_report.String(), fmt.Errorf("error reading event: %v", err)
			}
		}
		// Ignore SYN packets that are terminators.
		if (event.Type != evdev.EV_SYN) && (event.Code != evdev.SYN_REPORT) {
			event_report.WriteString(fmt.Sprintf("Time : %d.%06d, Code: %s, Type: %s, Value: %d\n", event.Time.Sec, event.Time.Usec,
				evdev.CodeName(event.Type, event.Code), evdev.EVToString[event.Type], event.Value))
		}
	}
	return event_report.String(), nil
}
