import subprocess
import time
import requests
import openhtf as htf
from openhtf.util.configuration import CONF

class DutControllerPlug(htf.BasePlug):
    """Manages connectivity with a Device Under Test (DUT).

    This plug provides methods for provisioning, connecting to, and tearing down
    the DUT, primarily via ADB commands executed remotely on an ADB host.
    It handles SSH port forwarding for remote ADB access and manages DUT-specific
    parameters like its IP address and ID.
    """

    def __init__(self) -> None:
        """Initializes the DutControllerPlug.

        Sets up the session for HTTP requests (disabling SSL verification for testing),
        configures the DUT port, and initializes internal state variables
        like IP address, SSH process, and DUT ID.
        """
        super().__init__()
        self.ip_address = None
        self.session = requests.Session()
        # Allows us to use self signed certificates for test.
        self.session.verify = False
        self.port = CONF.dut_port
        self.ssh_process = None
        self.use_remote_adb = CONF.use_remote_adb

        # DUT Parameters
        self.dut_id = None

    def __run_adb_cmd(self, adb_command: list[str]) -> subprocess.CompletedProcess:
        """Executes an ADB command locally.

        Args:
            adb_command: A list of strings representing the ADB command and its arguments.

        Returns:
            A subprocess.CompletedProcess object containing the result of the command.
        """
        return subprocess.run(
            adb_command, capture_output=True, text=True)

    def __remote_run_on_adb_host(self, remote_cmd: str) -> subprocess.CompletedProcess:
        """Executes a command on the remote ADB host via SSH.
        Args:
            remote_cmd: The command string to execute on the remote host.

        Returns:
            A subprocess.CompletedProcess object containing the result of the command.
        """
        ssh_cmd = [
            "ssh",
            "-tt",
            f"{CONF.adb_host}"
        ]
        ssh_cmd.append(remote_cmd)
        self.logger.debug(
            f"Remote CMD: Running {remote_cmd} on {CONF.adb_host}")
        ssh_run = subprocess.run(ssh_cmd, capture_output=True, text=True)
        return ssh_run

    def __remote_run_on_adb_host_and_check(self, remote_cmd: str, expected_outputs: list[str] | str = None) -> bool:
        """Executes a command on the remote ADB host and checks its output.

        The command is retried up to CONF.max_cmd_retry times.

        Args:
            remote_cmd: The command string to execute on the remote host.
            expected_outputs: A string or list of strings to search for in the
                              command's stdout. If any of these are found,
                              the method returns True. If None, only command
                              execution success is checked.

        Returns:
            True if the command was successful and expected output was found (if specified),
            False otherwise after retries.

        Raises:
            Exception: If the remote command fails to run after CONF.max_cmd_retry attempts.
        """
        for i in range(CONF.max_cmd_retry):
            ssh_run = self.__remote_run_on_adb_host(remote_cmd)
            if ssh_run.returncode == 0:
                if isinstance(expected_outputs, list):
                    return any(output in ssh_run.stdout for output in expected_outputs)
                elif isinstance(expected_outputs, str):
                    return expected_outputs in ssh_run.stdout
                else:
                    # If expected_outputs is None, just return True if command ran successfully
                    return True
            else:
                self.logger.debug(
                    f"Remote CMD: Failed running {remote_cmd}. Return code: {ssh_run.returncode}, Stderr: {ssh_run.stderr}")
                if i == CONF.max_cmd_retry - 1: # If it's the last retry
                    raise Exception(
                        f"Remote CMD: Failed to run {remote_cmd} after {CONF.max_cmd_retry} retries.")
        return False

    def kill_local_adb_server(self):
        """Kills the local ADB server if it is running.

        This prevents conflicts when establishing an SSH tunnel for remote ADB.
        Retries up to CONF.max_cmd_retry times.
        """
        for i in range(CONF.max_cmd_retry):
            adb_run = subprocess.run(
                ["adb", "kill-server"], shell=False, capture_output=True, text=True)
            if ("failed to read response from server" in adb_run.stderr) or ("failed to read response from server" in adb_run.stdout):
                self.logger.info("Local ADB not running")
                break

    def setup_port_forwarding_to_adb_host(self) -> bool:
        """Sets up an SSH tunnel for port forwarding to the ADB host.

        This allows local ADB commands to communicate with a remote ADB server.
        The method blocks until the tunnel is established or a timeout occurs.

        Returns:
            True if the SSH tunnel is successfully established, False otherwise.
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
            ssh_port_forwarding, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Give some time for the SSH tunnel to establish
        time.sleep(2)  # Wait 2 seconds for initial tunnel setup

        # Now, verify the tunnel by trying to run a local ADB command
        while time.time() - ssh_tunnel_start_time < CONF.remote_cmd_timeout:
            try:
                adb_check_cmd = self.__run_adb_cmd(["adb", "devices"])
                if adb_check_cmd.returncode == 0:
                    self.logger.info(
                        f"SSH tunnel active with pid: {self.ssh_process.pid}")
                    return True
            except Exception as e:
                self.logger.debug(f"ADB check failed: {e}")
            time.sleep(1)  # Wait before retrying ADB check
        return False

    def restart_remote_adb(self) -> None:
        """Restarts the ADB server on the remote host.

        It first attempts to kill any running remote ADB server and then starts a new one.
        Debugging information is logged based on the success of these operations.
        """
        if self.__remote_run_on_adb_host_and_check("adb kill-server", ["cannot connect to daemon", "error: protocol fault"]):
            self.logger.debug("Remote ADB server is not running")
        if self.__remote_run_on_adb_host_and_check("adb start-server", "daemon started successfully"):
            self.logger.debug("Remote ADB server started successfully")

    def provision_via_adb(self) -> bool:
        """Provisions the DUT using ADB commands executed via the remote ADB host.

        This method first kills any local ADB server, sets up SSH port forwarding
        to the remote ADB host, restarts the remote ADB server, and then
        processes the list of connected devices to identify the DUT.

        Returns:
            True if provisioning is successful, False otherwise.
        """
        # Kill any lingering local server that will not allow us to bind to adb port
        if self.use_remote_adb:
            self.logger.info("Using remote ADB host")
            self.kill_local_adb_server()
            self.restart_remote_adb()
            self.setup_port_forwarding_to_adb_host()
        
        # Verify adb works
        adb_list_devices_proc = self.__run_adb_cmd(["adb", "devices", "-l"])
        self.logger.debug(f"ADB devices list: {adb_list_devices_proc.stdout}")
        self.get_device_id(adb_list_devices_proc.stdout)
        if self.dut_id:
            return True # Add return True as the method is expected to return a bool
        return False

    def get_device_id(self, adb_device_list: str) -> str:
        """Processes the output of 'adb devices -l' to extract the DUT ID.

        Args:
            adb_device_list: A string containing the output from the 'adb devices -l' command.

        Returns:
            The DUT ID as a string if found, otherwise an empty string.
        """
        device_list = [line.strip()
                       for line in adb_device_list.splitlines() if line.strip()]
        if len(device_list) > 1:  # First line is "list of devices attached" sp skip that
            dut_ids = [line.split(" ")[0] for line in device_list[1:] ]
            if len(dut_ids) == 1:
                self.dut_id = dut_ids[0]
        return self.dut_id if self.dut_id else ""

    def tearDown(self):
        """Tears down the SSH process if it is active.

        This method is intended for cleanup, ensuring that any open SSH connections
        are properly terminated.
        """
        if self.ssh_process:
            self.ssh_process.kill()
