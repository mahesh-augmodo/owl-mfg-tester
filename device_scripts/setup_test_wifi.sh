#!/bin/sh

# === CONFIGURATION SOURCING ===
# Loads configuration variables (WIFI_INTERFACE, TEST_SSID, TEST_PASSWORD).
WIFI_INTERFACE="wlan0"
TEST_SSID="AugmodoTestWiFi5G"
TEST_PASSWORD="augmodo12@"

# ==============================================================================
# FUNCTION 1: list_wifi_networks [BAND]
# Lists SSIDs, sorted by signal (dBm).
# Arg 1: Filter band ('2.4' or '5').
# ==============================================================================
list_wifi_networks() {
    band=$1
    
    # Set title
    output_title="[All Bands]"
    [ "$band" = "2.4" ] && output_title="[2.4 GHz Only]"
    [ "$band" = "5" ] && output_title="[5 GHz Only]"

    # --- Ensure Fresh Data ---
    echo "--- Initiating Wi-Fi Scan (wait 2 seconds...) ---"
    wpa_cli scan > /dev/null 2>&1
    sleep 3
    # -------------------------

    echo "--- Available SSIDs (Sorted by Signal) $output_title ---"

    # Pipeline: scan_results -> remove header -> sort by signal -> filter/format
    wpa_cli scan_results | \
    tail -n +3 | \
    sort -k3,3nr | \
    
    awk -v target_band="$band" '
    {
        # Determine band based on frequency ($2)
        current_band = ($2 < 3000) ? "2.4" : "5";

        # Skip if filter is set and band does not match
        if (target_band != "" && target_band != current_band) {
            next
        }

        output_band = (current_band == "2.4") ? "2.4 GHz" : "5 GHz";

        # Format: [BAND]    SIGNAL dBm    SSID (4 spaces)
        printf "[%s]    %s dBm    ", output_band, $3;
        
        # Print SSID (fields 5 onwards)
        for (i=5; i<=NF; i++) {
            printf "%s%s", $i, (i==NF ? "" : " ")
        }
        print ""
    }'
}

# ==============================================================================
# FUNCTION 2: get_pid_by_name [PROCESS_PATTERN]
# Finds PID of a running application.
# ==============================================================================
get_pid_by_name() {
    [ -z "$1" ] && { echo "Error: Provide process name." >&2; return 1; }

    process_pattern="$1"
    
    # Use ps and awk to reliably find the PID ($1), excluding the awk command itself.
    ps | awk -v pat="$process_pattern" '$0 ~ pat && !/awk|grep/ {print $1}'
}

# ==============================================================================
# FUNCTION 3: check_if_connected
# Checks the wpa_state and prints connection status for the Wi-Fi interface.
# ==============================================================================
check_if_connected() {
    wpa_state=$(wpa_cli status | grep 'wpa_state' | cut -d= -f 2)
    
    if [ "$wpa_state" = "COMPLETED" ]; then
        echo >&2 "$WIFI_INTERFACE is connected (wpa_state=COMPLETED)."
        echo "CONNECTED"
    else
        echo >&2 "$WIFI_INTERFACE is not connected (wpa_state=$wpa_state)."
    fi
}

# ==============================================================================
# FUNCTION 4: get_ip_address
# Finds the device IP address.
# ==============================================================================
get_ip_address() {
    echo "Finding IP address"
    IP_ADDR=$(wpa_cli status | grep ip_address | cut -d"=" -f 2)
    echo "Device IP Address = $IP_ADDR"
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

echo "--- Starting Wi-Fi Automation Test ---"

# --- 1. Process Management: Kill cvr_app ---

PROCESS_NAME='cvr_app'
pid=$(get_pid_by_name "$PROCESS_NAME")

if [ -z "$pid" ]; then
    echo "$PROCESS_NAME is not running. Proceeding."
else
    echo "$PROCESS_NAME is running (PID: $pid). Attempting to stop."
    /oem/usr/bin/RkLunch-stop.sh
    [ $? -eq 0 ] && echo "Successfully stopped $PROCESS_NAME." || echo "Warning: Could not stop $PROCESS_NAME."
fi

# --- 2. Wi-Fi Configuration and Connection ---

echo ""
echo "--- Configuring Wi-Fi for Test Network: $TEST_SSID on $WIFI_INTERFACE ---"

/usr/bin/rkwifi.sh "$TEST_SSID" "$TEST_PASSWORD"

# Clean up stale wpa_supplicant socket
rm /var/run/wpa_supplicant/"$WIFI_INTERFACE" 2>/dev/null

# Start wpa_supplicant daemon
wpa_supplicant -B -i"$WIFI_INTERFACE" -c /tmp/wpa_supplicant.conf

sleep 5

# Get IP address via DHCP
echo "Attempting to get IP address on $WIFI_INTERFACE..."
udhcpc -i "$WIFI_INTERFACE" > /dev/null 2>&1

echo ""
echo "--- Verification and Reporting ---"

# Scan available networks
list_wifi_networks

echo ""

# Check the connection status
CONNECT_STATUS=$(check_if_connected)
if [ $CONNECT_STATUS = "CONNECTED" ]; then
    get_ip_address
fi

echo "--- Test Script Finished ---"