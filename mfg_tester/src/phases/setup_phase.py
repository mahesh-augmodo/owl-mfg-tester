import openhtf as htf
from openhtf.util.configuration import CONF
from plugs.DutController import ADBDutControllerPlug
from utils.command_result import CommandResult
from openhtf.core.test_descriptor import TestApi as htfTestApi
import ipaddress
import re

def is_valid_ip(ip_string):
    """Returns True if the input string is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

@htf.plug(dut=ADBDutControllerPlug)
def setup_adb(test: htfTestApi, dut):
    """Phase that runs the provisioning logic."""
    test.logger.info("Starting Provisioning...")
    # We call the method on the instance OpenHTF created for us
    dut.device_id = test.test_record.dut_id
    provision_result: CommandResult = dut.provision_via_adb()
    
    if not provision_result.is_success:
        return htf.PhaseResult.STOP

@htf.plug(dut=ADBDutControllerPlug)
@htf.measures(
    htf.Measurement("ip_address").with_validator(is_valid_ip)
)
def bringup_wifi(test: htf.TestApi, dut):
    result: CommandResult = dut.bringup_wifi_on_device()
    TestWifiNetworks = CONF.wifi_scan_networks
    if result.is_success:
        for wifiname in TestWifiNetworks:
            if wifiname not in result.full_output:
                test.logger.error("Cannot find test WiFi networks in network scan")
                return htf.PhaseResult.STOP

        # Let's find the IP Address
        ip_address_search = re.search(r'Device.IP.Address.=.([0-9.]+)*', result.full_output)
        test.measurements.ip_address = ip_address_search.group(1)
    
    test.logger.info("Wifi is up, and test networks have been found in network scan")
    return htf.PhaseResult.CONTINUE