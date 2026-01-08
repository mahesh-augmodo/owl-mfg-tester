import re


def safe_decode(byte_data: bytes) -> str:
    # Adopted from OWL-1-Test snippet
    # Critical to avoid issues in non utf-8 environments.
    # Users in China may use GBK
    if isinstance(byte_data, str):
        return byte_data

    encodings = ['utf-8', 'gbk', 'latin-1', 'ascii']
    for encoding in encodings:
        try:
            return byte_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return byte_data.decode('utf-8', errors='ignore')


def convert_unit_suffix(value_str):
    units = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    match = re.match(r"([0-9.]+)([A-Za-z]*)", value_str)
    if match:
        val, suffix = match.groups()
        multiplier = units.get(
            suffix.upper().rstrip('B'),
            1)  # Handle "M" or "MB"
        return float(val) * multiplier
    return 0.0
