import sys
import openhtf as htf
from openhtf.util.configuration import CONF
from openhtf.output.callbacks import json_factory
from tofupilot.openhtf import TofuPilot
from phases.setup_phase import setup_phase, copy_test_agent

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


if __name__ == "__main__":
    
    with open("config/station.yaml","r") as station_cfg:
        CONF.load_from_file(station_cfg)
    
    test = htf.Test(setup_phase,copy_test_agent,
    procedure_id="94b63dd8-ce0b-11f0-981b-0fecd78cd24f",
    part_number="scriptTest01"
    )
    with TofuPilot(test):
        test.execute()
