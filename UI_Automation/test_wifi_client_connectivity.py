# If not stated otherwise in this file or this component LICENSE file the
# following copyright and licenses apply:
#
# Copyright 2026 RDK Management
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import conftest
import utils
import playwright_utils
import time
from utils import print_step, print_error, print_success

def test_fronthaul_wifi_client_connectivity(config, request, ssh):
    print_step("Entering Test1: test_fronthaul_wifi_client_connectivity")
    device_list = ["controller"] + list(config.get("extenders", {}).keys())
    for device in device_list:
        print_step(f"\n\nWireless client connectivity verification on {device}")
        # Fetch the current SSID and password from the device database
        print_step(f"\nStep 1: Fetch SSID and password for fronthaul network from Database")
        fronthaul_ssid, fronthaul_password = utils.get_fronthaul_credentials(config, ssh)
        if fronthaul_ssid and fronthaul_password:
            print_success("Fronthaul SSID and password fetched successfully.")
        else:
            print_error(request, "Fronthaul SSID and/or password not found in database.")

        # Get all AP BSSID values (2.4GHz, 5GHz, 6GHz) for fronthaul network verification
        print_step(f"Step 2: Fetch BSSID values for fronthaul from {device}")
        bssids = utils.get_fronthaul_bssids(device, ssh)
        if bssids:
            print_success(f"BSSIDs fetched successfully: {bssids}")
        else:
            print_error(request, f"No BSSIDs retrieved from {device}")

        # Execute WiFi scan on the client and filter results for the target SSID
        print_step(f"Step 3: Perform WiFi Scan from client(s) to discover available BSSIDs for SSID : {fronthaul_ssid}")
        # Before performing a Wi-Fi scan, it's best to disconnect the Wi-Fi interface if it is currently connected to any network to avoid scan issues.
        scan_cmd = f"nmcli -t -f BSSID,SSID device wifi list | grep {fronthaul_ssid}"

        for client_name, wifi_client in config.get("wifi_clients", {}).items():
            print_step(f"\nPerforming Wi-Fi scan from {client_name}")
            client_ip = wifi_client["ip"]
            client_user = wifi_client["user"]
            client_pass = wifi_client["pass"]
            client_scan = utils.get_wifi_scan_result(client_ip, client_user, client_pass, fronthaul_ssid, ssh, scan_cmd)
            if client_scan:
                print_success("WiFi scan completed successfully.")
            else:
                print_error(request, "WiFi scan returned no results.")
            # Process scan results to extract valid BSSIDs
            client_scan_lines = []
            for line in client_scan.splitlines():
                line = line.replace("\\:", ":")
                if fronthaul_ssid in line and re.match(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", line):
                    client_scan_lines.append(line)
            # Fail the test if no valid BSSIDs were found after parsing
            if client_scan_lines:
                print_success(f"Valid BSSIDs found in scan: {client_scan_lines}")
            else:
                print_error(request, f"No {fronthaul_ssid} networks found on client")
            # Parse visible BSSIDs
            visible_bssids = []
            for line in client_scan_lines:
                bssid = line.split(":")[0] + ":" + ":".join(line.split(":")[1:6])
                visible_bssids.append(bssid.lower())
            print(f"Visible BSSIDs on {client_name}: {visible_bssids}")
            # Select the first AP BSSID that is currently visible to the client
            print_step(f"Step 4: Select the AP BSSID that is currently visible")
            target_bssid = next((mac for mac in bssids if mac in visible_bssids), None)
            if target_bssid:
                print_success(f"Selected target BSSID: {target_bssid}")
            else:
                print_error(request, f"No fronthaul AP BSSIDs are visible on client for SSID {fronthaul_ssid}")
                continue
            target_bssid = target_bssid.upper()
            print(f"Selected BSSID for {client_name} connection: {target_bssid}")
            # Connect the client to the selected fronthaul BSSID
            print_step(f"Step 5: Connect the client to BSSID :{target_bssid} via nmcli")
            # Fetch wireless interface of client
            client_wifi_intf = utils.get_client_wifi_intf(client_ip, client_user, client_pass, ssh)
            connect_cmd = (f"sudo -S nmcli device wifi connect '{fronthaul_ssid}' password '{fronthaul_password}' bssid {target_bssid} ifname {client_wifi_intf}")
            # Execute the command on the client device via SSH
            client_connect_out = ssh.run_client(client_ip, client_user, client_pass, connect_cmd, sudo_password = client_pass)
            # Fail the test if the connection was not successful
            if "successfully activated" in client_connect_out.lower():
                print_success(f"Client connected to fronthaul network successfully via the {target_bssid}")
            else:
                print_error(request, f"Client failed to connect to fronthaul network via BSSID {target_bssid}")
            print_step(f"Step 6: Validate {client_name}'s IP address assignment and internet connectivity on the wireless interface")
            # Verify Client IP assignment and internet connectivity
            try:
                 utils.verify_client_ip_and_internet(client_ip, client_user, client_pass, ssh, 7)
            except Exception as e:
                print_error(request, f"Client IP/internet verification failed: {str(e)}")
    print_step("Exiting Test11: test_fronthaul_wifi_client_connectivity")

def test_fronthaul_wifi_client_connectivity_with_updated_ssid(config, page, request, ssh, paths):
    print_step("Entering Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
    print_step("Step 1: Update the fronthaul SSID from RDKB-CLI and verify the update on controller and agent devices")
    new_ssid = "TDKB_New_SSID_03"
    playwright_utils.verify_ssid_update_in_controller_and_agent(config, page, request, ssh, new_ssid, 2, paths)
    # Wait 60 sec for the updated ssid to broadcast
    time.sleep(60)
    # Verify client connectivity after successful SSID update on controller and agent
    print_step("Step 9: Trigger test_fronthaul_wifi_client_connectivity to verify client connectivity after SSID update")
    test_fronthaul_wifi_client_connectivity(config, request, ssh)
    print_step("Exiting Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
