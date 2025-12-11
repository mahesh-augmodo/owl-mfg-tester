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
	stdout, _, err := RunShellCommandOnDevice("ifconfig", cmd_args, 3)
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
	content, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read sysfs file %s: %w", path, err)
	}
	return strings.TrimSpace(string(content)), nil
}

// writeSysfsValue writes a string value to a sysfs file.
func writeSysfsValue(path, value string) error {
	err := os.WriteFile(path, []byte(value), os.FileMode(os.O_WRONLY))
	if err != nil {
		return fmt.Errorf("failed to write to sysfs file %s: %w", path, err)
	}
	return nil
}
