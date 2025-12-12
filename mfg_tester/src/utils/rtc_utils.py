import time
import re
from datetime import datetime, timedelta


def set_device_time(dut, logger):
    """
    Sets device time using the BusyBox-compatible format MMDDhhmmYYYY.ss
    """
    now_utc = datetime.utcnow()

    # [FIX] Changed from "%Y%m%d.%H%M%S" to "%m%d%H%M%Y.%S"
    # Matches your successful manual command: 121111552025.05
    time_str = now_utc.strftime("%m%d%H%M%Y.%S")

    logger.info(f"Setting device time to UTC: {time_str}")

    # We use -u because your manual test used it successfully
    # Command: date -u 121111552025.05
    res = dut.run_adb_cmd(["shell", f"date -u {time_str}"])

    if not res.is_success:
        logger.error(f"Date command failed: {res.stderr}")
        raise RuntimeError("Failed to set device date")

    # 4. Write to Hardware
    dut.run_adb_cmd(["shell", "hwclock -w"])

    # 5. Measure Initial Offset (as discussed before)
    host_check_time = time.time()
    dev_time_check = dut._get_device_time_precise()

    initial_drift = 0.0
    if dev_time_check:
        initial_drift = (
            dev_time_check -
            datetime.utcfromtimestamp(host_check_time)).total_seconds()
        logger.info(f"Initial Latency/Offset measured: {initial_drift:.4f}s")

    return {
        "device_time_obj": now_utc,
        "host_time_epoch": host_check_time,
        "initial_offset": initial_drift
    }


def get_rtc_drift(dut, ref_data, timeout_s=60, logger=None):
    """
    Polls for device availability and calculates drift with VERBOSE logging.
    """
    start_time = time.time()
    deadline = start_time + timeout_s
    # Give the device some time to come up and stabilise.

    while time.time() < deadline:
        # 1. Fast Connectivity Check
        res = dut.run_adb_cmd(['shell', 'echo 1'], timeout=5)
        if not res.is_success:
            time.sleep(1)
            continue

        # 2. Read HW Clock
        dev_time = dut._get_device_time_precise()

        # 3. Capture Host Time IMMEDIATELY after receiving ADB response
        host_now = time.time()

        # 4. Calculate Expected Time
        host_now = time.time()
        host_elapsed = host_now - ref_data['host_time_epoch']

        # Expected Time = Original_Ref + Elapsed + INITIAL_OFFSET
        # We expect the device to maintain that initial -8s gap, not magically
        # fix it.
        expected_dev_time = ref_data['device_time_obj'] + \
            timedelta(seconds=host_elapsed)

        # Adjust expectation by the initial latency we measured
        expected_dev_time += timedelta(seconds=ref_data['initial_offset'])

        # 5. The Drift
        # Now, 'drift' represents ONLY the time lost during reboot/sleep
        drift = (dev_time - expected_dev_time).total_seconds()

        # --- DEBUG LOGGING ---
        if logger:
            logger.debug(f"--- RTC DEBUG CALCULATION ---")
            logger.debug(
                f"[1] Original Set Time (Device): {
                    ref_data['device_time_obj']}")
            logger.debug(
                f"[2] Host Elapsed Time:          {
                    host_elapsed:.4f} sec")
            logger.debug(
                f"[3] EXPECTED Device Time (1+2): {expected_dev_time}")
            logger.debug(
                f"    (Initial Offset was:    {
                    ref_data['initial_offset']:.4f}s)")
            logger.debug(f"[4] ACTUAL Device Time (RTC):   {dev_time}")
            logger.debug(f"[5] DRIFT (4-3):                {drift:.4f} sec")
            logger.debug(f"-------------------------------")

            return abs(drift)

    raise TimeoutError("Device failed to return valid RTC time")
