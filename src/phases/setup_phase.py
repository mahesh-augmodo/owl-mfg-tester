import openhtf as htf
from plugs.DutController import ADBDutControllerPlug
from utils.command_result import CommandResult
from openhtf.core.test_descriptor import TestApi as htfTestApi

@htf.plug(dut=ADBDutControllerPlug)
def setup_phase(test: htfTestApi, dut):
    """Phase that runs the provisioning logic."""
    test.logger.info("Starting Provisioning...")
    # We call the method on the instance OpenHTF created for us
    provision_result: CommandResult = dut.provision_via_adb()
    
    if not provision_result.is_success:
        return htf.PhaseResult.STOP
    
    test.test_record.dut_id=dut.device_id
    return htf.PhaseResult.CONTINUE

@htf.plug(dut=ADBDutControllerPlug)
def copy_test_agent(test: htfTestApi, dut: ADBDutControllerPlug):
    """Phase that copies over the test server"""
    result = dut.adb_push("resource/bin/dut_test_agent","/tmp",test.test_record.dut_id)
    if result.is_success:
        test.logging.info("Copied testAgent to device %s",test.test_record.dut_id)
        return htf.PhaseResult.CONTINUE
    return htf.PhaseResult.STOP