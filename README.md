# OWL Tester

This is a manufacturing tester for OWL devices built around on OpenHTF. It uses ADB/SSH to install a test agent onto the DUT to facilitate faster testing.

## Setup

To set up the development environment, follow these steps:

1.  **Python Version:** Ensure you have >=Python 3.14 installed on your system.
2.  **Install Pipenv:** If you do not have Pipenv, install it globally:
    ```bash
    pip install pipenv
    ```
3.  **Install Dependencies:** Navigate to the root of this repository and install the project dependencies:
    ```bash
    pipenv install
    ```
4.  **Configuration:** Review and update the `config/station.yaml` file with the specific configuration for your DUT and ADB setup. This includes parameters like `dut_port`, `adb_host`, and `adb_host_port`.

## Usage

To execute the tests:

1.  **Activate Virtual Environment:** Activate the Pipenv-managed virtual environment:
    ```bash
    pipenv shell
    ```
2.  **Run Tests:** Execute the main test script:
    ```bash
    python src/main.py
    ```

The `setup_phase` defined in `src/main.py` will initiate the provisioning logic for the DUT via ADB, and the test will proceed according to the OpenHTF framework.
