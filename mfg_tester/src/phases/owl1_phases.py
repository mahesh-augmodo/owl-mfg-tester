import gettext
import io
import ipaddress
import os
import re
import tempfile
import time

import openhtf as htf
from openhtf.core.test_descriptor import TestApi as htfTestApi
from openhtf.util.configuration import CONF
import pandas

from plugs.DutController import ADBDutControllerPlug
from plugs.GuiPlug import GuiPlug
from plugs.OwlProberClient import OwlProberClient
from utils.command_result import CommandResult
from utils.string_utils import convert_unit_suffix
from utils.rtc_utils import get_rtc_drift, set_device_time
from utils.camera_command_parsers import parse_dumpcam_hwi, parse_dumpcam_cnr_tnr
from utils.i18n import _
from utils.bundle_utils import get_resource_path


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
    gui.update_instruction(_("Connecting to device..."))

    adb_conn_result = dut.setup_adb_test_connection()
    if not adb_conn_result.is_success:
        test.logger.error(
            f"ConnectToDeviceViaADB Failed: {adb_conn_result.error_message}")
        gui.update_instruction(
            _("Failed to connect to device. Please check USB connection."))
        return htf.PhaseResult.STOP
    # We are reverting to getting device id from adb instead of passing it
    # ourselves.
    test.test_record.dut_id = dut.device_id
    test.logger.info("ConnectToDeviceViaADB Passed.")
    gui.update_instruction(_("Device connected successfully."))
    return htf.PhaseResult.CONTINUE


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
def PushTestScriptsToDevice(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug):
    test.logger.info("Starting PushTestScriptsToDevice Phase...")
    gui.update_instruction(_("Pushing test scripts to device..."))

    test.logger.info(
        "Ensuring ADB connection is active before pushing scripts...")
    adb_conn_result = dut.setup_adb_test_connection()
    if not adb_conn_result.is_success:
        test.logger.error(
            f"PushTestScriptsToDevice Failed: ADB reconnection failed: {
                adb_conn_result.error_message}")
        gui.update_instruction(_("Failed to reconnect to device. Check logs."))
        return htf.PhaseResult.STOP

    push_scripts_result = dut.push_folder_to_device(
        get_resource_path(CONF.scripts_path), CONF.dev_prober_path)
    if not push_scripts_result.is_success:
        test.logger.error(
            f"PushTestScriptsToDevice Failed: Pushing scripts to device failed: {
                push_scripts_result.error_message}")
        gui.update_instruction(_("Failed to push test scripts to device."))
        return htf.PhaseResult.STOP

    test.logger.info("PushTestScriptsToDevice Passed.")
    gui.update_instruction(_("Test scripts pushed successfully."))
    return htf.PhaseResult.CONTINUE


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("ip_address").with_validator(is_valid_ip)
)
def ConnectToFactoryWifi(test: htfTestApi, dut: ADBDutControllerPlug, gui):
    test.logger.info("Starting ConnectToFactoryWifi Phase...")
    gui.update_instruction(_("Connecting to factory Wi-Fi..."))
    wifi_script_path = f"{CONF.dev_prober_path}/{CONF.wifi_connect_script}"
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
            _("Failed to bring up Wi-Fi. Check device and network settings."))
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
        gui.update_instruction(_("Failed to obtain IP address from Wi-Fi."))
        return htf.PhaseResult.STOP

    test.logger.info("Wifi is up")
    test.logger.info("ConnectToFactoryWifi Passed.")
    gui.update_instruction(_("Connected to factory Wi-Fi successfully."))


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.PhaseOptions(repeat_limit=3)
def ScanWifiNetworks(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug):
    test.logger.info("Starting ScanWifiNetworks Phase...")
    gui.update_instruction(_("Scanning for Wi-Fi networks..."))
    TestWifiNetworks = CONF.wifi_scan_networks
    wifi_scan_script_path = f"{CONF.dev_prober_path}/{CONF.wifi_scan_script}"
    wifi_result = dut.scan_wifi_networks(wifi_scan_script_path)
    if wifi_result.is_success:
        for wifiname in TestWifiNetworks:
            if wifiname not in wifi_result.full_output:
                test.logger.error(
                    "WiFi scan failed: Cannot find test WiFi networks in network scan:")
                gui.update_instruction(
                    _("Failed to find required Wi-Fi networks in scan."))
                return htf.PhaseResult.REPEAT

    test.logger.info("ScanWifiNetworks Passed.")
    gui.update_instruction(_("Found known networks in WiFi Scan."))


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("rtc_time_drift_sec")
)
def TestRTC(test: htfTestApi, dut: ADBDutControllerPlug, gui: GuiPlug):
    test.logger.info("Starting TestRTC Phase...")
    gui.update_instruction(_("Starting RTC Test..."))

    # 1. Set Time
    gui.update_instruction(_("Setting device time..."))
    ref_time_data = set_device_time(dut, test.logger)

    # 2. Write to HW Clock & Shutdown
    gui.update_instruction(
        _("Writing to hardware clock and rebooting device..."))
    dut.run_adb_cmd(["shell", "hwclock -w"])
    dut.run_adb_cmd(["shell", "reboot"])
    time.sleep(15)  # It seems like reboot takes some timw to execute.

    # 4. Poll for return and calculate drift (No fixed wait!)
    gui.update_instruction(_("Polling for device recovery after reboot..."))
    try:
        drift = get_rtc_drift(
            dut,
            ref_time_data,
            timeout_s=60,
            logger=test.logger)
        test.measurements.rtc_time_drift_sec = drift
        test.logger.info(f"RTC Drift measured: {drift:.4f}s")
        test.logger.info("TestRTC Passed.")
        gui.update_instruction(_("RTC Test Passed successfully."))
        return htf.PhaseResult.CONTINUE

    except TimeoutError as e:
        test.logger.error(f"TestRTC Failed: {e}")
        gui.update_instruction(_("RTC Test Failed. Check logs for details."))
        return htf.PhaseResult.STOP


@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.plug(owl=OwlProberClient)
@htf.PhaseOptions(repeat_limit=3)
@htf.measures(
    htf.Measurement("mac_address")
)
def DeployAndConnectToOwlProber(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug,
        owl: OwlProberClient):
    test.logger.info("Starting DeployAndConnectToOwlProber Phase...")
    gui.update_instruction(_("Setting up device controller..."))
    owl_prober_path = get_resource_path(
        os.path.join(CONF.owl_prober_path, 'owl_prober'))
    result = dut.adb_push(
        owl_prober_path,
        CONF.dev_prober_path)  # Plugs persist
    if not result.is_success:
        test.logger.error(
            f"DeployAndConnectToOwlProber Failed: Unable to push owl_prober to DUT, error: {
                result.stderr}")
        gui.update_instruction(_("Failed to deploy device controller."))
        return htf.PhaseResult.REPEAT

    # Kill owl_prober if this is a running. Result does not matter
    test.logger.info("Killing existing owl_prober instances (if any).")
    gui.update_instruction(_("Stopping existing device controller (if any)."))
    dut.run_adb_cmd(["shell",
                     "'ps | grep owl_test_agent | grep -v grep | cut -d"
                     " -f2 | xargs kill -9'"])

    # Start owl_prober
    test.logger.info("Setting execute permissions for owl_prober...")
    gui.update_instruction(_("Setting up device controller permissions..."))
    result = dut.run_adb_cmd(
        ["shell", f"chmod +x {CONF.dev_prober_path}/owl_prober"])
    if not result.is_success:
        test.logger.error(
            "DeployAndConnectToOwlProber Failed: Unable to make owl_prober executable.")
        gui.update_instruction(
            _("Failed to set up device controller permissions."))
        return htf.PhaseResult.REPEAT

    test.logger.info("Starting owl_prober on device...")
    gui.update_instruction(_("Starting device controller..."))
    result = dut.run_adb_cmd(
        ["shell", f"nohup {CONF.dev_prober_path}/owl_prober"])
    if not result.is_success:
        test.logger.error(
            f"DeployAndConnectToOwlProber Failed: Unable to start owl_prober.")
        gui.update_instruction(_("Failed to start device controller."))
        return htf.PhaseResult.REPEAT

    # Try to conenct to gRPC.
    test.logger.info(
        f"Connecting to owl_prober gRPC interface at {
            test.state['ip_address']}:{
            CONF.dut_port}...")
    gui.update_instruction(_("Connecting to device controller..."))
    if not owl.connect(test.state["ip_address"], port=CONF.dut_port):
        test.logger.error(
            f"DeployAndConnectToOwlProber Failed: Unable to connect to owl_prober gRPC interface at {
                test.state['ip_address']}:{
                CONF.dut_port}")
        gui.update_instruction(
            _("Failed to establish device control communication."))
        return htf.PhaseResult.REPEAT

    agent_details = owl.GetDeviceAgentDetails()
    test.measurements.mac_address = agent_details.mac_addr
    test.logger.info("DeployAndConnectToOwlProber Passed.")
    gui.update_instruction(_("Device controller ready."))


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestOLEDDisplay(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    test.logger.info("Starting TestOLEDDisplay Phase...")
    gui.update_instruction(_("Starting OLED Display Test..."))

    # First configure OLED bus.
    test.logger.info("Configuring OLED display...")
    gui.update_instruction(_("Configuring OLED display..."))
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
        gui.update_instruction(_("Failed to configure OLED display."))
        return htf.PhaseResult.STOP

    test.logger.info("Setting OLED scrolling text...")
    gui.update_instruction(_("Setting text on OLED display..."))
    try:
        owl.SetOLEDScrollingText("OLED Test")
    except Exception as e:
        test.logger.error(
            f"TestOLEDDisplay Failed: Unable to set OLED scrolling text: {e}")
        gui.update_instruction(_("Failed to set text on OLED display."))
        return htf.PhaseResult.STOP

    oled_confirm = gui.prompt_user(
        _("Is there text on the OLED Screen ?"), [
            _("Yes"), _("No")])
    if oled_confirm == _("No"):
        test.logger.error(
            "TestOLEDDisplay Failed: Operator confirmed no text on OLED.")
        gui.update_instruction(_("Operator confirmed no text on OLED."))
        return htf.PhaseResult.STOP

    test.logger.info("Clearing OLED scrolling text.")
    gui.update_instruction(_("Clearing text from OLED display."))
    owl.SetOLEDScrollingText("")

    test.logger.info("TestOLEDDisplay Passed.")
    gui.update_instruction(_("OLED Display Test Passed successfully."))


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
    test.logger.info("Starting TestIMUAndKeysPresent Phase...")
    gui.update_instruction(_("Detecting IMU and Key devices..."))
    input_devices = owl.DiscoverEventDevices()
    key_devices = [
        device for device in input_devices.devices if device.device_type == "key"]
    # Gyros are also reported as "device_type" accelerometer
    accel_devices = [
        device for device in input_devices.devices if device.device_type == "accelerometer"]

    # There will never be >1 device of each type.
    accelerometer_present_local = False
    gyro_present_local = False
    for device in accel_devices:
        if "gsensor" in device.device_name:
            accelerometer_present_local = True
            test.state["accel_device"] = device
        elif "gyro" in device.device_name:
            gyro_present_local = True
            test.state["gyro_device"] = device

    for device in key_devices:
        if "adc-keys" in device.device_name:
            test.state["Function Key"] = device
        elif "gpio_keys" in device.device_name:
            test.state["Power Key"] = device

    test.measurements.accelerometer_present = accelerometer_present_local
    test.measurements.gyro_present = gyro_present_local
    test.measurements.num_keys = len(key_devices)

    if not accelerometer_present_local:
        test.logger.error(
            "TestIMUAndKeysPresent Failed: Accelerometer not detected.")
        gui.update_instruction(_("Accelerometer not detected."))
        return htf.PhaseResult.FAIL_AND_CONTINUE
    if not gyro_present_local:
        test.logger.error(
            "TestIMUAndKeysPresent Failed: Gyroscope not detected.")
        gui.update_instruction(_("Gyroscope not detected."))
        return htf.PhaseResult.FAIL_AND_CONTINUE
    if len(key_devices) == 0:
        test.logger.error(
            "TestIMUAndKeysPresent Failed: No key devices detected.")
        gui.update_instruction(_("No key devices detected."))
        return htf.PhaseResult.FAIL_AND_CONTINUE

    test.logger.info("TestIMUAndKeysPresent Passed.")
    gui.update_instruction(_("IMU and Key devices detected successfully."))


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("accelerometer_events_3s"),
    htf.Measurement("gyro_events_3s")
)
def TestIMUAccelGyro(test: htfTestApi, gui: GuiPlug, owl: OwlProberClient):
    try:
        test.logger.info("Starting TestIMUAccelGyro Phase...")
        gui.update_instruction(_("Starting Accelerometer & Gyro Test..."))
        accelerometer = test.state["accel_device"]
        gyro = test.state["gyro_device"]

        # Check if devices were identified in previous phase
        if not accelerometer:
            test.logger.error(
                "TestIMUAccelGyro Failed: Accelerometer device not found in state.")
            gui.update_instruction(_("Accelerometer not found."))
            return htf.PhaseResult.STOP
        if not gyro:
            test.logger.error(
                "TestIMUAccelGyro Failed: Gyroscope device not found in state.")
            gui.update_instruction(_("Gyroscope not found."))
            return htf.PhaseResult.STOP

        accel_report = owl.GetEventReportOverDuration(
            accelerometer.sysfs_path, duration_seconds=3)
        gyro_report = owl.GetEventReportOverDuration(
            gyro.sysfs_path, duration_seconds=3)
        accel_csv = pandas.read_csv(io.StringIO(accel_report.csv_report))
        gyro_csv = pandas.read_csv(io.StringIO(gyro_report.csv_report))

        test.measurements.accelerometer_events_3s = len(accel_csv)
        test.measurements.gyro_events_3s = len(gyro_csv)

        if len(accel_csv) == 0:
            test.logger.error(
                "TestIMUAccelGyro Failed: No accelerometer events detected.")
            gui.update_instruction(_("No accelerometer events detected."))
            return htf.PhaseResult.FAIL_AND_CONTINUE
        if len(gyro_csv) == 0:
            test.logger.error(
                "TestIMUAccelGyro Failed: No gyroscope events detected.")
            gui.update_instruction(_("No gyroscope events detected."))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        test.logger.info("TestIMUAccelGyro Passed.")
        gui.update_instruction(_("Accelerometer & Gyro Test Completed."))

    except KeyError as e:
        test.logger.error(
            f"TestIMUAccelGyro Failed: Missing device in state: {e}")
        gui.update_instruction(
            _("IMU devices not properly initialized. Check previous phases."))
        return htf.PhaseResult.STOP
    except Exception as e:
        test.logger.error(f"TestIMUAccelGyro Failed: {e}")
        gui.update_instruction(
            _("Accelerometer & Gyro Test Failed. Check logs for details."))
        return htf.PhaseResult.STOP


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.PhaseOptions(repeat_limit=2)
@htf.measures(
    htf.Measurement("function_key_pressed"),
    htf.Measurement("power_key_pressed")
)
def TestKeys(test: htfTestApi, gui: GuiPlug, owl: OwlProberClient):
    test.logger.info("Starting TestKeys Phase...")
    gui.update_instruction(_("Starting Keys Test..."))
    fn_key = test.state["Function Key"]
    pwr_key = test.state["Power Key"]

    gui.prompt_user(
        _("Get ready to press function (Orange) key when instructed"))
    gui.update_instruction(_("Press the function key (Orange key)"))
    fn_key_report = pandas.DataFrame()
    start_time = time.time()
    timeout = start_time + 60
    while (time.time() < timeout):
        fn_key_events = owl.GetEventReportOverDuration(
            fn_key.sysfs_path, duration_seconds=3)
        fn_key_report_str = io.StringIO(fn_key_events.csv_report)
        fn_key_report = pandas.concat(
            [fn_key_report, pandas.read_csv(fn_key_report_str)])
        if len(fn_key_report):
            gui.update_instruction(_("Key press detected"))
            test.measurements.function_key_pressed = True
            break
    if not test.measurements.function_key_pressed:
        return htf.PhaseResult.REPEAT

    gui.prompt_user(
        _("Get ready to power function (Black) key when instructed"))
    gui.update_instruction(_("Press the power key (Black key)"))
    pwr_key_events_report = pandas.DataFrame()
    start_time = time.time()
    timeout = start_time + 60
    while (time.time() < timeout):
        pwr_key_events = owl.GetEventReportOverDuration(
            pwr_key.sysfs_path, duration_seconds=3)
        pwr_key_event_str = io.StringIO(pwr_key_events.csv_report)
        pwr_key_events_report = pandas.concat(
            [pwr_key_events_report, pandas.read_csv(pwr_key_event_str)])
        if len(pwr_key_events_report):
            gui.update_instruction(_("Key press detected"))
            test.measurements.power_key_pressed = True
            break
    if not test.measurements.power_key_pressed:
        return htf.PhaseResult.REPEAT


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestBuzzer(test: htfTestApi, gui: GuiPlug, owl: OwlProberClient):
    test.logger.info("Starting TestBuzzer Phase...")
    gui.update_instruction(_("Starting Buzzer Sound Test..."))
    buzzer_path = "/sys/class/pwm/pwmchip3/pwm0/enable"
    try:
        owl.ConfigureBuzzer(buzzer_path)
        owl.SetBuzzer(True)
    except Exception as e:
        test.logger.error(
            f"TestBuzzer Failed: Unable to configure or set buzzer: {e}")
        gui.update_instruction(_("Buzzer setup failed. Check logs."))
        return htf.PhaseResult.STOP

    buzzer_audible = gui.prompt_user(
        _("Can you hear the Buzzer beeping ?"), [
            _("Yes"), _("No")])
    owl.SetBuzzer(False)
    if buzzer_audible == _("No"):
        test.logger.error(
            "TestBuzzer Failed: Operator confirmed buzzer not audible.")
        gui.update_instruction(_("Buzzer not audible."))
        return htf.PhaseResult.STOP

    test.logger.info("TestBuzzer Passed.")
    gui.update_instruction(_("Buzzer Sound test passed successfully."))


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("cpu_idle_percentage"),
    htf.Measurement("cpu_load_avg"),
    htf.Measurement("cpu_temp"),
    htf.Measurement("total_memory_kb")
)
def TestSystemState(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    test.logger.info("Starting TestSystemState Phase...")
    gui.update_instruction(_("Gathering system state information..."))
    try:
        system_state = owl.GetSystemState()
        test.measurements.cpu_temp = system_state.cpu_temperature
        test.measurements.cpu_idle_percentage = system_state.cpu_idle_percent
        test.measurements.cpu_load_avg = system_state.cpu_load_average
        test.measurements.total_memory_kb = system_state.total_memory_kb
        test.logger.info("TestSystemState Passed.")
        gui.update_instruction(_("System state gathered successfully."))
    except BaseException as e:
        test.logger.error(f"TestSystemState Failed: {e}")
        gui.update_instruction(_("Failed to gather system state. Check logs."))
        return htf.PhaseResult.FAIL_AND_CONTINUE


@htf.plug(owl=OwlProberClient)
@htf.plug(gui=GuiPlug)
def TestLEDs(test: htfTestApi, owl: OwlProberClient, gui: GuiPlug):
    test.logger.info("Starting TestLEDs Phase...")
    gui.update_instruction(_("Starting LED Test..."))

    red_led = "red_led"
    green_led = "green_led"
    blue_led = "blue_led"

    try:
        # Set to RED
        gui.update_instruction(_("Setting LED to Red."))
        owl.SetLEDColor(red_led, green_led, blue_led, 255, 0, 0, 0, 0, 0)
        response = gui.prompt_user(
            _("What colour is the LED ?"), [
                _("Red"), _("Green"), _("Blue")])
        if response != _("Red"):
            test.logger.error(
                "TestLEDs Failed: Operator reported incorrect LED color (Expected Red).")
            gui.update_instruction(_("Incorrect LED color (Expected Red)."))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        # Set to Green
        gui.update_instruction(_("Setting LED to Green."))
        owl.SetLEDColor(red_led, green_led, blue_led, 0, 255, 0, 0, 0, 0)
        response = gui.prompt_user(
            _("What colour is the LED ?"), [
                _("Red"), _("Green"), _("Blue")])
        if response != _("Green"):
            test.logger.error(
                "TestLEDs Failed: Operator reported incorrect LED color (Expected Green).")
            gui.update_instruction(_("Incorrect LED color (Expected Green)."))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        # Set to Blue
        gui.update_instruction(_("Setting LED to Blue."))
        owl.SetLEDColor(red_led, green_led, blue_led, 0, 0, 255, 0, 0, 0)
        response = gui.prompt_user(
            _("What colour is the LED ?"), [
                _("Red"), _("Green"), _("Blue")])
        if response != _("Blue"):
            test.logger.error(
                "TestLEDs Failed: Operator reported incorrect LED color (Expected Blue).")
            gui.update_instruction(_("Incorrect LED color (Expected Blue)."))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        # Set to Green and Blink
        gui.update_instruction(_("Setting LED to Green and Blinking."))
        owl.SetLEDColor(red_led, green_led, blue_led, 0, 255, 0, 0, 1, 0)
        response = gui.prompt_user(
            _("Is the LED Blinking?"), [
                _("Yes"), _("No")])
        if response == _("No"):
            test.logger.error(
                "TestLEDs Failed: Operator reported LED is not blinking.")
            gui.update_instruction(_("LED is not blinking."))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        test.logger.info("TestLEDs Passed.")
        gui.update_instruction(_("LED Test Passed successfully."))

    except Exception as e:
        test.logger.error(f"TestLEDs Failed: {e}")
        gui.update_instruction(_("LED Test Failed. Check logs for details."))
        return htf.PhaseResult.STOP


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

    test.logger.info("Starting IdentifyCamerasAndStopRecorder Phase...")
    gui.update_instruction(_("Identifying cameras and stopping recorder..."))

    cameras = dict()
    cameras["Left"] = "/dev/v4l-subdev4"
    cameras["Right"] = "/dev/v4l-subdev9"

    for key in cameras.keys():
        test.state[key] = cameras[key]

    left_cam_present_local = False
    right_cam_present_local = False

    for camera_name, camera_path in cameras.items():
        gui.update_instruction(_("Checking camera: {}").format(camera_name))
        command = "v4l2-ctl"
        args = f"-d {camera_path} --all".split(" ")
        result = owl.RunCommand(command,
                                args,
                                timeout_seconds=20,
                                use_shell=True
                                )
        if result.exit_code == 0 and 'User Controls' in result.stdout and 'Image Source Controls' in result.stdout:
            if camera_name == "Left":
                left_cam_present_local = True
            if camera_name == "Right":
                right_cam_present_local = True
            test.logger.info(
                f"Camera {camera_name} detected at {camera_path}.")
        else:
            test.logger.warning(
                f"Camera {camera_name} NOT detected at {camera_path}. Output: {
                    result.stdout.strip()} Error: {
                    result.stderr.strip()}")

    test.measurements.left_cam_present = left_cam_present_local
    test.measurements.right_cam_present = right_cam_present_local

    if not left_cam_present_local:
        test.logger.error(
            "IdentifyCamerasAndStopRecorder Failed: Left camera not present.")
        gui.update_instruction(_("Left camera not detected."))
        return htf.PhaseResult.FAIL_AND_CONTINUE
    if not right_cam_present_local:
        test.logger.error(
            "IdentifyCamerasAndStopRecorder Failed: Right camera not present.")
        gui.update_instruction(_("Right camera not detected."))
        return htf.PhaseResult.FAIL_AND_CONTINUE

    gui.update_instruction(_("Stopping recorder if running..."))
    owl.RunCommand("RkLunch-stop.sh", [], use_shell=True)
    test.logger.info("IdentifyCamerasAndStopRecorder Passed.")
    gui.update_instruction(_("Cameras identified and recorder stopped."))

    # Update CamIni
    gui.update_instruction(_("Updating cam configuration files..."))
    resolved_cam_ini_path = get_resource_path(CONF.cam_ini_path)
    for file in os.listdir(resolved_cam_ini_path):
        source_file_path = os.path.join(resolved_cam_ini_path, file)
        result = dut.adb_push(source_file_path, "/userdata/rkadk")
        if not result.is_success:
            return htf.PhaseResult.STOP
    gui.update_instruction(_("Completed upload of cam configuration files..."))

    return htf.PhaseResult.CONTINUE


@htf.plug(owl=OwlProberClient)
@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("left_cam_fps"),
    htf.Measurement("left_cam_exposure"),
    htf.Measurement("left_cam_aibnr"),
    htf.Measurement("left_cam_tnr"),
    htf.Measurement("left_cam_cnr"),
    htf.Measurement("right_cam_fps"),
    htf.Measurement("right_cam_exposure"),
    htf.Measurement("right_cam_aibnr"),
    htf.Measurement("right_cam_tnr"),
    htf.Measurement("right_cam_cnr")
)
def TestCamerasDarkPhoto(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        gui: GuiPlug,
        owl: OwlProberClient):
    test.logger.info("Starting TestCamerasDarkPhoto Phase...")
    gui.update_instruction(_("Testing cameras with dark photos..."))

    cameras = dict()
    cameras["Left"] = {"v4l-dev": test.state["Left"], "cam_idx": 1}
    cameras["Right"] = {"v4l-dev": test.state["Right"], "cam_idx": 0}

    for camera_name, details in cameras.items():
        gui.update_instruction(
            _("Preparing for {} camera dark photo.").format(camera_name))
        command = "rkadk_photo_test"
        args = [f"-I {details["cam_idx"]}", "-p /userdata/rkadk"]
        keys_to_send = "\n quit\n"
        gui.prompt_user(
            _("Cover {} camera for taking dark photo. Click ok when ready").format(camera_name))

        test.logger.info(
            f"Clearing existing temporary photos for {camera_name}...")
        owl.RunCommand("rm", ["-rf", "/tmp/*.jpeg"], use_shell=True)

        test.logger.info(f"Taking dark photo with {camera_name} camera...")
        gui.update_instruction(
            _("Taking dark photo with {} camera.").format(camera_name))
        photo_result = owl.RunCommand(command,
                                      args,
                                      timeout_seconds=CONF.camera_cmd_timeout,
                                      stdin_data=keys_to_send,
                                      use_shell=True
                                      )
        if photo_result.exit_code != 0:
            test.logger.error(
                f"TestCamerasDarkPhoto Failed: Failed to take photo with {camera_name} camera. " f"Stdout: {
                    photo_result.stdout.strip()}, Stderr: {
                    photo_result.stderr.strip()}")
            gui.update_instruction(
                _("Failed to take dark photo with {} camera.").format(camera_name))
            return htf.PhaseResult.FAIL_AND_CONTINUE

        dst_filename = f"DarkPhotoTest{camera_name}.jpeg"
        test.logger.info(f"Downloading photo from {camera_name} camera...")
        gui.update_instruction(
            _("Downloading dark photo from {} camera.").format(camera_name))
        try:
            photo_file = owl.DownloadFile(
                "/tmp/PhotoTest_0.jpeg",
                tempfile.gettempdir(),
                dst_filename)
            test.attach(
                name=dst_filename,
                binary_data=io.open(photo_file, mode='rb').read(),
                mimetype="image/jpeg"
            )
            test.logger.info(
                f"Photo from {camera_name} camera downloaded to {photo_file}.")
        except Exception as e:
            test.logger.error(
                f"TestCamerasDarkPhoto Failed: Failed to download photo from {camera_name} camera: {e}")
            gui.update_instruction(
                _("Failed to download dark photo from {} camera.").format(camera_name))
            return htf.PhaseResult.FAIL_AND_CONTINUE

    camera_params = get_camera_parameters(owl)
    test.measurements.left_cam_fps = camera_params["Left Camera"]["fps"]
    test.measurements.left_cam_exposure = camera_params["Left Camera"]["exposure_time"]
    test.measurements.left_cam_aibnr = camera_params["Left Camera"]["aibnr"]
    test.measurements.left_cam_tnr = camera_params["Left Camera"]["tnr"]
    test.measurements.left_cam_cnr = camera_params["Left Camera"]["cnr"]

    test.measurements.right_cam_fps = camera_params["Right Camera"]["fps"]
    test.measurements.right_cam_exposure = camera_params["Right Camera"]["exposure_time"]
    test.measurements.right_cam_aibnr = camera_params["Right Camera"]["aibnr"]
    test.measurements.right_cam_tnr = camera_params["Right Camera"]["tnr"]
    test.measurements.right_cam_cnr = camera_params["Right Camera"]["cnr"]

    if camera_params is None:
        return htf.PhaseResult.STOP
    test.logger.info("TestCamerasDarkPhoto Passed.")
    gui.update_instruction(_("Camera dark photo test passed successfully."))


@htf.plug(owl=OwlProberClient)
@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("sdcard_present"),
    htf.Measurement("sdcard_filesystem"),
    htf.Measurement("sdcard_total_size"),
    htf.Measurement("sdcard_available_size"),
    htf.Measurement("sdcard_read_speed"),
    htf.Measurement("sdcard_write_speed")
)
def TestSDCard(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        owl: OwlProberClient,
        gui: GuiPlug):

    # --- 1. DETECTION PHASE ---
    gui.update_instruction(_("Verifying if SDCard is mounted..."))

    # We grep for sdcard directly in the command to simplify parsing
    check_sd_card = owl.RunCommand(
        "df -hT | grep -i sdcard", [], use_shell=True)

    if not check_sd_card.stdout.strip():
        gui.update_instruction(_("SD Card not found!"))
        test.measurements.sdcard_present = False
        return htf.PhaseResult.FAIL_AND_CONTINUE

    # Parsing the DF output
    # Expected: Filesystem Type Size Used Avail Use% Mounted on
    # Example: /dev/block/mmcblk1p1 vfat 29G 1.2G 28G 4% /storage/sdcard1
    parts = re.split(r'\s+', check_sd_card.stdout.strip())

    if len(parts) < 6:
        test.logger.error(f"Failed to parse df output: {check_sd_card.stdout}")
        test.measurements.sdcard_present = False
        return htf.PhaseResult.FAIL_AND_CONTINUE

    sdcard_info = {
        "filesystem": parts[0],
        "type": parts[1],
        "size": parts[2],
        "used": parts[3],
        "available": parts[4],
        "use_percent": parts[5],
        # Grab the last part as mount point (handles cases with missing columns
        # slightly better)
        "mount_point": parts[-1]
    }

    test.measurements.sdcard_present = True
    test.measurements.sdcard_filesystem = sdcard_info["type"]
    test.measurements.sdcard_total_size = convert_unit_suffix(
        sdcard_info["size"])
    test.measurements.sdcard_available_size = convert_unit_suffix(
        sdcard_info["available"])

    mount_point = sdcard_info["mount_point"]
    test.logger.info(f"SD Card detected at: {mount_point}")

    # --- 2. CLEANUP PHASE ---
    # Removes the 'video' folder as done in the original script
    gui.update_instruction(_("Cleaning up old files..."))
    owl.RunCommand(f"rm -rf {mount_point}/video", [], use_shell=True)

    # --- 3. WRITE TEST ---
    gui.update_instruction(_("Running Write Speed Test..."))

    # Use 'dd' to write 64MB (16 blocks of 4MB)
    # conv=fsync ensures data is physically written, not just cached
    temp_file = f"{mount_point}/temp_test_file"
    write_cmd = f"dd if=/dev/zero of={temp_file} bs=4M count=16 conv=fsync"

    write_res = owl.RunCommand(write_cmd, [], use_shell=True)
    if write_res.exit_code != 0:
        test.logger.error(f"Write test failed: {write_res.stderr}")
        return htf.PhaseResult.FAIL_AND_CONTINUE

    # Parse Speed: "16+0 records in ... 15.4 MB/s"
    # Regex handles both "MB/s" and "GB/s"
    speed_match = re.search(r', ([\d.]+)\s*([KMG]B)/s', write_res.stderr)
    # Note: 'dd' usually prints stats to stderr, not stdout

    if speed_match:
        speed_val = float(speed_match.group(1))
        unit = speed_match.group(2)

        # Normalize to MB/s if needed
        if unit == "GB":
            speed_val *= 1024
        elif unit == "KB":
            speed_val /= 1024

        test.measurements.sdcard_write_speed = speed_val
        test.logger.info(f"Write Speed: {speed_val} MB/s")
    else:
        test.logger.warning("Could not parse write speed from output.")

    # --- 4. READ TEST ---
    gui.update_instruction(_("Running Read Speed Test..."))

    # Read back the temp file we just created
    read_cmd = f"dd if={temp_file} of=/dev/null bs=1M count=16"
    read_res = owl.RunCommand(read_cmd, [], use_shell=True)

    if read_res.exit_code != 0:
        test.logger.error("Read test failed.")
    else:
        # Parse Speed
        speed_match = re.search(r', ([\d.]+)\s*([KMG]B)/s', read_res.stderr)
        if speed_match:
            speed_val = float(speed_match.group(1))
            unit = speed_match.group(2)

            if unit == "GB":
                speed_val *= 1024
            elif unit == "KB":
                speed_val /= 1024

            test.measurements.sdcard_read_speed = speed_val
            test.logger.info(f"Read Speed: {speed_val} MB/s")

    # --- 5. FINAL CLEANUP ---
    gui.update_instruction(_("Cleaning up temp files..."))
    owl.RunCommand(f"rm {temp_file}", [], use_shell=True)

    gui.update_instruction(_("SD Card Test Complete"))


def get_camera_parameters(owl: OwlProberClient):
    dumpcam_content = {}
    # To run dumpcam we first need rkaiq server running.
    owl.RunCommand("RkLunch.sh", [""], use_shell=True)
    # Get FPS, Exposure and Resolution
    dumpcam_run = owl.RunCommand("dumpcam", ["hwi"], use_shell=True)
    dumpcam_content = dumpcam_run.stdout
    return_params = {}
    if len(dumpcam_content):
        cam_dumps = [dump for dump in dumpcam_content.split(
            "╔") if "HWI -> sensor" in dump]
        if len(cam_dumps) == 2:
            return_params["Right Camera"] = parse_dumpcam_hwi(cam_dumps[0])
            return_params["Left Camera"] = parse_dumpcam_hwi(cam_dumps[1])

    # Get TNR
    dumpcam_run = owl.RunCommand("dumpcam", ["tnr"], use_shell=True)
    dumpcam_content = dumpcam_run.stdout
    if len(dumpcam_content):
        cam_dumps = [dump for dump in dumpcam_content.split(
            "╔") if "Module: tnr" in dump]
        return_params["Right Camera"] = {
            "tnr": parse_dumpcam_cnr_tnr(
                cam_dumps[0]),
            **return_params["Right Camera"]}
        return_params["Left Camera"] = {
            "tnr": parse_dumpcam_cnr_tnr(
                cam_dumps[1]),
            **return_params["Left Camera"]}

    # Get CNR
    dumpcam_run = owl.RunCommand("dumpcam", ["cnr"], use_shell=True)
    dumpcam_content = dumpcam_run.stdout
    if len(dumpcam_content):
        cam_dumps = [dump for dump in dumpcam_content.split(
            "╔") if "Module: cnr" in dump]
        return_params["Right Camera"] = {
            "cnr": parse_dumpcam_cnr_tnr(
                cam_dumps[0]),
            **return_params["Right Camera"]}
        return_params["Left Camera"] = {
            "cnr": parse_dumpcam_cnr_tnr(
                cam_dumps[1]),
            **return_params["Left Camera"]}

    # Get AIBNR. It is a different format
    dumpcam_run = owl.RunCommand("dumpcam", ["aibnr"], use_shell=True)
    dumpcam_content = dumpcam_run.stdout
    string_to_search = "working mode="
    if len(dumpcam_content):
        cam_dumps = [dump for dump in dumpcam_content.splitlines()
                     if string_to_search in dump]
        if len(cam_dumps) == 2:
            # Should be same for both cameras.
            idx = cam_dumps[0].find(string_to_search) + len(string_to_search)
            return_params["Right Camera"] = {
                "aibnr": cam_dumps[0][idx:].split()[0] == '1', **return_params["Right Camera"]}
            return_params["Left Camera"] = {
                "aibnr": cam_dumps[1][idx:].split()[0] == '1', **return_params["Left Camera"]}

    owl.RunCommand("RkLunch-stop.sh", [""], use_shell=True)
    return return_params


@htf.plug(owl=OwlProberClient)
@htf.plug(dut=ADBDutControllerPlug)
@htf.plug(gui=GuiPlug)
@htf.measures(
    htf.Measurement("batt_present"),
    htf.Measurement("batt_millivolts"),
    htf.Measurement("batt_milliamps"),
    htf.Measurement("batt_temperature"),
    htf.Measurement("batt_charging_verified"),
    htf.Measurement("batt_discharging_verified")
)
def TestBatteryPhase(
        test: htfTestApi,
        dut: ADBDutControllerPlug,
        owl: OwlProberClient,
        gui: GuiPlug):
    owl.ConfigureBattery("cw221X-bat",
                         voltage_node="voltage_now",
                         current_node="current_now",
                         temp_node="hwmon2/temp1_input")

    gui.update_instruction(_("Getting battery reading"))
    batt_details = owl.GetBatteryReadings()
    test.measurements.batt_present = batt_details.present
    test.measurements.batt_temperature = batt_details.celsius_temperature / 100
    test.measurements.batt_millivolts = batt_details.millivolts
    test.measurements.batt_milliamps = batt_details.milliamps

    test.state["batt_state"] = batt_details.status
    if batt_details.status == "Charging":
        test.measurements.batt_charging_verified = True
    else:
        return htf.PhaseResult.STOP
    gui.update_instruction(_("Verified battery is charging"))

    gui.prompt_user(_("Disconnect pogo connector to device"))
    batt_details = owl.GetBatteryReadings()
    if batt_details.status == "Discharging":
        test.measurements.batt_discharging_verified = True

    gui.prompt_user(_("Reconnect pogo connector to device"))

    # Poll for return
    gui.update_instruction(_("Polling for device recovery after reboot..."))
    start_time = time.time()
    deadline = start_time + 60
    # Give the device some time to come up and stabilise.

    while time.time() < deadline:
        # 1. Fast Connectivity Check
        res = dut.run_adb_cmd(['shell', 'echo 1'], timeout=5)
        if res.is_success:
            break
        time.sleep(1)

    result = dut.run_adb_cmd(
        ["shell", f"chmod +x {CONF.dev_prober_path}/owl_prober"])
    if not result.is_success:
        test.logger.error(
            f"TestBattery Failed: Unable to restart owl_prober.")
        gui.update_instruction(_("Failed to restart device controller."))
        return htf.PhaseResult.STOP
