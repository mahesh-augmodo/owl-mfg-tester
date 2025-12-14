#!/bin/sh

# === CONFIGURATION ===
WIFI_INTERFACE="wlan0"

# Optional argument to filter band (2.4 or 5)
FILTER_BAND="$1"

# ==============================================================================
# FUNCTION: list_wifi_networks [BAND]
# Lists SSIDs, sorted by signal (dBm).
# Arg 1: Filter band ('2.4' or '5').
# ==============================================================================
list_wifi_networks() {
    band="$1"
    
    # Set title based on filter
    output_title="[All Bands]"
    [ "$band" = "2.4" ] && output_title="[2.4 GHz Only]"
    [ "$band" = "5" ] && output_title="[5 GHz Only]"

    # --- Ensure Fresh Data ---
    echo "--- Initiating Wi-Fi Scan on $WIFI_INTERFACE (wait 7 seconds...) ---"
    
    # Trigger scan
    wpa_cli -i "$WIFI_INTERFACE" scan > /dev/null 2>&1
    
    # Wait for scan to populate
    sleep 7
    # -------------------------

    echo "--- Available SSIDs (Sorted by Signal) $output_title ---"

    # Pipeline: scan_results -> remove header -> sort by signal -> filter/format
    wpa_cli -i "$WIFI_INTERFACE" scan_results | \
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

        # Format: [BAND]    SIGNAL dBm    SSID
        printf "[%s]    %s dBm    ", output_band, $3;
        
        # Print SSID (fields 5 onwards)
        for (i=5; i<=NF; i++) {
            printf "%s%s", $i, (i==NF ? "" : " ")
        }
        print ""
    }'
}

list_wifi_networks 