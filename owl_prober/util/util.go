package util

import (
	"bytes"
	"fmt"
	"log"
	"log/slog"
	"os"
	"os/exec"
	"strings"
	"time"
	"unicode/utf8"
)

func GetWLANMacIp(if_name string) (string, string, error) {
	cmd_args := make([]string, 0)
	cmd_args = append(cmd_args, if_name)
	stdout, _, err := RunShellCommandOnDevice("ifconfig", cmd_args, 3*time.Second, "", "", false)
	if err != nil {
		slog.Error("cannot run ifconfig : ", "error", err.Error())
		return "", "", err
	}
	macaddr := selectAfterSubstring(stdout, "HWaddr", "\n")
	ipaddr := selectAfterSubstring(stdout, "inet addr:", "\n ")
	return macaddr, ipaddr, nil
}

func selectAfterSubstring(s string, substr string, delimiter string) string {
	idx := strings.Index(s, substr)
	var mac_addr strings.Builder
	if idx > 0 {
		idx += utf8.RuneCountInString(substr)
		for idx < utf8.RuneCountInString(s) {
			if strings.ContainsAny(string(s[idx]), delimiter) {
				break
			}
			mac_addr.WriteString(string(s[idx]))
			idx++
		}
		return strings.Trim(mac_addr.String(), " \r\n")
	}
	return ""
}

// RunShellCommandOnDevice executes a local shell command on the device.
func RunShellCommandOnDevice(command string, args []string, timeout time.Duration, stdinData string, workingDirectory string, useShell bool) (string, string, error) {
	// Set default timeout if 0 is provided
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	var cmd *exec.Cmd
	if useShell {
		fullCommand := command
		if len(args) > 0 {
			fullCommand += " " + strings.Join(args, " ")
		}
		cmd = exec.Command("sh", "-c", fullCommand) // Changed to sh -c for portability
	} else {
		cmd = exec.Command(command, args...)
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if stdinData != "" {
		cmd.Stdin = strings.NewReader(stdinData)
	}

	if workingDirectory != "" {
		cmd.Dir = workingDirectory
	}

	timer := time.AfterFunc(timeout, func() {
		if cmd.Process != nil {
			log.Printf("Command %s %v timed out, killing process.", command, args)
			// It's better to send a signal to the process group to ensure all child processes are killed
			// For simplicity, using Kill() on the main process for now.
			cmd.Process.Kill()
		}
	})
	defer timer.Stop()

	err := cmd.Run() // Use cmd.Run() for simple command execution
	stdoutStr := strings.TrimSpace(stdout.String())
	stderrStr := strings.TrimSpace(stderr.String())

	if err != nil {
		return stdoutStr, stderrStr, fmt.Errorf("command '%s %v' failed: %w, stderr: %s", command, args, err, stderrStr)
	}
	return stdoutStr, stderrStr, nil
}

// readSysfsValue reads the content of a sysfs file.
func readSysfsValue(path string) (string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read sysfs file %s: %w", path, err)
	}
	return strings.TrimSpace(string(content)), nil
}

// writeSysfsValue writes a string value to a sysfs file.
func writeSysfsValue(path, value string) error {
	err := os.WriteFile(path, []byte(value), 0644) // Changed FileMode to 0644 for write permissions
	if err != nil {
		return fmt.Errorf("failed to write to sysfs file %s: %w", path, err)
	}
	return nil
}

// RunShellCommandOnDeviceGRPC is a gRPC-compatible wrapper for RunShellCommandOnDevice.
func RunShellCommandOnDeviceGRPC(command string, args []string, timeoutSeconds int32, stdinData string, workingDirectory string, useShell bool) (stdout string, stderr string, exitCode int32, errorMessage string) {
	timeout := time.Duration(timeoutSeconds) * time.Second
	out, errs, err := RunShellCommandOnDevice(command, args, timeout, stdinData, workingDirectory, useShell)

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			// Command exited with a non-zero status
			return out, errs, int32(exitErr.ExitCode()), err.Error()
		}
		// Other execution error (e.g., command not found, timeout - which is handled by timer)
		return out, errs, -1, err.Error() // Use -1 for non-exit errors or specific error codes
	}
	// Command executed successfully (exit code 0)
	return out, errs, 0, ""
}

// SetLEDColor sets the brightness values and blink rates for RGB LEDs via sysfs.
// It assumes LED sysfs directories are under /sys/class/leds/
func SetLEDColor(redLedName, greenLedName, blueLedName string, redVal, greenVal, blueVal int32, redBlinkRate, greenBlinkRate, blueBlinkRate int32) error {
	basePath := "/sys/class/leds/"

	// Helper function to set LED brightness and trigger
	setLED := func(ledName string, value int32, blinkRate int32) error {
		if ledName == "" {
			return nil // No path provided, skip this LED
		}
		sysfsPath := fmt.Sprintf("%s%s", basePath, ledName)

		// Set trigger
		triggerPath := fmt.Sprintf("%s/trigger", sysfsPath)
		if blinkRate > 0 {
			// Set trigger to timer and configure delays
			if err := writeSysfsValue(triggerPath, "timer"); err != nil {
				return fmt.Errorf("failed to set trigger for %s to timer: %w", ledName, err)
			}
			delayOnPath := fmt.Sprintf("%s/delay_on", sysfsPath)
			delayOffPath := fmt.Sprintf("%s/delay_off", sysfsPath)

			// Calculate delays in milliseconds
			if blinkRate == 0 { 
				blinkRate = 1 // Defensive: avoid division by zero if somehow passed 0 for blinking
			}
			periodMs := 1000 / blinkRate
			delayOn := periodMs / 2
			delayOff := periodMs / 2

			if err := writeSysfsValue(delayOnPath, fmt.Sprintf("%d", delayOn)); err != nil {
				return fmt.Errorf("failed to set delay_on for %s: %w", ledName, err)
			}
			if err := writeSysfsValue(delayOffPath, fmt.Sprintf("%d", delayOff)); err != nil {
				return fmt.Errorf("failed to set delay_off for %s: %w", ledName, err)
			}
		} else {
			// Set trigger to 'none' for solid color
			if err := writeSysfsValue(triggerPath, "none"); err != nil {
				slog.Warn(fmt.Sprintf("failed to set trigger for %s to none: %v. Continuing without trigger.", ledName, err))
			}
		}

		// Set brightness value
		brightnessPath := fmt.Sprintf("%s/brightness", sysfsPath)
		if err := writeSysfsValue(brightnessPath, fmt.Sprintf("%d", value)); err != nil {
			return fmt.Errorf("failed to set brightness for %s: %w", ledName, err)
		}
		return nil
	}

	if err := setLED(redLedName, redVal, redBlinkRate); err != nil {
		return err
	}
	if err := setLED(greenLedName, greenVal, greenBlinkRate); err != nil {
		return err
	}
	if err := setLED(blueLedName, blueVal, blueBlinkRate); err != nil {
		return err
	}

	return nil
}
