import sys
import openhtf as htf
from openhtf.util.configuration import CONF
from openhtf.output.callbacks import json_factory
from plugs.DutController import DutControllerPlug

CONF.declare('dut_port', default_value=8443,
             description='Port for Go Agent on DUT')
CONF.declare("use_remote_adb", default_value=True,description="Use remote ADB host")
CONF.declare('adb_host', default_value="mahesh-deskpi",
             description='Hostname of ADB device')
CONF.declare('adb_host_port', default_value=5037, description='ADB Port')
CONF.declare('max_cmd_retry', default_value=3, description="How many times to retry a command")
CONF.declare('remote_cmd_timeout', default_value=30, description="Timeout in secs for remote commands")


@htf.plug(dut=DutControllerPlug)
def setup_phase(test, dut):
    """Phase that runs the provisioning logic."""
    test.logger.info("Starting Provisioning...")
    # We call the method on the instance OpenHTF created for us
    dut.provision_via_adb()
    test.test_record.dut_id = dut.dut_id


if __name__ == "__main__":
    
    with open("config/station.yaml","r") as station_cfg:
        CONF.load_from_file(station_cfg)
    
    test = htf.Test(setup_phase)
    test.execute()
