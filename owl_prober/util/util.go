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
	err := os.WriteFile(path, []byte(value), os.FileMode(os.O_WRONLY))
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
