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
def setup_adb_connection(test: htfTestApi, dut: ADBDutControllerPlug):
    """Phase that runs the provisioning logic."""
    test.logger.info("Starting Provisioning...")
    # We call the method on the instance OpenHTF created for us
    dut.device_id = test.test_record.dut_id

    adb_conn_result = dut.setup_adb_test_connection()
    if not adb_conn_result.is_success:
        test.logger.error(
            f"ADB connection setup failed: {adb_conn_result.error_message}")
        return htf.PhaseResult.STOP

    push_scripts_result = dut.push_scripts_to_device()
    if not push_scripts_result.is_success:
        test.logger.error(
            f"Pushing scripts to device failed: {push_scripts_result.error_message}")
        return htf.PhaseResult.STOP

    return htf.PhaseResult.CONTINUE


@htf.plug(dut=ADBDutControllerPlug)
@htf.measures(
    htf.Measurement("ip_address").with_validator(is_valid_ip)
)
def bringup_wifi(test: htf.TestApi, dut):
    wifi_result: CommandResult = dut.bringup_wifi_on_device()
    if not wifi_result.is_success:
        test.logger.error(f"Wifi bringup failed: {wifi_result.error_message}")
        return htf.PhaseResult.STOP

    TestWifiNetworks = CONF.wifi_scan_networks
    if wifi_result.is_success:
        for wifiname in TestWifiNetworks:
            if wifiname not in wifi_result.full_output:
                test.logger.error(
                    "Cannot find test WiFi networks in network scan")
                return htf.PhaseResult.STOP

        # Let's find the IP Address
        ip_address_search = re.search(
            r'Device.IP.Address.=.([0-9.]+)*', wifi_result.full_output)
        if ip_address_search:
            test.measurements.ip_address = ip_address_search.group(1)
        else:
            test.logger.error(
                "Could not find IP address in WiFi bringup output.")
            return htf.PhaseResult.STOP

    test.logger.info(
        "Wifi is up, and test networks have been found in network scan")
    return htf.PhaseResult.CONTINUE
