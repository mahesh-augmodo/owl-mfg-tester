from utils.bundle_utils import get_resource_path
from ui_app import ui_main
from phases.owl1_phases import ConnectToDeviceViaADB, \
    ConnectToFactoryWifi, \
    ScanWifiNetworks, \
    DeployAndConnectToOwlProber, \
    TestOLEDDisplay, \
    TestRTC, \
    PushTestScriptsToDevice, \
    TestIMUAndKeysPresent, \
    TestIMUAccelGyro, \
    IdentifyCamerasAndStopRecorder, \
    TestCamerasDarkPhoto, \
    TestSystemState, \
    TestLEDs, \
    TestKeys, \
    TestBuzzer, \
    TestSDCard, \
    TestBatteryPhase
from utils.verbose_console_summary import VerboseConsoleSummary
from openhtf.output.callbacks import json_factory
from utils.limits_loader import apply_limits_to_test
from openhtf.util.configuration import CONF
import openhtf as htf
import os
import sys
import inspect

# --- START FIX FOR OPENHTF / PYINSTALLER ---
# OpenHTF tries to read source code, which doesn't exist in a frozen app.
# We override inspect.getsourcelines to return a placeholder instead of
# crashing.
if getattr(sys, 'frozen', False):
    def _frozen_getsourcelines(object):
        return (["# Source code not available in frozen application\n"], 1)

    inspect.getsourcelines = _frozen_getsourcelines


class NullWriter:
    def write(self, text):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False

    # This fixes the "no attribute 'mode'" error
    @property
    def mode(self):
        return 'w'

    # Adding encoding prevents future errors if a library checks for it
    @property
    def encoding(self):
        return 'utf-8'


if sys.stdout is None:
    sys.stdout = NullWriter()

if sys.stderr is None:
    sys.stderr = NullWriter()


# Import the new UI application's main entry point

CONF.declare('dut_port', default_value=50051,
             description='Port for Go Agent on DUT')
CONF.declare(
    "use_remote_adb",
    default_value=True,
    description="Use remote ADB host")
CONF.declare('adb_host', default_value="mahesh-deskpi",
             description='Hostname of ADB device')
CONF.declare('adb_host_port', default_value=5037, description='ADB Port')
CONF.declare(
    'max_cmd_retry',
    default_value=3,
    description="How many times to retry a command")
CONF.declare(
    'adb_timeout',
    default_value=30,
    description="Timeout in secs for running adb commands")
CONF.declare(
    'camera_cmd_timeout',
    default_value=60,
    description="Timeout in secs for camera commands run on the device")
CONF.declare('remote_cmd_timeout', default_value=30,
             description="Timeout in secs for remote commands")
CONF.declare('cmd_retry_interval', default_value=2,
             description="Time is secs to wait before retrying")
CONF.declare("scripts_path", description="Path to find device scripts")
CONF.declare(
    "cam_ini_path",
    description="The path on the host where the ini files for the camera are located")
CONF.declare("owl_prober_path", default_value="resources",
             description="Path on host where owl_prober binary is located.")
CONF.declare("dev_prober_path", default_value="/tmp/",
             description="Path on device where files are copied to.")
CONF.declare("wifi_connect_script", description="Name of wifi connect script")
CONF.declare("wifi_scan_script", description="Name of wifi scan script")
CONF.declare(
    "wifi_scan_networks",
    description="Wifi networks that should be present in wifi scan")
CONF.declare('ssh_user', default_value="root",
             description='Username for SSH connection to remote ADB host.')
CONF.declare(
    'ssh_private_key_path',
    default_value=None,
    description='Path to SSH private key file for remote ADB host (e.g., ~/.ssh/id_rsa).')
CONF.declare('ssh_port', default_value=22,
             description='Port for SSH connection to remote ADB host.')
CONF.declare('grpc_agent_port', default_value=50051,
             description='Port for the gRPC agent on the device.')
CONF.declare('grpc_connection_timeout_seconds', default_value=10,
             description='Timeout for gRPC agent connection and initial RPCs.')
CONF.declare('wifi_ssid',
             description='Wifi factory network.')
CONF.declare('wifi_password',
             description='Wifi password for factory network.')
CONF.declare("reports_dir", default_value="reports/",
             description="Directory where the test reports are stored.")


def build_cli_htf_test_suite():
    """Builds the OpenHTF test suite for CLI execution."""
    # Load configuration
    config_file = get_resource_path('config/station.yaml')
    with open(config_file, "r") as station_cfg:
        CONF.load_from_file(station_cfg)

    # Return the OpenHTF test instance
    test = htf.Test(ConnectToDeviceViaADB,
                    TestRTC,
                    PushTestScriptsToDevice,
                    ConnectToFactoryWifi,
                    ScanWifiNetworks,
                    DeployAndConnectToOwlProber,
                    TestBatteryPhase,
                    TestSDCard,
                    TestSystemState,
                    TestIMUAndKeysPresent,
                    TestKeys,
                    TestIMUAccelGyro,
                    TestLEDs,
                    TestOLEDDisplay,
                    TestBuzzer,
                    IdentifyCamerasAndStopRecorder,
                    TestCamerasDarkPhoto)

    limits_file = get_resource_path("config/limits.yaml")
    apply_limits_to_test(test, limits_file)

    # Determine reports path based on execution environment
    reports_path = CONF.reports_dir
    if getattr(sys, 'frozen', False):
        # When bundled, save reports to AppData to ensure write permissions
        # and avoid issues with running from read-only locations.
        reports_path = os.path.join(
            os.environ['APPDATA'],
            'OwlMfgTester',
            CONF.reports_dir)

    # Ensure the path is absolute and the directory exists.
    reports_path = os.path.abspath(reports_path)
    if not os.path.isdir(reports_path):
        os.makedirs(reports_path)
        print(f"Creating reports directory at {reports_path}")

    json_filename = os.path.join(reports_path,
                                 "{dut_id}_{outcome}_{start_time_millis}.json")

    test.add_output_callbacks(
        json_factory.OutputToJSON(json_filename, indent=4)
    )
    return test


if __name__ == "__main__":
    if "--cli" in sys.argv:
        # Run the OpenHTF test in CLI mode
        # Remove the argument to avoid issues with other parsers
        sys.argv.remove("--cli")
        test = build_cli_htf_test_suite()
        test.execute()
    else:
        # Run the PyQt6 UI application, passing the test factory
        ui_main.main(test_factory=build_cli_htf_test_suite)
