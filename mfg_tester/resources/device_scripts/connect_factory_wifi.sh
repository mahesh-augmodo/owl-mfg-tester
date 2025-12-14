#!/bin/sh

# === CONFIGURATION ===
WIFI_INTERFACE="wlan0"

# Argument parsing
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <SSID> <PASSWORD>"
    exit 1
fi

TEST_SSID="$1"
TEST_PASSWORD="$2"

# ==============================================================================
# FUNCTION: get_pid_by_name [PROCESS_PATTERN]
# Finds PID of a running application.
# ==============================================================================
get_pid_by_name() {
    pattern="$1"
    [ -z "$pattern" ] && { echo "Error: Provide process name." >&2; return 1; }
    
    # Use ps and awk to reliably find the PID ($1), excluding awk/grep itself.
    # Assuming standard ps output where PID is column 1
    ps | awk -v pat="$pattern" '$0 ~ pat && !/awk|grep/ {print $1}'
}

# ==============================================================================
# FUNCTION: check_if_connected
# Checks the wpa_state.
# ==============================================================================
check_if_connected() {
    wpa_state=$(wpa_cli -i "$WIFI_INTERFACE" status | grep 'wpa_state' | cut -d= -f 2)
    
    if [ "$wpa_state" = "COMPLETED" ]; then
        echo >&2 "$WIFI_INTERFACE is connected (wpa_state=COMPLETED)."
        echo "CONNECTED"
    else
        echo >&2 "$WIFI_INTERFACE is not connected (wpa_state=$wpa_state)."
        echo "DISCONNECTED"
    fi
}

# ==============================================================================
# FUNCTION: get_ip_address
# Finds the device IP address.
# ==============================================================================
get_ip_address() {
    IP_ADDR=$(wpa_cli -i "$WIFI_INTERFACE" status | grep ip_address | cut -d"=" -f 2)
    echo "Device IP Address = $IP_ADDR"
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

echo "--- Starting Wi-Fi Connection Setup ---"

# --- 1. Process Management: Kill cvr_app ---
PROCESS_NAME='cvr_app'
pid=$(get_pid_by_name "$PROCESS_NAME")

if [ -z "$pid" ]; then
    echo "$PROCESS_NAME is not running. Proceeding."
else
    echo "$PROCESS_NAME is running (PID: $pid). Attempting to stop."
    # Attempt graceful stop using OEM script
    if [ -f /oem/usr/bin/RkLunch-stop.sh ]; then
        /oem/usr/bin/RkLunch-stop.sh
    else
        kill "$pid"
    fi
    sleep 1
fi

# --- 2. Wi-Fi Configuration ---
echo ""
echo "--- Configuring Wi-Fi for Network: $TEST_SSID on $WIFI_INTERFACE ---"

# Generate config using external tool
/usr/bin/rkwifi.sh "$TEST_SSID" "$TEST_PASSWORD"

# Clean up stale wpa_supplicant socket
rm /var/run/wpa_supplicant/"$WIFI_INTERFACE" 2>/dev/null

# Start wpa_supplicant daemon
echo "Starting wpa_supplicant..."
wpa_supplicant -B -i"$WIFI_INTERFACE" -c /tmp/wpa_supplicant.conf

sleep 5

# --- 3. DHCP Lease ---
echo "Attempting to get IP address on $WIFI_INTERFACE..."

UDHCPC_TIMEOUT=10 
UDHCPC_RETRIES=3  
DHCP_SUCCESS=0

for i in $(seq 1 $UDHCPC_RETRIES); do
    echo "DHCP attempt $i of $UDHCPC_RETRIES..."
    udhcpc -i "$WIFI_INTERFACE" -T "$UDHCPC_TIMEOUT" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "udhcpc successful."
        DHCP_SUCCESS=1
        break
    else
        echo "udhcpc failed. Retrying in 2 seconds..."
        sleep 2
    fi
done

if [ "$DHCP_SUCCESS" -eq 0 ]; then
    echo "Failed to obtain IP address after $UDHCPC_RETRIES attempts."
    exit 1
fi

# --- 4. Verification ---
echo ""
echo "--- Verification ---"

CONNECT_STATUS=$(check_if_connected)

if [ "$CONNECT_STATUS" = "CONNECTED" ]; then
    get_ip_address
    echo "--- Setup Successful ---"
else
    echo "--- Setup Failed: Interface not connected ---"
    exit 1
fi