from proto import test_agent_pb2_grpc
from proto import test_agent_pb2
from openhtf.util.configuration import CONF
import ipaddress
import grpc
import os


class AgentM():

    def __init__(self, ip_address: str, port: int) -> None:
        self.dut_ip = None
        self.dut_port = None
        self.conn = None
        try:
            ipaddress.ip_address(ip_address)
            if 0 < port < 65536:
                self.dut_ip = ip_address
                self.dut_port = port
            else:
                raise ValueError
            # Dial the gRPC connection
            self.conn = grpc.aio.insecure_channel(
                f"{self.dut_ip}:{self.dut_port}")
            self.stub = test_agent_pb2_grpc.DutAgentServiceStub(self.conn)

        except ValueError:
            print(
                f"dut ip address not valid. grpc ip and port given were {ip_address}:{port}")

    async def GetDeviceAgentDetails(self):
        # Let's test the connection
        test_agent_details = test_agent_pb2.GetAgentDetailsRequest()
        response = await self.stub.GetAgentDetails(test_agent_details)
        print(response)
        return response

    async def GetSystemState(self):
        systemstate_request = test_agent_pb2.GetSystemStateRequest()
        systemstate_request.cpu_temperature_sysfs_path = "/sys/class/hwmon/hwmon2/temp1_input"
        systemstate_request.idle_duration_seconds = 2
        response = await self.stub.GetSystemState(systemstate_request)
        print(response)
        return response

    async def ConfigureOLEDDisplay(
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
        response = await self.stub.ConfigureOLEDDisplay(oled_settings)
        print(response)
        return response

    async def SetOLEDStaticText(self, text: str):
        oled_text_request = test_agent_pb2.SetOLEDTextRequest(text=text)
        response = await self.stub.SetOLEDStaticText(oled_text_request)
        print(response)
        return response

    async def SetOLEDScrollingText(self, text: str):
        oled_text_request = test_agent_pb2.SetOLEDTextRequest(text=text)
        response = await self.stub.SetOLEDScrollingText(oled_text_request)
        print(response)
        return response

    async def ConfigureBattery(
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
        response = await self.stub.ConfigureBattery(battery_settings)
        print(response)
        return response

    async def GetBatteryReadings(self):
        battery_readings_request = test_agent_pb2.GetBatteryReadingsRequest()
        response = await self.stub.GetBatteryReadings(battery_readings_request)
        print(response)
        return response

    async def DiscoverEventDevices(self):
        discover_event_devices_request = test_agent_pb2.DiscoverEventDevicesRequest()
        response = await self.stub.DiscoverEventDevices(discover_event_devices_request)
        print(response)
        return response

    async def GetEventReportOverDuration(
            self, device_path: str, duration_seconds: int):
        get_event_report_request = test_agent_pb2.GetEventReportOverDurationRequest(
            device_path=device_path, duration_seconds=duration_seconds)
        response = await self.stub.GetEventReportOverDuration(get_event_report_request)
        print(response)
        return response

    async def ConfigureBuzzer(self, device_path: str):
        buzzer_settings = test_agent_pb2.BuzzerSettings(
            device_path=device_path)
        response = await self.stub.ConfigureBuzzer(buzzer_settings)
        print(response)
        return response

    async def SetBuzzer(self, on: bool):
        set_buzzer_request = test_agent_pb2.SetBuzzerRequest(on=on)
        response = await self.stub.SetBuzzer(set_buzzer_request)
        print(response)
        return response

    async def UploadFile(self, filepath: str, chunk_size: int = 4096):
        async def generate_chunks():
            filename = os.path.basename(filepath)
            total_size = os.path.getsize(filepath)
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

        response = await self.stub.UploadFile(generate_chunks())
        print(response)
        return response

    async def DownloadFile(self, filename: str, destination_path: str):
        download_request = test_agent_pb2.DownloadFileRequest(
            filename=filename)

        file_path = os.path.join(destination_path, os.path.basename(filename))

        with open(file_path, 'wb') as f:
            async for response in self.stub.DownloadFile(download_request):
                f.write(response.chunk_data)
                print(
                    f"Received chunk offset: {
                        response.offset}, total size: {
                        response.total_size}")
        print(f"File {filename} downloaded to {file_path} successfully.")
        return file_path
