import subprocess
import time
from typing import Optional, Tuple, List, Union, Callable  # Added Callable
import openhtf as htf
from openhtf.util.configuration import CONF
from utils.command_result import CommandResult
from utils.safe_decode import safe_decode

class ADBDutControllerPlug(htf.BasePlug):

    def __init__(self) -> None:
        """Initializes the ADBDutControllerPlug.

        Initializes internal state variables
        like IP address, SSH process, and DUT ID.
        """
        super().__init__()
        self.ssh_process: Optional[subprocess.Popen] = None
        self.use_remote_adb: bool = CONF.use_remote_adb  # Correctly load from CONF
        self.device_id: Optional[str] = None  # Placeholder for device ID

    def _run_command_with_retry_and_check(
        self,
        command_executor: Callable[..., CommandResult], # Callable for either __run_adb_cmd or __remote_run_on_adb_host
        command_args: Union[List[str], str], # Can be List[str] for adb_cmd or str for remote_cmd
        expected_outputs: Union[List[str], str, None],
        command_context_name: str, # e.g., "ADB command", "Remote SSH command"
        device_id: Optional[str] = None # Only relevant for adb_cmd_executor
    ) -> CommandResult: # Changed return type
        """
        Generic helper to execute a command, retry, and check its output.

        Args:
            command_executor: The function to execute the command (e.g., self.__run_adb_cmd or self.__remote_run_on_adb_host).
                              It should return CommandResult.
            command_args: The arguments for the command executor. For __run_adb_cmd, it's List[str]. For __remote_run_on_adb_host, it's a single str.
            expected_outputs: A string or list of strings to search for in the
                              command's output upon successful execution.
            command_context_name: A descriptive name for the command context (e.g., "ADB command").
            device_id: Optional device ID for ADB commands, passed only to __run_adb_cmd.

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        expected_outputs_list = [expected_outputs] if isinstance(expected_outputs, str) else (expected_outputs or [])

        # For logging purposes, prepare a string representation of the command
        # Handle command_args differently based on the executor
        log_command_str = ""
        if command_executor == self.__run_adb_cmd:
            log_command_str = ' '.join(command_args)
        elif isinstance(command_args, str) and command_executor == self.__remote_run_on_adb_host:
            log_command_str = command_args 

        last_command_result: Optional[CommandResult] = None # Track the last result

        for i in range(CONF.max_cmd_retry):
            # Dynamically call the provided command_executor
            current_command_result: CommandResult = (
                command_executor(command_args, device_id)
                if command_executor == self.__run_adb_cmd
                else command_executor(command_args) # For __remote_run_on_adb_host, command_args is already a string
            )
            last_command_result = current_command_result # Update last result
            current_output = current_command_result.full_output  # Use full_output for checking

            if current_command_result.is_success: # Command executed successfully
                if not expected_outputs_list or any(exp in current_output for exp in expected_outputs_list): # Output validation passed
                    msg = f"{command_context_name} check for '{log_command_str}' passed on try {i+1}."
                    self.logger.debug(msg)
                    return CommandResult(is_success=True, stdout=current_command_result.stdout, stderr=current_command_result.stderr, exit_code=current_command_result.exit_code, error_message=msg)
                else: # Output validation failed, so log and continue retry
                    msg = f"{command_context_name} check for '{log_command_str}' failed on output validation on try {i+1}. Output: {current_output.strip()}"
                    self.logger.debug(msg)
            else: # Command execution itself failed
                msg = f"Execution of {command_context_name} '{log_command_str}' failed on try {i+1}. Error: {current_command_result.error_message or current_output.strip()}"
                self.logger.debug(msg)

            # If we reach here, either command failed or validation failed, so continue the retry loop
            if i < CONF.max_cmd_retry - 1:
                self.logger.debug(f"Waiting {CONF.cmd_retry_interval}s before retry...")
                time.sleep(CONF.cmd_retry_interval)
            
        # If the loop completes without returning, all retries failed.
        # Construct final CommandResult using details from the last attempt if available.
        final_error_msg = f"{command_context_name} '{log_command_str}' failed to execute or validate after {CONF.max_cmd_retry} retries."
        if last_command_result and last_command_result.error_message:
            final_error_msg += f" Last error: {last_command_result.error_message}."
        elif last_command_result and last_command_result.full_output:
             final_error_msg += f" Last output: {last_command_result.full_output.strip()}."
        
        self.logger.error(final_error_msg)
        return CommandResult(is_success=False, error_message=final_error_msg,
                             stdout=last_command_result.stdout if last_command_result else None,
                             stderr=last_command_result.stderr if last_command_result else None,
                             exit_code=last_command_result.exit_code if last_command_result else None)

    def __run_subprocess_command(
        self,
        full_command: List[str],
        timeout: int,
        context_name: str,  # For logging, e.g., "Local ADB command", "Remote SSH command"
    ) -> CommandResult:  # Changed return type
        """
        Executes a subprocess command, handles timeouts and general exceptions,
        decodes output, and returns a standardized result.

        Args:
            full_command: The command and its arguments as a list of strings.
            timeout: The maximum time in seconds to wait for the command to complete.
            context_name: A descriptive name for the command type (e.g., "Local ADB command").

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        self.logger.debug(
            f"Executing {context_name}: {' '.join(full_command)}")
        completed_process = None
        try:
            completed_process = subprocess.run(
                full_command,
                capture_output=True,
                text=False,  # Always capture raw bytes for safe_decode
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            error_msg = f"Error: {context_name} timed out after {timeout}s: {' '.join(full_command)}"
            self.logger.error(error_msg)
            return CommandResult(is_success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Error: Failed to execute {context_name}: {e}"
            self.logger.error(error_msg)
            return CommandResult(is_success=False, error_message=error_msg)

        stdout = safe_decode(
            completed_process.stdout) if completed_process.stdout else None
        stderr = safe_decode(
            completed_process.stderr) if completed_process.stderr else None
        exit_code = completed_process.returncode

        if exit_code == 0:
            self.logger.debug(
                f"{context_name} successful. Output length: {len(stdout or '')}")
            return CommandResult(is_success=True, stdout=stdout, stderr=stderr, exit_code=exit_code)
        else:
            error_msg = f"{context_name} Failed (Code: {exit_code}):\nSTDOUT: {stdout or ''}\nSTDERR: {stderr or ''}"
            self.logger.error(error_msg)
            return CommandResult(is_success=False, error_message=error_msg, stdout=stdout, stderr=stderr, exit_code=exit_code)

    def __run_adb_cmd(self, adb_command: List[str], device_id: Optional[str] = None) -> CommandResult:
        """
        Executes a general ADB command locally.
        (Refactored to use _run_subprocess_command)

        Args:
            adb_command: A list of strings representing the ADB command and its arguments.
            device_id: Optional ID of the target device. Defaults to None.

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        # Determine target device and build the full command
        target_device = device_id if device_id is not None else self.device_id

        full_command = ['adb']
        if target_device:
            full_command.extend(['-s', target_device])
        full_command.extend(adb_command)

        return self.__run_subprocess_command(full_command, CONF.adb_timeout, "Local ADB command")

    def __run_adb_cmd_and_check(self,
                                adb_command: List[str],
                                expected_outputs: Union[List[str],
                                                        str, None] = None,
                                # Changed return type
                                device_id: Optional[str] = None) -> CommandResult:
        """
        Executes an ADB command, retrying up to CONF.max_cmd_retry times and 
        checking the output for expected strings.

        (Refactored to use _run_command_with_retry_and_check)

        Args:
            adb_command: The command to execute (e.g., ['shell', 'ls', '/data']).
            expected_outputs: A string or list of strings to search for in the
                                command's stdout upon successful execution. If None, 
                                only command execution success is checked.
            device_id: Optional ID of the target device.

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        return self._run_command_with_retry_and_check(
            self.__run_adb_cmd, adb_command, expected_outputs, "ADB command", device_id
        )

    # Changed return type
    def __remote_run_on_adb_host(self, remote_cmd: str) -> CommandResult:
        """
        Executes a command on the remote ADB host via SSH.
        (Refactored to use _run_subprocess_command)

        Args:
            remote_cmd: The command string to execute on the remote host.

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        ssh_cmd = [
            "ssh",
            "-tt",
            f"{CONF.adb_host}"
        ]
        ssh_cmd.append(remote_cmd)

        # Call the generic subprocess runner
        return self.__run_subprocess_command(ssh_cmd, CONF.adb_timeout, "Remote SSH command")

    # Changed return type
    def __remote_run_on_adb_host_and_check(self, remote_cmd: str, expected_outputs: Union[List[str], str, None]) -> CommandResult:
        """
        Executes a command on the remote ADB host and checks its output.

        The command is retried up to CONF.max_cmd_retry times.

        (Refactored to use _run_command_with_retry_and_check)

        Args:
            remote_cmd: The command string to execute on the remote host.
            expected_outputs: A string or list of strings to search for in the
                              command's stdout. If any of these are found,
                              the method returns True. If None, only command
                              execution success is checked.

        Returns:
            A CommandResult object indicating success/failure and containing output details. # Updated docstring
        """
        return self._run_command_with_retry_and_check(
            self.__remote_run_on_adb_host, remote_cmd, expected_outputs, "Remote SSH command"
        )

    def adb_push(self, local_path: str, remote_path: str, device_id: Optional[str] = None, timeout: Optional[int] = None) -> CommandResult:
        """
        Executes the 'adb push' command to copy a file to the DUT.
        (Refactored to use _run_subprocess_command for execution)

        This function handles the special case where adb push writes progress/status
        messages to stderr upon success.

        Args:
            local_path: The path of the file on the local machine (host).
            remote_path: The destination path on the DUT.
            device_id: Optional ID of the target device. Defaults to the instance's dut_id.
            timeout: Optional: Timeout for the command execution in seconds. Defaults to CONF.adb_timeout.

        Returns:
            A CommandResult object indicating success/failure and containing output details.
        """
        if timeout is None:
            timeout = CONF.adb_timeout
        # If device_id is not provided, use the instance's DUT ID if available
        target_device = device_id if device_id is not None else self.device_id

        command_args = ['push', local_path, remote_path]
        full_command = ['adb']

        if target_device:
            full_command.extend(['-s', target_device])

        full_command.extend(command_args)

        # Use the generic subprocess runner
        result = self.__run_subprocess_command(
            full_command, timeout, "ADB Push command")

        if result.is_success:
            # For 'push', status messages often end up in stderr.
            # We prioritize stderr content as the primary status output.
            status_output = result.stderr or result.stdout  # Use stderr or stdout for status

            # Check for standard success indicators
            if status_output and ("pushed" in status_output or "bytes in" in status_output or "1 file pushed" in status_output):
                self.logger.debug(
                    f"Push confirmed successful: {status_output}")
                return CommandResult(is_success=True, stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code, error_message=f"Push successful: {status_output}")
            else:
                # Minimal output often indicates success but is less descriptive.
                self.logger.debug("Push successful, minimal output.")
                return CommandResult(is_success=True, stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code, error_message="Push successful, no detailed output returned.")
        else:
            # If _run_subprocess_command returned False, it means there was an execution error or timeout.
            # The 'output' already contains the error message.
            return result

    def kill_local_adb_server(self) -> CommandResult:  # Changed return type
        """Kills the local ADB server if it is running.

        This prevents conflicts when establishing an SSH tunnel for remote ADB.
        Retries up to CONF.max_cmd_retry times.

        Returns:
            A CommandResult object indicating success/failure.
        """
        for i in range(CONF.max_cmd_retry):
            result = self.__run_adb_cmd(["kill-server"])

            # Define the success condition clearly
            # ADB kill-server can return non-zero but still indicate success if server was already dead
            success_messages = ["failed to read response from server", "error: protocol fault", "daemon not running"]
            is_effectively_killed = result.is_success or any(msg in (result.stderr or "") for msg in success_messages)
            
            if is_effectively_killed:
                msg = "Local ADB server successfully terminated or was already stopped."
                self.logger.info(msg)
                return CommandResult(is_success=True, error_message=msg)

            self.logger.debug(
                f"Attempt to kill local ADB failed on try {i+1}. Error: {result.error_message}. Output: {result.full_output.strip()}")
            if i < CONF.max_cmd_retry - 1:
                time.sleep(CONF.cmd_retry_interval)

        final_error_msg = f"Failed to kill local ADB server after {CONF.max_cmd_retry} retries. Last error: {result.error_message}. Last output: {result.full_output.strip()}"
        self.logger.error(final_error_msg)
        return CommandResult(is_success=False, error_message=final_error_msg, stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)

    # Changed return type
    def setup_port_forwarding_to_adb_host(self) -> CommandResult:
        """Sets up an SSH tunnel for port forwarding to the ADB host.

        This allows local ADB commands to communicate with a remote ADB server.
        The method blocks until the tunnel is established or a timeout occurs.

        Returns:
            A CommandResult object indicating success/failure.
        """
        self.logger.info(
            f"Starting SSH tunnel to {CONF.adb_host} on port {CONF.adb_host_port}")
        ssh_port_forwarding = ["ssh",
                               "-vN",
                               "-L",
                               f"{CONF.adb_host_port}:localhost:{CONF.adb_host_port}",
                               f"{CONF.adb_host}"
                               ]
        ssh_tunnel_start_time = time.time()

        self.ssh_process = subprocess.Popen(
            # Added text=False
            ssh_port_forwarding, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        time.sleep(2)  # Wait 2 seconds for initial tunnel setup

        last_result: Optional[CommandResult] = None
        while time.time() - ssh_tunnel_start_time < CONF.remote_cmd_timeout:
            result = self.__run_adb_cmd(["devices"])  # Get CommandResult
            last_result = result

            if result.is_success and "device" in result.full_output:
                msg = f"SSH tunnel active with pid: {self.ssh_process.pid}. ADB devices list verified."
                self.logger.info(msg)
                return CommandResult(is_success=True, error_message=msg)

            self.logger.debug(
                f"ADB check failed. Error: {result.error_message}. Output: {result.full_output.strip()}")
            time.sleep(1)  # Wait before retrying ADB check

        final_error_msg = "SSH tunnel setup failed: ADB verification timed out."
        self.logger.error(final_error_msg)
        
        # Streamlined return, using last_result attributes directly if available
        if last_result:
            return CommandResult(is_success=False, error_message=final_error_msg,
                                 stdout=last_result.stdout, stderr=last_result.stderr, exit_code=last_result.exit_code)
        else:
            return CommandResult(is_success=False, error_message=final_error_msg)

    def restart_remote_adb(self) -> CommandResult:  # Changed return type
        """Restarts the ADB server on the remote host.

        It first attempts to kill any running remote ADB server and then starts a new one.

        Returns:
            A CommandResult object indicating success/failure.
        """
        self.logger.info("Attempting to kill remote ADB server.")
        # We don't need to check the result here for success, as the start command will fail if it's still running
        kill_result = self.__remote_run_on_adb_host_and_check(
            "adb kill-server", ["cannot connect to daemon", "error: protocol fault"])
        if not kill_result.is_success:
            self.logger.debug(
                f"Remote ADB server kill attempt indicated failure or not running: {kill_result.error_message}")

        self.logger.info("Attempting to start remote ADB server.")
        start_result = self.__remote_run_on_adb_host_and_check(
            "adb start-server", "daemon started successfully")

        if start_result.is_success:
            self.logger.debug("Remote ADB server started successfully.")
            return CommandResult(is_success=True, error_message="Remote ADB server started successfully.")
        else:
            final_error_msg = f"Failed to start remote ADB server after retries. Last error: {start_result.error_message}. Last output: {start_result.full_output.strip()}"
            self.logger.error(final_error_msg)
            return CommandResult(is_success=False, error_message=final_error_msg, stdout=start_result.stdout, stderr=start_result.stderr, exit_code=start_result.exit_code)

    def provision_via_adb(self) -> CommandResult:  # Changed return type
        """Provisions the DUT using ADB commands executed via the remote ADB host.

        This method first kills any local ADB server, sets up SSH port forwarding
        to the remote ADB host, restarts the remote ADB server, and then
        processes the list of connected devices to identify the DUT.

        Returns:
            A CommandResult object indicating success/failure.
        """
        # Kill any lingering local server that will not allow us to bind to adb port
        if self.use_remote_adb:
            self.logger.info("Using remote ADB host for provisioning.")

            kill_result = self.kill_local_adb_server()
            if not kill_result.is_success:
                self.logger.error(
                    f"Provisioning failed: {kill_result.error_message}")
                return kill_result  # Propagate the detailed failure

            restart_result = self.restart_remote_adb()
            if not restart_result.is_success:
                self.logger.error(
                    f"Provisioning failed: {restart_result.error_message}")
                return restart_result  # Propagate the detailed failure

            ssh_setup_result = self.setup_port_forwarding_to_adb_host()
            if not ssh_setup_result.is_success:
                self.logger.error(
                    f"Provisioning failed: {ssh_setup_result.error_message}")
                return ssh_setup_result  # Propagate the detailed failure
        else:
            self.logger.info(
                "Local ADB provisioning in use (remote ADB host not configured).")

        # Verify adb works and get DUT ID
        list_devices_result = self.__run_adb_cmd(["devices", "-l"])

        if not list_devices_result.is_success:
            self.logger.error(f"Provisioning failed: {list_devices_result.error_message}")
            return list_devices_result # Directly return the CommandResult, as it contains full details

        self.logger.debug(
            f"ADB devices list: {list_devices_result.full_output}")
        # This method updates self.dut_id internally
        self.get_device_id(list_devices_result.full_output)

        if self.device_id:
            info_msg = f"Provisioning successful. DUT ID identified: {self.device_id}"
            self.logger.info(info_msg)
            return CommandResult(is_success=True, error_message=info_msg)

        error_msg = "No valid DUT ID could be extracted from the device list."
        self.logger.error(f"Provisioning failed: {error_msg}")
        return CommandResult(is_success=False, error_message=error_msg, stdout=list_devices_result.stdout, stderr=list_devices_result.stderr, exit_code=list_devices_result.exit_code)

    def get_device_id(self, adb_device_list: str) -> str:
        """Processes the output of 'adb devices -l' to extract the DUT ID.

        Args:
            adb_device_list: A string containing the output from the 'adb devices -l' command.

        Returns:
            The DUT ID as a string if found, otherwise an empty string.
        """
        device_list = [line.strip()
                       for line in adb_device_list.splitlines() if line.strip()]
        if len(device_list) > 1:  # First line is "list of devices attached" so skip that
            dut_ids = [line.split(" ")[0] for line in device_list[1:]]
            if len(dut_ids) == 1:
                self.device_id = dut_ids[0]
        return self.device_id if self.device_id else ""

    def tearDown(self) -> None:
        """Tears down the SSH process if it is active.

        This method is intended for cleanup, ensuring that any open SSH connections
        are properly terminated.
        """
        if self.ssh_process:
            self.ssh_process.kill()
