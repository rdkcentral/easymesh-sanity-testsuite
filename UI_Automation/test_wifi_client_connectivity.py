/**
 * If not stated otherwise in this file or this component LICENSE file the
 * following copyright and licenses apply:
 *
 * Copyright 2026 RDK Management
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import re
import pytest
import utils
import time
from utils import print_step, print_error, print_success

def test_fronthaul_wifi_client_connectivity(request, ssh):
    print_step("Entering Test1: test_fronthaul_wifi_client_connectivity")
    for device in ["controller", "agent"]:
        print_step(f"\n\nWireless client connectivity verification on {device}")
        # Fetch the current SSID and password from the device database
        print_step(f"\nStep 1: Fetch SSID and password for fronthaul network from Database")
        fronthaul_ssid, fronthaul_password = utils.get_fronthaul_credentials(request, ssh)
        # Get all AP BSSID values (2.4GHz, 5GHz, 6GHz) for fronthaul network verification
        print_step(f"Step 2: Fetch BSSID values for fronthaul from {device}")
        bssids = utils.get_fronthaul_bssids(device, ssh)
        # Execute WiFi scan on the client and filter results for the target SSID
        print_step(f"Step 3: Perform WiFi Scan from client to discover available BSSIDs for SSID : {fronthaul_ssid}")
        # Before performing a Wi-Fi scan, it's best to disconnect the Wi-Fi interface if it is currently connected to any network to avoid scan issues.
        scan_cmd = f"nmcli -t -f BSSID,SSID device wifi list | grep {fronthaul_ssid}"
        client_scan = utils.get_wifi_scan_result(fronthaul_ssid, ssh, request, scan_cmd)
        # Process scan results to extract valid BSSIDs
        client_scan_lines = []
        for line in client_scan.splitlines():
            line = line.replace("\\:", ":")
            if fronthaul_ssid in line and re.match(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", line):
                client_scan_lines.append(line)
        # Fail the test if no valid BSSIDs were found after parsing
        if not client_scan_lines:
            print_error(request, f"No {fronthaul_ssid} networks found on client")
        # Parse visible BSSIDs
        visible_bssids = []
        for line in client_scan_lines:
            bssid = line.split(":")[0] + ":" + ":".join(line.split(":")[1:6])
            visible_bssids.append(bssid.lower())
        print(f"Visible BSSIDs on client: {visible_bssids}")
        # Select the first AP BSSID that is currently visible to the client
        print_step(f"Step 4: Select the AP BSSID that is currently visible")
        target_bssid = next((mac for mac in bssids if mac in visible_bssids), None)
        if not target_bssid:
            print_error(request, f"No fronthaul AP BSSIDs are visible on client for SSID {fronthaul_ssid}")
        target_bssid = target_bssid.upper()
        print(f"Selected BSSID for client connection: {target_bssid}")
        # Connect the client to the selected fronthaul BSSID
        print_step(f"Step 5: Connect the client to BSSID :{target_bssid} via nmcli")
        # Fetch wireless interface of client
        client_wifi_intf = utils.get_client_wifi_intf(request, ssh)
        connect_cmd = (f"sudo -S nmcli device wifi connect '{fronthaul_ssid}' password '{fronthaul_password}' bssid {target_bssid} ifname {client_wifi_intf}")
        # Execute the command on the client device via SSH
        client_connect_out = ssh.run_client(request.session.client_ip, request.session.client_user, request.session.client_pass, connect_cmd, sudo_password = request.session.client_pass)
        # Fail the test if the connection was not successful
        if "successfully activated" not in client_connect_out.lower():
            print_error(request, f"Client failed to connect to fronthaul network via BSSID {target_bssid}")
        else:
            print_success(f"Client connected to fronthaul network successfully via the {target_bssid}")
        print_step("Step 6: Validate the client IP address assignment and internet connectivity on the wireless interface")
        # Verify Client IP assignment and internet connectivity
        utils.verify_client_ip_and_internet(request, ssh, 7)
    print_step("Exiting Test11: test_fronthaul_wifi_client_connectivity")

def test_fronthaul_wifi_client_connectivity_with_updated_ssid(page, request, ssh, paths):
    print_step("Entering Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
    print_step("Step 1: Update the fronthaul SSID from RDKB-CLI and verify the update on controller and agent devices")
    new_ssid = "TDKB_New_SSID_01"
    ctrl_out, agent_out = utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 2, paths)
    # Validate SSID consistency after update on controller and agent devices
    print_step("Step 9: Validate if updated SSID is consistent on both controller and agent devices and matches the expected value")
    ctrl_ssid = ctrl_out.strip()
    agent_ssid = agent_out.strip()
    # Check controller SSID
    if ctrl_ssid != new_ssid:
        print_error(request, f"SSID update validation failed on controller. Expected: {new_ssid}, Actual: {ctrl_ssid}")
    # Check agent SSID
    if agent_ssid != new_ssid:
        print_error(request, f"SSID update validation failed on agent. Expected: {new_ssid}, Actual: {agent_ssid}")
    print_success(f"Pass: SSID update verified successfully on both controller and agent with value '{new_ssid}'")
    # Wait 60 sec for the updated ssid to broadcast
    time.sleep(60)
    # Verify client connectivity after successful SSID update on controller and agent
    print_step("Step 10: Trigger test_fronthaul_wifi_client_connectivity to verify client connectivity after SSID update")
    test_fronthaul_wifi_client_connectivity(request, ssh)
    print_step("Exiting Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
