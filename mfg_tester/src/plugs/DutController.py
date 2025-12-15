import subprocess
import time
import sys
import re
from typing import Optional, List, Union, Callable
from datetime import datetime, timedelta

import openhtf as htf
from openhtf.util.configuration import CONF
from utils.command_result import CommandResult
from utils.safe_decode import safe_decode

WINDOWS_ADB_PATH = "platform_utils/win/android_platform_tools/adb.exe"


class ADBDutControllerPlug(htf.BasePlug):
    def __init__(self) -> None:
        super().__init__()
        self.ssh_process: Optional[subprocess.Popen] = None
        self.use_remote_adb: bool = CONF.use_remote_adb
        self.device_id: Optional[str] = None
        self.adb_bin = WINDOWS_ADB_PATH if sys.platform == 'win32' else 'adb'

        if self.use_remote_adb:
            self._setup_remote_adb()

    def _exec_cmd(
        self,
        cmd: List[str],
        timeout: int = 60,
        retries: int = 0,
        retry_interval: int = 2,
        context: str = "Command"
    ) -> CommandResult:
        """
        Unified helper to execute subprocess commands with retries, timeout, and decoding.
        """
        last_result = None

        for attempt in range(retries + 1):
            if attempt > 0:
                self.logger.debug(
                    f"Retrying {context} (Attempt {attempt + 1}/{retries + 1})...")
                time.sleep(retry_interval)

            self.logger.debug(f"Executing {context}: {' '.join(cmd)}")

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,  # Capture raw bytes for safe_decode
                    timeout=timeout
                )

                stdout = safe_decode(proc.stdout) if proc.stdout else ""
                stderr = safe_decode(proc.stderr) if proc.stderr else ""

                last_result = CommandResult(
                    is_success=(proc.returncode == 0),
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=proc.returncode,
                    error_message=stderr if proc.returncode != 0 else ""
                )

                if last_result.is_success:
                    return last_result

            except subprocess.TimeoutExpired:
                last_result = CommandResult(
                    is_success=False,
                    error_message=f"{context} timed out after {timeout}s")
                self.logger.debug(last_result.error_message)
            except Exception as e:
                last_result = CommandResult(
                    is_success=False, error_message=f"{context} failed: {e}")
                self.logger.debug(last_result.error_message)

        # If we exhausted retries
        err_msg = f"{context} failed after {retries} retries. Last error: {
            last_result.error_message if last_result else 'Unknown'}"
        self.logger.debug(err_msg)
        return last_result

    def run_adb_cmd(
            self,
            args: List[str],
            device_id: Optional[str] = None,
            timeout: int = None,
            retries: int = 0) -> CommandResult:
        """Executes an ADB command locally."""
        target = device_id if device_id else self.device_id
        timeout = timeout if timeout else CONF.adb_timeout

        cmd = [self.adb_bin]

        if target:
            cmd.extend(['-s', target])

        cmd.extend(args)

        return self._exec_cmd(cmd, timeout=timeout, context="ADB")

    def _remote_exec(self, remote_cmd: str) -> CommandResult:
        """Executes a command on the remote ADB host via SSH."""
        cmd = ["ssh", "-tt", f"{CONF.adb_host}", remote_cmd]
        return self._exec_cmd(
            cmd,
            timeout=CONF.adb_timeout,
            context="Remote SSH")

    def _get_device_time_precise(self) -> Optional[datetime]:
        """Retrieves precise time and auto-corrects for timezone offsets."""

        # 1. Read the Raw Hardware Time
        res = self.run_adb_cmd(['shell', 'hwclock -r'])

        if not res.is_success or not res.stdout:
            self.logger.debug("hwclock failed or returned empty")
            return None

        try:
            pattern = r'\s*(\w{3} \w{3} {1,2}\d{1,2} \d{2}:\d{2}:\d{2} \d{4}) {2}([\d.]+) seconds'
            match = re.search(pattern, res.stdout)

            if match:
                # Parse the time string
                time_str = re.sub(r'  (\d) ', r' 0\1 ', match.group(1))
                seconds_frac = float(match.group(2))
                base_time = datetime.strptime(time_str, "%a %b %d %H:%M:%S %Y")
                hw_time = base_time + timedelta(seconds=seconds_frac)

                # Compare RTC time vs Host UTC time
                host_now_utc = datetime.utcnow()
                diff_seconds = (hw_time - host_now_utc).total_seconds()

                # TODO: (mahesh-augmodo) Figure out why cvr_app does this.
                # Check for +8 Hour Offset (28,800 seconds)
                # Tolerance: 28,000 to 29,500 seconds (allows for some drift/reboot time)
                # THIS IS TO DEAL WITH CVR_APP WEIRDNESS
                if 28000 < diff_seconds < 30000:
                    self.logger.warning(
                        "Detected +8h Timezone artifact in RTC. Applying -8h correction.")
                    hw_time -= timedelta(hours=8)

                # Check for -8 Hour Offset (rare, but possible)
                elif -30000 < diff_seconds < -28000:
                    self.logger.warning(
                        "Detected -8h Timezone artifact in RTC. Applying +8h correction.")
                    hw_time += timedelta(hours=8)

                # Check for other common offsets (e.g., +1h for CET) can be
                # added here

                return hw_time

        except Exception as e:
            self.logger.debug(f"Failed to parse time: {e}")

        return None

    def _wait_for_device_offline(self, timeout: int = 60) -> bool:
        self.logger.debug(
            f"Waiting for device {
                self.device_id} to go offline...")
        start = time.time()
        while time.time() - start < timeout:
            res = self.run_adb_cmd(["devices"])
            if res.is_success and self.device_id not in res.stdout:
                self.logger.debug("Device is offline.")
                return True
            time.sleep(3)
        return False

    def adb_push(
            self,
            local: str,
            remote: str,
            timeout: int = None,
            retries: int = None) -> CommandResult:
        """Executes adb push."""
        retries = retries if retries is not None else CONF.max_cmd_retry
        return self.run_adb_cmd(['push', local, remote],
                                timeout=timeout, retries=retries)

    def _setup_remote_adb(self) -> Optional[CommandResult]:
        """Sets up SSH tunnel and restarts remote ADB."""
        self.logger.debug("Setting up remote ADB...")

        # 1. Kill local
        self.run_adb_cmd(["kill-server"])

        # 2. Restart Remote
        self._remote_exec("adb kill-server")  # Ignore result
        start_res = self._remote_exec("adb start-server")
        if not start_res.is_success:
            return start_res

        # 3. SSH Tunnel
        self.logger.debug(f"Tunneling to {CONF.adb_host}")
        self.ssh_process = subprocess.Popen(
            ["ssh", "-vN", "-L", f"{CONF.adb_host_port}:localhost:{CONF.adb_host_port}", f"{CONF.adb_host}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
        )
        time.sleep(2)  # Stabilize

        # 4. Verify
        start_time = time.time()
        while time.time() - start_time < CONF.remote_cmd_timeout:
            if self.run_adb_cmd(["devices"]).is_success:
                self.logger.debug("SSH Tunnel established.")
                return CommandResult(is_success=True)
            time.sleep(1)

        return CommandResult(
            is_success=False,
            error_message="Tunnel setup timed out")

    def setup_adb_test_connection(self) -> CommandResult:
        """Main provisioning entry point."""
        # Check if already connected
        check = self.run_adb_cmd(["devices"])
        device_id = self.get_connected_device_id(check.stdout)
        if check.is_success and device_id:
            self.logger.debug(f"Device {self.device_id} already connected.")
            return CommandResult(is_success=True)

        if self.use_remote_adb:
            self._setup_remote_adb()

        # Retry finding device
        res = self._exec_cmd(
            [self.adb_bin, 'devices'],
            retries=3,
            context="Scan Devices"
        )

        device_id = self.get_connected_device_id(check.stdout)
        if not device_id:
            return CommandResult(
                is_success=False,
                stdout=res.stdout,
                stderr=res.stderr)

    def get_connected_device_id(self, adb_device_list: str) -> str:
        """Get's device id from adb devices -l
        Assumes only one device is connected if not, errors out."""
        device_list = [line.strip()
                       for line in adb_device_list.splitlines() if line.strip()]
        if len(device_list) > 1:  # First line is "list of devices attached" so skip that
            dut_ids = [line.split(" ")[0] for line in device_list[1:]]
            if len(dut_ids) == 1:
                self.device_id = dut_ids[0]
        return self.device_id if self.device_id else ""

    def push_folder_to_device(
            self,
            folder_path: str,
            device_folder_path: str) -> CommandResult:
        if not self.device_id:
            return CommandResult(
                is_success=False,
                error_message="No Device ID")

        res = self.adb_push(
            folder_path,
            device_folder_path,
            retries=CONF.max_cmd_retry)
        if res.is_success:
            self.logger.debug(f"Pushed {folder_path} to {device_folder_path}")
        else:
            self.logger.debug(f"Push folder failed: {res.stderr}")
        return res

    def bringup_wifi_on_device(self, wifi_script_path: str) -> CommandResult:
        if not self.device_id:
            return CommandResult(is_success=False)

        path = f"/tmp/{wifi_script_path}"
        self.run_adb_cmd(["shell", "chmod +x", path])

        res = self.run_adb_cmd(
            ["shell", path, f"{CONF.wifi_ssid}", f"{CONF.wifi_password}"], timeout=120)
        if res.is_success:
            self.logger.debug("Wifi script executed successfully")
        else:
            self.logger.debug(f"Wifi script failed: {res.stderr}")
        return res

    def scan_wifi_networks(self, wifi_scan_script_path: str) -> CommandResult:
        if not self.device_id:
            return CommandResult(is_success=False)

        path = f"/tmp/{wifi_scan_script_path}"
        self.run_adb_cmd(["shell", "chmod +x", path])

        res = self.run_adb_cmd(["shell", path], timeout=120)
        if res.is_success:
            self.logger.debug("Wifi scan script executed successfully")
        else:
            self.logger.debug(f"Wifi scan script failed: {res.stderr}")
        return res

    def tearDown(self) -> None:
        if self.ssh_process:
            self.ssh_process.kill()
