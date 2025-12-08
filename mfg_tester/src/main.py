import sys
import openhtf as htf
from openhtf.util.configuration import CONF
from openhtf.plugs import user_input
from openhtf.output.callbacks import json_factory
from tofupilot.openhtf import TofuPilot
from phases.setup_phase import setup_adb_connection, bringup_wifi

CONF.declare('dut_port', default_value=8443,
             description='Port for Go Agent on DUT')
CONF.declare("use_remote_adb", default_value=True,description="Use remote ADB host")
CONF.declare('adb_host', default_value="mahesh-deskpi",
             description='Hostname of ADB device')
CONF.declare('adb_host_port', default_value=5037, description='ADB Port')
CONF.declare('max_cmd_retry', default_value=3, description="How many times to retry a command")
CONF.declare('adb_timeout', default_value=30, description="Timeout in secs for running adb commands")
CONF.declare('remote_cmd_timeout', default_value=30, description="Timeout in secs for remote commands")
CONF.declare('cmd_retry_interval', default_value=2, description="Time is secs to wait before retrying")
CONF.declare("scripts_path",description="Path to find device scripts")
CONF.declare("wifi_scan_networks", description="Wifi networks that should be present in wifi scan")
CONF.declare('ssh_user', default_value="root",
             description='Username for SSH connection to remote ADB host.')
CONF.declare('ssh_private_key_path', default_value=None,
             description='Path to SSH private key file for remote ADB host (e.g., ~/.ssh/id_rsa).')
CONF.declare('ssh_port', default_value=22,
             description='Port for SSH connection to remote ADB host.')
CONF.declare('grpc_agent_port', default_value=50051,
             description='Port for the gRPC agent on the device.')
CONF.declare('grpc_connection_timeout_seconds', default_value=10,
             description='Timeout for gRPC agent connection and initial RPCs.')

if __name__ == "__main__":
    
    with open("mfg_tester/config/station.yaml","r") as station_cfg:
        CONF.load_from_file(station_cfg)
    
    test = htf.Test(setup_adb_connection, bringup_wifi,
    procedure_id="94b63dd8-ce0b-11f0-981b-0fecd78cd24f",
    part_number="scriptTest01"
    )
    with TofuPilot(test):
        test.execute(test_start=user_input.prompt_for_test_start("Please scan device id for test to start:"))
