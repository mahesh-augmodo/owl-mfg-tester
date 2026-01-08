import re


def parse_dumpcam_hwi(output_text: str):
    """
    Parses the full 'dumpcam hwi' output to extract:
    - FPS (from 'sensor dev attr 2')
    - Exposure Time (from 'exposure configured to drv')
    - Resolution (from 'sensor dev attr 1')
    """
    results = {
        "fps": None,
        "exposure_time": None,
        "resolution": None
    }

    dumpcam_lines = output_text.splitlines()
    results["fps"] = float(
        _get_first_col_value_from_table(
            dumpcam_lines, "fps"))
    results["exposure_time"] = float(
        _get_first_col_value_from_table(
            dumpcam_lines, "time_f"))
    width = _get_first_col_value_from_table(dumpcam_lines, "width")
    height = _get_first_col_value_from_table(dumpcam_lines, "height")
    results["resolution"] = f"{width}x{height}"

    return results


def parse_dumpcam_cnr_tnr(output_text: str) -> bool:
    """
    Parses the 'dumpcam tnr/cnr' output to extract:
    - Enable
    """
    dumpcam_lines = output_text.splitlines()
    return _get_first_col_value_from_table(dumpcam_lines, "en") == "Y"


def _get_first_col_value_from_table(table_lines, col_name):
    table_row, table_col = 0, 0
    for idx, line in enumerate(table_lines):
        if col_name in line:
            table_row = idx + 1  # The actual values.
            table_col = line.find(col_name)
    if table_row and table_row:
        result = table_lines[table_row][table_col:].split()[0]
        return result
