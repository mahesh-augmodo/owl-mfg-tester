# Helpers for running in a bundled application.
import sys
import os
import appdirs
import shutil

# Version for the bundled station.yaml. Increment to force overwrite on
# next run.
BUNDLE_CONFIG_VERSION = 1


def get_resource_path(relative_path):
    """
    Get the path to the READ-ONLY file bundled inside the exe.
    """
    if getattr(sys, 'frozen', False):
        # In PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # In Development (normal python script)
        base_path = os.path.dirname(os.path.abspath(__file__))
        # Adjust if main.py is in src/ but config is in root
        # base_path = os.path.join(base_path, '..')

    return os.path.join(base_path, relative_path)


def get_config_path():
    """
    Ensures config exists in AppData and is up-to-date, then returns the path to it.
    A new station.yaml will be copied over if the bundled version is newer.
    """
    CONFIG_FILENAME = "station.yaml"
    VERSION_FILENAME = "config.version"

    # 1. Determine where the writable config SHOULD be
    # On Windows this usually resolves to:
    # C:\Users\<User>\AppData\Local\OwlMfgTester
    user_data_dir = appdirs.user_data_dir("OwlMfgTester")

    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    destination_path = os.path.join(user_data_dir, CONFIG_FILENAME)
    version_path = os.path.join(user_data_dir, VERSION_FILENAME)

    # 2. Check current config version
    current_version = 0
    if os.path.exists(version_path):
        try:
            with open(version_path, 'r') as f:
                current_version = int(f.read().strip())
        except (ValueError, IOError):
            # Handle corrupted or unreadable version file
            print("Warning: Could not read config version file. Assuming old version.")
            current_version = 0

    # 3. If bundled config is newer, or if config doesn't exist, copy it over.
    if BUNDLE_CONFIG_VERSION > current_version or not os.path.exists(
            destination_path):
        if not os.path.exists(destination_path):
            print(
                f"First run detected or config missing. Copying config to {destination_path}...")
        else:
            print(
                f"Newer bundled config (v{BUNDLE_CONFIG_VERSION}) found. Upgrading from v{current_version}...")

        source_path = get_resource_path(
            os.path.join('config', CONFIG_FILENAME))

        try:
            shutil.copy2(source_path, destination_path)
            # Update the version file
            with open(version_path, 'w') as f:
                f.write(str(BUNDLE_CONFIG_VERSION))
            print("Config upgrade complete.")
        except FileNotFoundError:
            print(f"CRITICAL: Could not find default config at {source_path}")
            # Handle error (maybe create a blank default or crash gracefully)

    return destination_path
