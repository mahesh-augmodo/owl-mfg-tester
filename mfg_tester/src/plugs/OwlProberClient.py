from proto import test_agent_pb2_grpc
from proto import test_agent_pb2
import openhtf as htf
from openhtf.util.configuration import CONF
from typing import Optional
import ipaddress
import grpc
import os
# asyncio is not needed for synchronous gRPC calls unless making specific
# async ones. Removed.


class OwlProberClient(htf.BasePlug):

    def __init__(self) -> None:
        super().__init__()
        self.dut_ip = None
        self.dut_port = None
        self.conn = None  # Stores the raw gRPC channel
        self.stub = None  # Stores the gRPC stub

    def connect(self, ip_address: str, port: int) -> bool:
        """
        Establishes a gRPC connection to the OwlProber agent.
        Returns True on success, False on failure.
        """
        try:
            ipaddress.ip_address(ip_address)  # Validate IP address format
            if not (0 < port < 65536):  # Validate port range
                raise ValueError(f"Invalid port number: {port}")

            self.dut_ip = ip_address
            self.dut_port = port

            # Create an insecure gRPC channel
            self.conn = grpc.insecure_channel(
                f"{self.dut_ip}:{self.dut_port}",
                # Adjust options if needed, e.g., for connection timeouts
                options=[('grpc.max_receive_message_length', -1),  # Unlimited message size
                         ('grpc.max_send_message_length', -1)]
            )
            self.stub = test_agent_pb2_grpc.DutAgentServiceStub(self.conn)

            # Test connection with a small RPC
            # For synchronous clients, need to ensure the connection is ready
            # A simple way to check is to try a quick RPC
            # with grpc.StreamStreamContext() as ctx:
            # self.stub.GetAgentDetails(test_agent_pb2.GetAgentDetailsRequest(), timeout=CONF.grpc_connection_timeout_seconds)

            # More robust connection check, blocking until connected or
            # deadline exceeded
            grpc.channel_ready_future(self.conn).result(
                timeout=CONF.grpc_connection_timeout_seconds)
            self.logger.info(
                f"Successfully connected to OwlProber at {
                    self.dut_ip}:{
                    self.dut_port}")
            return True

        except ValueError as ve:
            self.logger.error(f"Invalid IP address or port: {ve}")
            self.conn = None
            self.stub = None
            return False
        except grpc.FutureTimeoutError:
            self.logger.error(
                f"Failed to connect to OwlProber within {
                    CONF.grpc_connection_timeout_seconds}s. Connection timed out.")
            self.conn = None
            self.stub = None
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to OwlProber: {e}")
            self.conn = None
            self.stub = None
            return False

    def disconnect(self):
        """Closes the gRPC connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.stub = None
            self.logger.info("Disconnected from OwlProber.")

    def GetDeviceAgentDetails(self):
        # Let's test the connection
        test_agent_details = test_agent_pb2.GetAgentDetailsRequest()
        response = self.stub.GetAgentDetails(test_agent_details)
        self.logger.debug(f"Received DeviceAgentDetails: {response}")
        return response

    def GetSystemState(self):
        systemstate_request = test_agent_pb2.GetSystemStateRequest()
        systemstate_request.cpu_temperature_sysfs_path = "/sys/class/hwmon/hwmon2/temp1_input"
        systemstate_request.idle_duration_seconds = 2
        response = self.stub.GetSystemState(systemstate_request)
        self.logger.debug(f"Received SystemState: {response}")
        return response

    def ConfigureOLEDDisplay(
            self,
            i2c_bus_name: str,
            dev_addr: int,
            width: int,
            height: int,
            power_pin: int,
            reset_pin: int):
        oled_settings = test_agent_pb2.OLEDSettings(
            I2CBusName=i2c_bus_name,
            DevAddr=dev_addr,
            Width=width,
            Height=height,
            PowerPin=power_pin,
            ResetPin=reset_pin
        )
        response = self.stub.ConfigureOLEDDisplay(oled_settings)
        self.logger.debug(f"ConfigureOLEDDisplay response: {response}")
        return response

    def SetOLEDStaticText(self, text: str):
        oled_text_request = test_agent_pb2.SetOLEDTextRequest(text=text)
        response = self.stub.SetOLEDStaticText(oled_text_request)
        self.logger.debug(f"SetOLEDStaticText response: {response}")
        return response

    def SetOLEDScrollingText(self, text: str):
        oled_text_request = test_agent_pb2.SetOLEDTextRequest(text=text)
        response = self.stub.SetOLEDScrollingText(oled_text_request)
        self.logger.debug(f"SetOLEDScrollingText response: {response}")
        return response

    def ConfigureBattery(
            self,
            device_name: str,
            voltage_node: str,
            current_node: str,
            temp_node: str):
        battery_settings = test_agent_pb2.BatterySettings(
            device_name=device_name,
            voltage_node=voltage_node,
            current_node=current_node,
            temp_node=temp_node
        )
        response = self.stub.ConfigureBattery(battery_settings)
        self.logger.debug(f"ConfigureBattery response: {response}")
        return response

    def GetBatteryReadings(self):
        battery_readings_request = test_agent_pb2.GetBatteryReadingsRequest()
        response = self.stub.GetBatteryReadings(battery_readings_request)
        self.logger.debug(f"Received BatteryReadings: {response}")
        return response

    def DiscoverEventDevices(self):
        discover_event_devices_request = test_agent_pb2.DiscoverEventDevicesRequest()
        response = self.stub.DiscoverEventDevices(
            discover_event_devices_request)
        self.logger.debug(f"Received DiscoverEventDevices: {response}")
        return response

    def GetEventReportOverDuration(
            self, device_path: str, duration_seconds: int):
        get_event_report_request = test_agent_pb2.GetEventReportOverDurationRequest(
            device_path=device_path, duration_seconds=duration_seconds)
        response = self.stub.GetEventReportOverDuration(
            get_event_report_request)
        self.logger.debug(f"Received GetEventReportOverDuration: {response}")
        return response

    def ConfigureBuzzer(self, device_path: str):
        buzzer_settings = test_agent_pb2.BuzzerSettings(
            device_path=device_path)
        response = self.stub.ConfigureBuzzer(buzzer_settings)
        self.logger.debug(f"ConfigureBuzzer response: {response}")
        return response

    def SetBuzzer(self, on: bool):
        set_buzzer_request = test_agent_pb2.SetBuzzerRequest(on=on)
        response = self.stub.SetBuzzer(set_buzzer_request)
        self.logger.debug(f"SetBuzzer response: {response}")
        return response

    def RunCommand(
            self,
            command: str,
            args: list = None,
            timeout_seconds: int = 30,
            working_directory: str = "",
            stdin_data: str = "",
            use_shell: bool = False):
        """
        Executes a shell command on the DUT via the OwlProber agent.
        Args:
            command: The command executable (e.g., "ls", "echo").
            args: A list of string arguments for the command.
            timeout_seconds: Timeout for the command execution.
            working_directory: Optional working directory for the command.
            stdin_data: Optional data to pipe to the command's stdin.
            use_shell: If True, execute the command through a shell (e.g., "bash -c").
        Returns:
            test_agent_pb2.RunCommandResponse containing stdout, stderr, exit_code, and error_message.
        """
        run_command_request = test_agent_pb2.RunCommandRequest(
            command=command,
            args=args if args is not None else [],
            timeout_seconds=timeout_seconds,
            working_directory=working_directory,
            stdin_data=stdin_data,
            use_shell=use_shell
        )
        response = self.stub.RunCommand(
            run_command_request,
            timeout=CONF.grpc_connection_timeout_seconds)
        self.logger.debug(
            f"RunCommand response: exit_code={
                response.exit_code}, " f"stdout_len={
                len(
                    response.stdout)}, stderr_len={
                    len(
                        response.stderr)}, " f"error_message='{
                            response.error_message}'")
        return response

    def UploadFile(
            self,
            filepath: str,
            chunk_size: int = 65536) -> test_agent_pb2.UploadFileResponse:
        """
        Uploads a file to the OwlProber agent on the DUT.
        Args:
            filepath: The path to the local file to upload.
            chunk_size: The size of chunks to send (in bytes).
        Returns:
            test_agent_pb2.UploadFileResponse indicating success or failure.
        """
        if not os.path.exists(filepath):
            self.logger.error(
                f"UploadFile Failed: Local file not found: {filepath}")
            return test_agent_pb2.UploadFileResponse(
                message=f"Local file not found: {filepath}", success=False)

        def generate_chunks():
            filename = os.path.basename(filepath)
            total_size = os.path.getsize(filepath)
            self.logger.debug(
                f"Starting to generate chunks for {filename}, total size: {total_size} bytes")
            with open(filepath, 'rb') as f:
                offset = 0
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    yield test_agent_pb2.UploadFileRequest(
                        filename=filename,
                        chunk_data=chunk_data,
                        offset=offset,
                        total_size=total_size
                    )
                    offset += len(chunk_data)
            self.logger.debug(f"Finished generating chunks for {filename}")

        try:
            response = self.stub.UploadFile(
                generate_chunks(), timeout=CONF.grpc_connection_timeout_seconds)
            self.logger.info(
                f"UploadFile: {
                    response.message} (Success: {
                    response.success})")
            return response
        except Exception as e:
            self.logger.error(f"UploadFile Failed for {filepath}: {e}")
            return test_agent_pb2.UploadFileResponse(
                message=f"gRPC call failed: {e}", success=False)

    def DownloadFile(self, filename: str, dst_path: str,
                     dst_filename: Optional[str] = "") -> str:
        """
        Downloads a file from the OwlProber agent on the DUT to a local path.
        Args:
            filename: The name of the file on the DUT to download.
            dst_path: The local directory to save the downloaded file.
            dst_filename: Optional parameter to rename file if needed.
        Returns:
            The full local path to the downloaded file on success, or raises an exception on failure.
        Raises:
            Exception: If the gRPC call fails or file cannot be written.
        """
        download_request = test_agent_pb2.DownloadFileRequest(
            filename=filename)

        # Create destination directory if it doesn't exist
        os.makedirs(dst_path, exist_ok=True)
        if dst_filename:
            file_path = os.path.join(dst_path, os.path.basename(dst_filename))
        else:
            file_path = os.path.join(dst_path, os.path.basename(filename))

        self.logger.info(f"Starting download of {filename} to {file_path}")
        try:
            with open(file_path, 'wb') as f:
                for response_chunk in self.stub.DownloadFile(
                        download_request, timeout=CONF.grpc_connection_timeout_seconds):
                    if response_chunk.chunk_data:
                        f.write(response_chunk.chunk_data)
                        self.logger.debug(
                            f"Received chunk for {filename}: offset={
                                response_chunk.offset}, total_size={
                                response_chunk.total_size}")
            self.logger.info(
                f"File {filename} downloaded to {file_path} successfully.")
            return file_path
        except Exception as e:
            self.logger.error(f"DownloadFile Failed for {filename}: {e}")
            raise  # Re-raise the exception after logging
