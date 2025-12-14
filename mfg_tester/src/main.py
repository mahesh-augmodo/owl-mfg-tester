import sys
import openhtf as htf
from openhtf.util.configuration import CONF
from openhtf.plugs import user_input
from utils.limits_loader import apply_limits_to_test
from openhtf.output.callbacks import json_factory
from utils.verbose_console_summary import VerboseConsoleSummary
# from tofupilot.openhtf import TofuPilot  # Commented out for now,
# re-evaluate if needed for UI
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
    TestLEDs

# Import the new UI application's main entry point
from ui_app import ui_main

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


def build_cli_htf_test_suite():
    """Builds the OpenHTF test suite for CLI execution."""
    # Load configuration
    with open("config/station.yaml", "r") as station_cfg:
        CONF.load_from_file(station_cfg)

    # Return the OpenHTF test instance
    test = htf.Test(ConnectToDeviceViaADB,
                    TestRTC,
                    PushTestScriptsToDevice,
                    ConnectToFactoryWifi,
                    ScanWifiNetworks,
                    DeployAndConnectToOwlProber,
                    TestSystemState,
                    TestIMUAndKeysPresent,
                    TestIMUAccelGyro,
                    TestLEDs,
                    TestOLEDDisplay,
                    IdentifyCamerasAndStopRecorder,
                    TestCamerasDarkPhoto,
                    procedure_id="94b63dd8-ce0b-11f0-981b-0fecd78cd24f",
                    part_number="scriptTest01")

    apply_limits_to_test(test, "config/limits.yaml")

    test.add_output_callbacks(
        json_factory.OutputToJSON(
            "reports/{dut_id}_{outcome}_{start_time_millis}.json",
            indent=4
        ),
        VerboseConsoleSummary()
    )
    return test


if __name__ == "__main__":
    if "--cli" in sys.argv:
        # Run the OpenHTF test in CLI mode
        # Remove the argument to avoid issues with other parsers
        sys.argv.remove("--cli")
        test = build_cli_htf_test_suite()
        # Ensure TofuPilot is imported if actually needed for CLI execution
        from tofupilot.openhtf import TofuPilot
        with TofuPilot(test):
            test.execute(test_start=user_input.prompt_for_test_start(
                "Please scan device id for test to start:"))
    else:
        # Run the PyQt6 UI application, passing the test factory
        ui_main.main(test_factory=build_cli_htf_test_suite)
