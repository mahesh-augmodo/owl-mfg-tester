# Adopted from OWL-1-Test snippet
# Critical to avoid issues in non utf-8 environments.
# Users in China may use GBK

def safe_decode(byte_data: bytes) -> str:
    if isinstance(byte_data, str):
        return byte_data

    encodings = ['utf-8', 'gbk', 'latin-1', 'ascii']
    for encoding in encodings:
        try:
            return byte_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return byte_data.decode('utf-8', errors='ignore')
