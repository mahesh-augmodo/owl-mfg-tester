package util

import (
	"fmt"
	"log/slog"
	"sync" // Added for mutex

	pb "owl_test_agent/proto" // Added for protobuf messages
)

var (
	configuredBuzzerSettings *pb.BuzzerSettings // Stores the buzzer settings configured via gRPC
	buzzerMu                 sync.RWMutex       // Mutex to protect access to configuredBuzzerSettings
)

// ConfigureBuzzer sets the device path for the buzzer.
func ConfigureBuzzer(settings *pb.BuzzerSettings) error {
	buzzerMu.Lock()
	defer buzzerMu.Unlock()
	configuredBuzzerSettings = settings
	slog.Info("Buzzer configured", "devicePath", settings.DevicePath)
	return nil
}

// SetBuzzer turns the buzzer on or off using the configured device path.
func SetBuzzer(on bool) error {
	buzzerMu.RLock() // Use RLock for reading settings
	settings := configuredBuzzerSettings
	buzzerMu.RUnlock()

	if settings == nil {
		return fmt.Errorf("buzzer not configured. Please call ConfigureBuzzer first")
	}

	write_val := "0"
	if on {
		write_val = "1"
	}

	err := writeSysfsValue(settings.DevicePath, write_val)
	if err != nil {
		slog.Error("unable to write to buzzer", "devicePath", settings.DevicePath, "error", err)
		return err
	}
	slog.Info("Buzzer state set", "on", on, "devicePath", settings.DevicePath)
	return nil
}
