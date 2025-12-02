package util

import (
	"bytes"
	"fmt"
	"io/ioutil" // Using ioutil for ReadFile/WriteFile as os.ReadFile/WriteFile requires Go 1.16+
	"log"
	"os/exec"
	"strings"
	"time"
)

// RunShellCommandOnDevice executes a local shell command on the device.
func RunShellCommandOnDevice(command string, args []string, timeout time.Duration) (string, string, error) {
	cmd := exec.Command(command, args...)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	timer := time.AfterFunc(timeout, func() {
		if cmd.Process != nil {
			log.Printf("Command %s %v timed out, killing process.", command, args)
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
	content, err := ioutil.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read sysfs file %s: %w", path, err)
	}
	return strings.TrimSpace(string(content)), nil
}

// writeSysfsValue writes a string value to a sysfs file.
func writeSysfsValue(path, value string) error {
	err := ioutil.WriteFile(path, []byte(value), 0644) // 0644 is standard file permission
	if err != nil {
		return fmt.Errorf("failed to write to sysfs file %s: %w", path, err)
	}
	return nil
}

// Helper to get min of two ints
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
