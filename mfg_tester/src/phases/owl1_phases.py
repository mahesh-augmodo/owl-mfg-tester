import openhtf as htf
from openhtf.util.configuration import CONF
from plugs.DutController import ADBDutControllerPlug
from plugs.GuiPlug import GuiPlug
from plugs.OwlProberClient import OwlProberClient
from utils.command_result import CommandResult
from openhtf.core.test_descriptor import TestApi as htfTestApi
from utils.rtc_utils import get_rtc_drift, set_device_time
import ipaddress
import time
import re
import pandas
import io
import tempfile
from os import path


def is_valid_ip(ip_string):
    """Returns True if the input string is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
def ConnectToDeviceViaADB(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug):
    """Phase that runs the provisioning logic."""
    test.logger.info("Starting ConnectToDeviceViaADB Phase...")
    gui.update_instruction("Connecting to device...")
    dut.device_id = test.test_record.dut_id

    adb_conn_result = dut.setup_adb_test_connection()
    if not adb_conn_result.is_success:
        test.logger.error(
            f"ConnectToDeviceViaADB Failed: {adb_conn_result.error_message}")
        gui.update_instruction(
            "Failed to connect to device. Please check USB connection.")
        return htf.PhaseResult.STOP

    test.logger.info("ConnectToDeviceViaADB Passed.")
    gui.update_instruction("Device connected successfully.")
    return htf.PhaseResult.CONTINUE


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
def PushTestScriptsToDevice(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug):
    test.logger.info("Starting PushTestScriptsToDevice Phase...")
    gui.update_instruction("Pushing test scripts to device...")

    test.logger.info(
        "Ensuring ADB connection is active before pushing scripts...")
    adb_conn_result = dut.setup_adb_test_connection()
    if not adb_conn_result.is_success:
        test.logger.error(
            f"PushTestScriptsToDevice Failed: ADB reconnection failed: {
                adb_conn_result.error_message}")
        gui.update_instruction("Failed to reconnect to device. Check logs.")
        return htf.PhaseResult.STOP

    push_scripts_result = dut.push_scripts_to_device(CONF.scripts_path)
    if not push_scripts_result.is_success:
        test.logger.error(
            f"PushTestScriptsToDevice Failed: Pushing scripts to device failed: {
                push_scripts_result.error_message}")
        gui.update_instruction("Failed to push test scripts to device.")
        return htf.PhaseResult.STOP

    test.logger.info("PushTestScriptsToDevice Passed.")
    gui.update_instruction("Test scripts pushed successfully.")
    return htf.PhaseResult.CONTINUE


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("ip_address").with_validator(is_valid_ip)
)
def ConnectToFactoryWifi(test: htfTestApi, dut: ADBDutControllerPlug, gui):
    test.logger.info("Starting ConnectToFactoryWifi Phase...")
    gui.update_instruction("Connecting to factory Wi-Fi...")
    wifi_script_path = path.join(CONF.scripts_path, CONF.wifi_connect_script)
    wifi_result: CommandResult = dut.bringup_wifi_on_device(wifi_script_path)
    test.attach(
        'wifi_bringup_report.txt',
        wifi_result.full_output,
        mimetype="text/plain"
    )
    if not wifi_result.is_success:
        test.logger.error(
            f"ConnectToFactoryWifi Failed: Wifi bringup failed: {
                wifi_result.error_message}")
        gui.update_instruction(
            "Failed to bring up Wi-Fi. Check device and network settings.")
        return htf.PhaseResult.STOP

    # Let's find the IP Address
    ip_address_search = re.search(
        r'Device.IP.Address.=.([0-9.]+)*', wifi_result.full_output)
    if ip_address_search:
        test.measurements.ip_address = ip_address_search.group(1)
        test.state["ip_address"] = ip_address_search.group(1)
    else:
        test.logger.error(
            "ConnectToFactoryWifi Failed: Could not find IP address in WiFi bringup output.")
        gui.update_instruction("Failed to obtain IP address from Wi-Fi.")
        return htf.PhaseResult.STOP

    test.logger.info("Wifi is up")
    test.logger.info("ConnectToFactoryWifi Passed.")
    gui.update_instruction("Connected to factory Wi-Fi successfully.")


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.PhaseOptions(repeat_limit=3)
def ScanWifiNetworks(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug):
    TestWifiNetworks = CONF.wifi_scan_networks
    wifi_scan_script_path = path.join(CONF.scripts_path, CONF.wifi_scan_script)
    wifi_result = dut.scan_wifi_networks(wifi_scan_script_path)
    if wifi_result.is_success:
        for wifiname in TestWifiNetworks:
            if wifiname not in wifi_result.full_output:
                test.logger.error(
                    "WiFi scan failed: Cannot find test WiFi networks in network scan:")
                gui.update_instruction(
                    "Failed to find required Wi-Fi networks in scan.")
                return htf.PhaseResult.REPEAT

    test.logger.info("ScanWifiNetworks Passed.")
    gui.update_instruction("Found known networks in WiFi Scan.")


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("rtc_time_drift_sec")
)
def TestRTC(test: htfTestApi, dut: ADBDutControllerPlug, gui: GuiPlug):
    test.logger.info("Starting TestRTC Phase...")
    gui.update_instruction("Starting RTC Test...")

    # 1. Set Time
    gui.update_instruction("Setting device time...")
    ref_time_data = set_device_time(dut, test.logger)

    # 2. Write to HW Clock & Shutdown
    gui.update_instruction("Writing to hardware clock and rebooting device...")
    dut.run_adb_cmd(["shell", "hwclock -w"])
    dut.run_adb_cmd(["shell", "reboot"])
    time.sleep(15)  # It seems like reboot takes some timw to execute.

    # 4. Poll for return and calculate drift (No fixed wait!)
    gui.update_instruction("Polling for device recovery after reboot...")
    try:
        drift = get_rtc_drift(
            dut,
            ref_time_data,
            timeout_s=60,
            logger=test.logger)
        test.measurements.rtc_time_drift_sec = drift
        test.logger.info(f"RTC Drift measured: {drift:.4f}s")
        test.logger.info("TestRTC Passed.")
        gui.update_instruction("RTC Test Passed successfully.")
        return htf.PhaseResult.CONTINUE

    except TimeoutError as e:
        test.logger.error(f"TestRTC Failed: {e}")
        gui.update_instruction("RTC Test Failed. Check logs for details.")
        return htf.PhaseResult.STOP


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.plug(owl=OwlProberClient)
@htf.measures(
    htf.Measurement("mac_address")
)
def DeployAndConnectToOwlProber(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug,
        owl: OwlProberClient):
    test.logger.info("Starting DeployAndConnectToOwlProber Phase...")
    gui.update_instruction("Setting up device controller...")
    owl_prober_path = path.join(CONF.owl_prober_path, "owl_prober")
    result = dut.adb_push(owl_prober_path, "/tmp/")  # Plugs persist
    if not result.is_success:
        test.logger.error(
            f"DeployAndConnectToOwlProber Failed: Unable to push owl_prober to DUT, error: {
                result.stderr}")
        gui.update_instruction("Failed to deploy device controller.")
        return htf.PhaseResult.STOP

    # Kill owl_prober if this is a running. Result does not matter
    test.logger.info("Killing existing owl_prober instances (if any)...")
    gui.update_instruction("Stopping existing device controller (if any)...")
    dut.run_adb_cmd(["shell",
                     "'ps | grep owl_test_agent | grep -v grep | cut -d"
                     " -f2 | xargs kill -9'"])

    # Start owl_prober
    test.logger.info("Setting execute permissions for owl_prober...")
    gui.update_instruction("Setting up device controller permissions...")
    result = dut.run_adb_cmd(["shell", "chmod +x /tmp/owl_prober"])
    if not result.is_success:
        test.logger.error(
            "DeployAndConnectToOwlProber Failed: Unable to make owl_prober executable.")
        gui.update_instruction(
            "Failed to set up device controller permissions.")
        return htf.PhaseResult.STOP

    test.logger.info("Starting owl_prober on device...")
    gui.update_instruction("Starting device controller...")
    result = dut.run_adb_cmd(["shell", "nohup /tmp/owl_prober"])
    if not result.is_success:
        test.logger.error(
            "DeployAndConnectToOwlProber Failed: Unable to start owl_prober.")
        gui.update_instruction("Failed to start device controller.")
        return htf.PhaseResult.STOP

    # Try to conenct to gRPC.
    test.logger.info(
        f"Connecting to owl_prober gRPC interface at {
            test.state['ip_address']}:{
            CONF.dut_port}...")
    gui.update_instruction("Connecting to device controller...")
    if not owl.connect(test.state["ip_address"], port=CONF.dut_port):
        # test.state['ip_address'] = "192.168.8.207" #Debug
        # if not owl.connect(
        #     "127.0.0.1",
        #         port=CONF.dut_port):  # #Debug
        test.logger.error(
            f"DeployAndConnectToOwlProber Failed: Unable to connect to owl_prober gRPC interface at {
                test.state['ip_address']}:{
                CONF.dut_port}")
        gui.update_instruction(
            "Failed to establish device control communication.")
        return htf.PhaseResult.STOP

    agent_details = owl.GetDeviceAgentDetails()
    test.measurements.mac_address = agent_details.mac_addr
    test.logger.info("DeployAndConnectToOwlProber Passed.")
    gui.update_instruction("Device controller ready.")


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestOLEDDisplay(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    test.logger.info("Starting TestOLEDDisplay Phase...")
    gui.update_instruction("Starting OLED Display Test...")

    # First configure OLED bus.
    test.logger.info("Configuring OLED display...")
    gui.update_instruction("Configuring OLED display...")
    try:
        owl.ConfigureOLEDDisplay(
            "/dev/i2c-2",
            0x3C,
            128,
            64,
            17,
            187
        )
    except Exception as e:
        test.logger.error(
            f"TestOLEDDisplay Failed: Unable to configure OLED display: {e}")
        gui.update_instruction("Failed to configure OLED display.")
        return htf.PhaseResult.STOP

    test.logger.info("Setting OLED scrolling text...")
    gui.update_instruction("Setting text on OLED display...")
    try:
        owl.SetOLEDScrollingText("OLED Test")
    except Exception as e:
        test.logger.error(
            f"TestOLEDDisplay Failed: Unable to set OLED scrolling text: {e}")
        gui.update_instruction("Failed to set text on OLED display.")
        return htf.PhaseResult.STOP

    oled_confirm = gui.prompt_user(
        "Is there text on the OLED Screen ?", [
            "Yes", "No"])
    if oled_confirm == "No":
        test.logger.error(
            "TestOLEDDisplay Failed: Operator confirmed no text on OLED.")
        gui.update_instruction("Operator confirmed no text on OLED.")
        return htf.PhaseResult.STOP

    test.logger.info("Clearing OLED scrolling text.")
    gui.update_instruction("Clearing text from OLED display.")
    owl.SetOLEDScrollingText("")

    test.logger.info("TestOLEDDisplay Passed.")
    gui.update_instruction("OLED Display Test Passed successfully.")


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("accelerometer_present"),
    htf.Measurement("gyro_present"),
    htf.Measurement("num_keys")
)
def TestIMUAndKeysPresent(
        test: htfTestApi,
        gui: GuiPlug,
        owl: OwlProberClient):
    input_devices = owl.DiscoverEventDevices()
    key_devices = [
        device for device in input_devices.devices if device.device_type == "key"]
    # Gyros are also reported as "device_type" accelerometer
    accel_devices = [
        device for device in input_devices.devices if device.device_type == "accelerometer"]

    # There will never be >1 device of each type.
    for device in accel_devices:
        if "gsensor" in device.device_name:
            test.measurements.accelerometer_present = True
            test.state["accel_device"] = device
        elif "gyro" in device.device_name:
            test.state["gyro_device"] = device
            test.measurements.gyro_present = True

    test.measurements.num_keys = len(key_devices)


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("accelerometer_events_3s"),
    htf.Measurement("gyro_events_3s")
)
def TestIMUAccelGyro(test: htfTestApi, gui: GuiPlug, owl: OwlProberClient):
    try:
        test.logger.info("Starting TestIMUAccelGyro Phase...")
        gui.update_instruction("Starting Accelerometer & Gyro Test...")
        accelerometer = test.state["accel_device"]
        gyro = test.state["gyro_device"]
        accel_report = owl.GetEventReportOverDuration(
            accelerometer.sysfs_path, duration_seconds=3)
        gyro_report = owl.GetEventReportOverDuration(
            gyro.sysfs_path, duration_seconds=3)
        accel_csv = pandas.read_csv(io.StringIO(accel_report.csv_report))
        gyro_report = owl.GetEventReportOverDuration(
            gyro.sysfs_path, duration_seconds=3)
        gyro_csv = pandas.read_csv(io.StringIO(gyro_report.csv_report))
        test.measurements.accelerometer_events_3s = len(accel_csv)
        test.measurements.gyro_events_3s = len(gyro_csv)

        test.logger.info("TestIMUAccelGyro Completed.")
        gui.update_instruction("Accelerometer & Gyro Test Completed.")

    except KeyError:
        return htf.PhaseResult.STOP


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestBuzzer(test: htfTestApi, gui: GuiPlug, owl: OwlProberClient):
    test.logger.info("Starting TestBuzzer Phase...")
    gui.update_instruction("Starting Buzzer Sound Test...")
    buzzer_path = "/sys/class/pwm/pwmchip3/pwm0/enable"
    owl.ConfigureBuzzer(buzzer_path)
    owl.SetBuzzer(True)
    buzzer_audible = gui.prompt_user(
        "Can you hear the Buzzer beeping ?", [
            "Yes", "No"])
    owl.SetBuzzer(False)
    if buzzer_audible == "No":
        htf.PhaseResult.STOP

    test.logger.info("TestBuzzer Passed.")
    gui.update_instruction("Buzzer Sound test passed successfully.")


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("cpu_idle_percentage"),
    htf.Measurement("cpu_load_avg"),
    htf.Measurement("cpu_temp"),
    htf.Measurement("total_memory_kb")
)
def TestSystemState(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    try:
        system_state = owl.GetSystemState()
        test.measurements.cpu_temp = system_state.cpu_temperature
        test.measurements.cpu_idle_percentage = system_state.cpu_idle_percent
        test.measurements.cpu_load_avg = system_state.cpu_load_average
        test.measurements.total_memory_kb = system_state.total_memory_kb
    except BaseException:
        return htf.PhaseResult.FAIL_AND_CONTINUE


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestLEDs(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    # Set to RED
    owl.SetLEDColor("red_led", "green_led", "blue_led", 255, 0, 0, 0, 0, 0)
    response = gui.set_user_response(
        "What colour is the LED ?", [
            "Red", "Green", "Blue"])
    if response != "Red":
        htf.PhaseResult.FAIL_AND_CONTINUE
    # Set to Green
    owl.SetLEDColor("red_led", "green_led", "blue_led", 0, 255, 0, 0, 0, 0)
    response = gui.set_user_response(
        "What colour is the LED ?", [
            "Red", "Green", "Blue"])
    if response != "Green":
        htf.PhaseResult.FAIL_AND_CONTINUE
    # Set to Blue
    owl.SetLEDColor("red_led", "green_led", "blue_led", 0, 0, 255, 0, 0, 0)
    response = gui.set_user_response(
        "What colour is the LED ?", [
            "Red", "Green", "Blue"])
    if response != "Blue":
        htf.PhaseResult.FAIL_AND_CONTINUE
    # Set to Green and Blink
    owl.SetLEDColor("red_led", "green_led", "blue_led", 0, 255, 0, 0, 1, 0)
    response = gui.set_user_response("Is the LED Blinking?", ["Yes", "No"])
    if response == "No":
        htf.PhaseResult.FAIL_AND_CONTINUE


@htf.plug(owl=OwlProberClient)
@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("left_cam_present"),
    htf.Measurement("right_cam_present")
)
def IdentifyCamerasAndStopRecorder(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug,
        owl: OwlProberClient):

    cameras = dict()
    cameras["Left"] = "/dev/v4l-subdev4"
    cameras["Right"] = "/dev/v4l-subdev9"

    for key in cameras.keys():
        test.state[key] = cameras[key]

    for camera in cameras.keys():
        command = "v4l2-ctl"
        args = f"-d {cameras[camera]} --all".split(" ")
        result = owl.RunCommand(command,
                                args,
                                timeout_seconds=20,
                                use_shell=True
                                )
        if 'User Controls' in result.stdout and 'Image Source Controls' in result.stdout:
            if camera == "Left":
                test.measurements.left_cam_present = True
            if camera == "Right":
                test.measurements.right_cam_present = True

    owl.RunCommand("RkLunch-stop.sh", [], use_shell=True)


@htf.plug(owl=OwlProberClient)
@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
def TestCamerasDarkPhoto(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug,
        owl: OwlProberClient):

    cameras = dict()
    cameras["Left"] = {"v4l-dev": test.state["Left"], "cam_idx": 1}
    cameras["Right"] = {"v4l-dev": test.state["Right"], "cam_idx": 0}
    for camera, details in cameras.items():
        command = "rkadk_photo_test"
        args = f"-I:{details["cam_idx"]} ".split(" ")
        keys_to_send = "\n quit\n"
        gui.prompt_user(
            f"Cover {camera} camera for taking dark photo. Click ok when ready")
        owl.RunCommand("rm", ["-rf", "/tmp/*.jpeg"], use_shell=True)
        owl.RunCommand(command,
                       args,
                       timeout_seconds=CONF.camera_cmd_timeout,
                       stdin_data=keys_to_send,
                       use_shell=True
                       )
        dst_filename = f"DarkPhotoTest{camera}.jpeg"
        photo_file = owl.DownloadFile(
            "/tmp/PhotoTest_0.jpeg",
            tempfile.gettempdir(),
            dst_filename)
        test.attach(
            name=dst_filename,
            binary_data=io.open(photo_file, mode='rb').read(),
            mimetype="image/jpeg"
        )
        print(photo_file)
