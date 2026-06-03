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
import time
from playwright.sync_api import expect, sync_playwright, TimeoutError as PlaywrightTimeoutError
import pytest
import json
import conftest

def print_step(message):
    print(f"\033[1m\033[97m{message}\033[0m") # Bold white text
    return f'<span style="color:black; font-weight:bold;">{message}</span>'

def print_error(request, message):
    print(f"\033[91mFAIL: {message}\033[0m")
    # Store error in test node
    if not hasattr(request.node, "error_logs"):
        request.node.error_logs = []
    request.node.error_logs.append(message)
    return f'<span style="color:red; font-weight:bold;">FAIL: {message}</span>'

def print_success(message):
    print(f"\033[92mPASS: {message}\033[0m")  # Green text
    return f'<span style="color:green; font-weight:bold;">PASS: {message}</span>'

def run_command_fetch_output_from_device(command, device, ssh):
    try:
        out = ssh.run(device, command)
        return out
    except Exception as e:
        pytest.fail(f"Failed to run the command {command} and fetch output from the {device} device. Error: {e}")

def verify_service_status(request, device, service_name, ssh, step):    
    print_step(f"Step {step}: Verify {service_name} service status from {device}")
    out = run_command_fetch_output_from_device(f"systemctl is-active {service_name}", device, ssh)
    if "active" not in out:
        print_error(request, f"{service_name} service is NOT running on {device}:\n{out}")
    else:
        print_success(f"{service_name} service is running as expected on {device} device")

def verify_core_dump_generated(request, ssh):
    for step, device in enumerate(ssh.device_list, start=1):
        print_step(f"Step {step}: Verify core files presence in /tmp directory from {device}")
        out = run_command_fetch_output_from_device("ls /tmp/*dmp* 2>/dev/null", device, ssh)        
        if out.strip():
            print_error(request, f"Fail: Dump files found in /tmp on {device}:\n{out}")
        else:
            print_success(f"No dump files found in /tmp directory on {device} device.")

def get_client_wifi_intf(client_ip, client_user, client_pass, ssh):
    # Fetch WiFi interface details of client device
    result = ssh.run_client(client_ip, client_user, client_pass, "nmcli -t -f DEVICE,TYPE dev status | grep wifi | cut -d: -f1")
    wifi_iface = result.strip()
    if not wifi_iface:
       pytest.fail("WiFi interface not found on the device")
    return wifi_iface

def get_interface_mac_address(device, interface_name, ssh):
    # Run ifconfig remotely via SSH
    output = run_command_fetch_output_from_device(f"ifconfig {interface_name}", device, ssh)
    # Parse MAC address
    mac_match = re.search(r"(?:HWaddr|ether)\s+([0-9a-fA-F:]{17})", output, re.IGNORECASE)
    if not mac_match:
        pytest.fail(f"MAC address not found for {interface_name}")
    mac_address = mac_match.group(1)
    print(f"MAC address of {interface_name} on {device}: {mac_address}")
    return mac_address.lower()

def get_db_values(config, ssh, query):
    #Run MySQL query on device via SSH and return output
    cmd = f"mysql -N --batch -u {config['database']['user']} -p{config['database']['pass']} -D {config['database']['name']} -e \"{query}\""
    ctrl_out = run_command_fetch_output_from_device(cmd, "controller", ssh)
    return ctrl_out

def _get_non_empty_mysql_rows(query_out):
    # Preserve in-row separators while dropping blank lines.
    return [line.rstrip("\r") for line in query_out.splitlines() if line.strip()]

def _parse_ssid_passphrase_row(row):
    # MySQL --batch is tab-delimited; keep a whitespace fallback for safety.
    if "\t" in row:
        ssid, password = row.split("\t", 1)
        return ssid.strip(), password.strip()

    parts = row.split(None, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    pytest.fail(
        "Invalid DB row format for SSID/PassPhrase. "
        f"Expected two columns but got: '{row}'"
    )

def wifi_reset_dialog_handler(dialog):
    #Handle the popup by capturing its message and confirming OK based on the message.
    msg = dialog.message.lower()
    if "resetting the wi-fi configuration" in msg:
        print(f"Dialog Message:\n{msg}")
        dialog.accept()
        time.sleep(5)
    elif "wi-fi configuration reset successfully" in msg:
        print_success(f"Dialog Message:\n{msg}")
        dialog.accept()
    else:
        print(f"Dialog Message: {msg}")
        pytest.fail("Error in handling the Wi-Fi reset confirmation dialog.")

def get_reset_json_data(config, ssh):
    #Read Reset.json from the controller and return parsed data.
    reset_json_file = config["system"]["reset_json_file"]
    cmd = f"cat {reset_json_file}"
    out = run_command_fetch_output_from_device(cmd, "controller", ssh)
    try:
        data = json.loads(out)
    except Exception as e:
        pytest.fail(f"Failed to parse Reset.json: {e}")
    return data.get("wfa-dataelements:Reset")

def get_network_ssid_list_db(config, ssh):
    #Fetch NetworkSSIDList table from DB dynamically with proper column names.
    network_ssid_list_db_table = config["database"]["ssid_table"]
    #Step 1: Get column names of NetworkSSIDList table
    col_output = get_db_values(config, ssh, f"SHOW COLUMNS FROM {network_ssid_list_db_table};")
    if not col_output.strip():
        pytest.fail(f"No columns returned from {network_ssid_list_db_table}")
    columns = [line.split("\t")[0] for line in col_output.strip().splitlines()]

    #Step 2: Get NetworkSSIDList table rows
    row_output = get_db_values(config, ssh, f"SELECT * FROM {network_ssid_list_db_table};")
    if not row_output.strip():
        pytest.fail(f"No data returned from table {network_ssid_list_db_table}")
    data_rows = [line.split("\t") for line in row_output.strip().splitlines()]

    # Step 3: Map values to columns
    rows = []
    for values in data_rows:
        if len(values) != len(columns):
            pytest.fail(f"Row column count mismatch: {values}")
        rows.append(dict(zip(columns, [v.strip() for v in values])))
    return rows

def normalize_bool(val):
    #Normalize DB boolean-like values (1, 0, true, false, yes, no) to Python bool.
    return str(val).lower() in ["1", "true", "yes"]

def get_fronthaul_credentials(config, request, ssh, step):
    # Fetch the current fronthaul SSID and password from OneWifiMesh DB
    print_step(f"\nStep {step}: Fetch SSID and password for fronthaul network from Database")
    try:
        query = (
            f"SELECT SSID, PassPhrase FROM {config['database']['ssid_table']} "
            "WHERE ID='Fronthaul@OneWifiMesh' LIMIT 1;"
        )
        query_out = get_db_values(config, ssh, query)
        # Check if query returned anything
        if not query_out.strip():
            print_error(request, "No fronthaul SSID entry found in DB matching pattern")
            return None, None
        rows = _get_non_empty_mysql_rows(query_out)
        if len(rows) != 1:
            print_error(request, f"Expected exactly 1 fronthaul SSID row, found {len(rows)} rows")
            return None, None
        # Extract SSID and password from query output
        ssid, password = _parse_ssid_passphrase_row(rows[0])
        if not ssid or not password:
            print_error(request, "Fetched fronthaul SSID or password is empty")
            return None, None
        print(f"Fetched fronthaul credentials: SSID={ssid}, Password={password}")
        print_success("Fronthaul SSID and password fetched successfully.")
        return ssid, password
    except Exception as e:
        print_error(request, f"Failed to fetch fronthaul credentials from DB: {e}")
        return None, None

def get_fronthaul_bssids(device, request, ssh, step):
    # Get all AP BSSID values (2.4GHz, 5GHz, 6GHz) for fronthaul network verification
    print_step(f"Step {step}: Fetch BSSID values for fronthaul from {device}")
    # Fetch all BSSID values for the fronthaul network, includes 2.4GHz, 5GHz, and 6GHz radios.
    try:
        iw_output = run_command_fetch_output_from_device("iw dev mld0 info", device, ssh)
    except Exception as e:
        print_error(request, f"Failed to fetch BSSIDs from {device}: {e}")
        return None
    bssids = re.findall(r"link addr ([0-9a-fA-F:]{17})", iw_output)
    if bssids:
        print(f"Fetched BSSIDs from {device}: {bssids}")
        print_success(f"BSSIDs fetched successfully: {bssids}")
        return [bssid.lower() for bssid in bssids]
    else:
        print_error(request, f"No fronthaul BSSIDs found on {device}")
        return None

def verify_client_ip_and_internet(client_ip, client_user, client_pass, ssh, step):
    #Verify client interface has obtained an IP address and can reach the internet by pinging an external host.
    client_wifi_intf = get_client_wifi_intf(client_ip, client_user, client_pass, ssh)
    try:
        # Step 1: Get the IP address assigned to the client interface
        print_step(f"Step {step}: Fetch IP address obtained on client interface '{client_wifi_intf}'")
        client_ip_out = ssh.run_client(client_ip, client_user, client_pass, f"nmcli -t -f IP4.ADDRESS device show {client_wifi_intf} | awk -F'[:/]' '{{print $2}}'")
        client_ip = client_ip_out.strip()
        # Fail if no IP was obtained
        if not client_ip:
            pytest.fail(f"Client interface '{client_wifi_intf}' did not obtain an IP address from fronthaul network")
        print_success(f"Client obtained IP address on {client_wifi_intf}: {client_ip}")
        print_step(f"Step {step+1}: Verify internet connectivity from client interface '{client_wifi_intf}' by pinging www.google.com")
        # Step 2: Test internet connectivity using ping via the assigned IP/interface
        client_ping_out = ssh.run_client(client_ip, client_user, client_pass, f"ping -I {client_wifi_intf} -c 5 www.google.com")
        # Fail if ping reports any packet loss
        if "0% packet loss" not in client_ping_out:
            pytest.fail(f"Client interface '{client_wifi_intf}' does NOT have internet connectivity via fronthaul network")
        print_success(f"Client has internet connectivity via {client_wifi_intf}")
    except Exception as e:
        # Catch any unexpected exception and fail the test with details
        pytest.fail(f"Failed to verify IP or internet connectivity on interface '{client_wifi_intf}': {e}")

def fetch_tr181_topology_verification_params(ssh):
    # Fetch the required TR-181 parameters required for topology validation
    # Get number of devices (Agent and extender)
    cmd_device_count = "dmcli eRT getv Device.WiFi.DataElements.Network.DeviceNumberOfEntries | grep 'value:'"
    output = run_command_fetch_output_from_device(cmd_device_count, "controller", ssh)
    print(f"Output for device count command: {output}")
    if not output:
        pytest.fail(f"SSH command returned empty output: {cmd_device_count}")
    match = re.search(r"value:\s*(\d+)", output)
    if not match:
        pytest.fail(f"Failed to parse device count from output: {output}")
    device_count = int(match.group(1))
    device_ssid_map = {}
    for i in range(1, device_count + 1):
        # Get unique ID (Mac address) for each device
        cmd_device_id = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.ID | grep 'value:'"
        output = run_command_fetch_output_from_device(cmd_device_id, "controller", ssh)
        print(f"Output for device {i} ID command: {output}")
        if not output:
            pytest.fail(f"Error fetching device ID for device index {i}: got empty output")
        match = re.search(r"value:\s*(.+)", output)
        if not match:
            pytest.fail(f"Failed to parse device ID for device index {i}: output={output}")
        device_id = match.group(1).strip()
        device_ssid_map[device_id] = {}
        # Get number of Radios for each device
        cmd_radio_count = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.RadioNumberOfEntries | grep 'value:'"
        output = run_command_fetch_output_from_device(cmd_radio_count, "controller", ssh)
        print(f"Output for device {i} radio count command: {output}")
        if not output:
            pytest.fail(f"Error fetching radio number of entries for device index {i}: got empty output")
        match = re.search(r"value:\s*(\d+)", output)
        if not match:
            pytest.fail(f"Failed to parse radio count for device index {i}: output={output}")
        radio_count = int(match.group(1))
        for r in range(1, radio_count + 1):
            # Get number of BSS entries for each Radio
            cmd_bss_count = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSSNumberOfEntries | grep 'value:'"
            output = run_command_fetch_output_from_device(cmd_bss_count, "controller", ssh)
            print(f"Output for device {i} radio {r} BSS count command: {output}")
            if not output:
                pytest.fail(f"Error fetching BSS number of entries for device index {i}, radio index {r}: got empty output")
            match = re.search(r"value:\s*(\d+)", output)
            if not match:
                pytest.fail(f"Failed to parse BSS count for device index {i}, radio index {r}: output={output}")
            bss_count = int(match.group(1))
            for b in range(1, bss_count + 1):
                # Get SSID value for each BSS
                cmd_ssid = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSS.{b}.SSID | grep 'value:'"
                ssid_output = run_command_fetch_output_from_device(cmd_ssid, "controller", ssh)
                print(f"Output for device {i} radio {r} BSS {b} SSID command: {ssid_output}")
                if not ssid_output:
                    pytest.fail(f"Error fetching SSID for device index {i}, radio index {r}, BSS index {b}: got empty output")
                match = re.search(r"value:\s*(.+)", ssid_output)
                if not match:
                    pytest.fail(f"Failed to parse SSID for device index {i}, radio index {r}, BSS index {b}: output={ssid_output}")
                ssid = match.group(1).strip()
                # Get BSSID value for each BSS
                cmd_bssid = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSS.{b}.BSSID | grep 'value:'"
                bssid_output = run_command_fetch_output_from_device(cmd_bssid, "controller", ssh)
                print(f"Output for device {i} radio {r} BSS {b} BSSID command: {bssid_output}")
                if not bssid_output:
                    pytest.fail(f"Error fetching BSSID for device index {i}, radio index {r}, BSS index {b}: got empty output")
                match = re.search(r"value:\s*([0-9a-f:]{17})", bssid_output, re.I)
                if not match:
                    pytest.fail(f"Failed to parse BSSID for device index {i}, radio index {r}, BSS index {b}: output={bssid_output}")
                bssid = match.group(1).lower()
                if ssid not in device_ssid_map[device_id]:
                    device_ssid_map[device_id][ssid] = {'bssids': [], 'mld_mac': None}
                device_ssid_map[device_id][ssid]['bssids'].append(bssid)
        # Only fetch first MLD entry, if private SSID exists (This is because of limited info available)
        for ssid_name in device_ssid_map[device_id]:
            if ssid_name.lower().startswith("private"):
                cmd_mld_mac = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.APMLD.1.MLDMACAddress | grep 'value:'"
                output = run_command_fetch_output_from_device(cmd_mld_mac, "controller", ssh)
                print(f"Output for device {i} MLD MAC command: {output}")
                if output:
                    mld_mac_match = re.search(r"value:\s*([0-9a-f:]{17})", output, re.I)
                    if mld_mac_match:
                        device_ssid_map[device_id][ssid_name]['mld_mac'] = mld_mac_match.group(1).lower()
                    else:
                        pytest.fail(f"Failed to parse MLD MAC for device index {i}: output={output}")
                break
    return device_ssid_map, device_count

def get_sta_interfaces_from_bridge(ssh, device, bridge_intf):
    # Get the list of station interfaces from the bridge.
    br_output = run_command_fetch_output_from_device(f"brctl show {bridge_intf}", device, ssh)
    # Fail if the bridge command output is empty
    if not br_output.strip():
        pytest.fail(f"No output returned from 'brctl show {bridge_intf}' on {device}")
    sta_interfaces = []
    for line in br_output.splitlines()[1:]:  # Skip header line
        parts = line.split()
        if len(parts) > 0 and parts[-1].startswith("wifi") and ".sta" in parts[-1]:
            sta_interfaces.append(parts[-1])
    return sta_interfaces

def get_wifi_scan_result(client_ip, client_user, client_pass, ssid_name, ssh, scan_cmd):
	# Before performing a Wi-Fi scan, it's best to disconnect the Wi-Fi interface if it is currently connected to any network to avoid scan issues.
    # Disconnect Wi-Fi interface if currently connected
    client_wifi_intf = get_client_wifi_intf(client_ip, client_user, client_pass, ssh)
    check_cmd = f'nmcli -t -f DEVICE,STATE device status | grep -E "^{client_wifi_intf}:(connected|connecting)"'
    check_output = ssh.run_client(client_ip, client_user, client_pass, check_cmd)
    if check_output.strip():
        # Disconnect if connected
        disconnect_cmd = f'sudo -S nmcli device disconnect {client_wifi_intf}'
        disconnect_output = ssh.run_client(client_ip, client_user, client_pass, disconnect_cmd, sudo_password=client_pass)
        if "successfully disconnected" not in disconnect_output.lower():
            pytest.fail(f"Wi-Fi interface {client_wifi_intf} issue in client device. Failed to disconnect before scan: {disconnect_output}")
    # Run Wi-Fi scan with 3 attempts
    for attempt in range(1, 4):
        scan_output = ssh.run_client(client_ip, client_user, client_pass, scan_cmd, sudo_password=client_pass).strip()
        if scan_output:
            # If a specific SSID is found, return the scan result, otherwise retry. 
            if ssid_name:
                if ssid_name in scan_output:
                    break
        # Wait 5 seconds before next attempt
        time.sleep(5)
    # Fail the test if scan returned nothing
    if not scan_output or not scan_output.strip():
        pytest.fail(f"No Wi-Fi networks found on client device for interface {client_wifi_intf}")
    return scan_output

def extract_mac_from_dump(dump_output):
    match = re.search(r"([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5})", dump_output)
    return match.group(1).lower() if match else None

def get_station_mac(device, sta_iface, ssh):
    # Fetch the station MAC address from the station dump output
    dump = run_command_fetch_output_from_device(f"iw dev {sta_iface} station dump", device, ssh)
    if not dump.strip():
        pytest.fail(f"No station dump output found on {device} for interface {sta_iface}")
    mac = extract_mac_from_dump(dump)
    if not mac:
        pytest.fail(f"Failed to extract MAC address from station dump on {device} for interface {sta_iface}")
    return mac.lower()

def build_extender_mac_map(request, ssh):
    # Build the extender mesh backhaul MAC address mapping
    mesh_bh_inf = "wifi1.3"
    extender_mac_map = {}
    mac_map_ok = True
    for extender in ssh.extenders:
        mac = get_interface_mac_address(extender, mesh_bh_inf, ssh)
        if not mac:
            print_error(request, f"Mesh backhaul MAC address not found on {extender} interface {mesh_bh_inf}")
            mac_map_ok = False
        else:
            extender_mac_map[mac] = extender
    return extender_mac_map, mac_map_ok

def get_child_mac(current_extender, config, request, ssh):
    # Fetch the child extender MAC connected to the current extender
    sta_list = get_sta_interfaces_from_bridge(ssh, current_extender, config["system"]["bridge_intf"])
    print(f"{current_extender}: detected {len(sta_list)} STA interface(s) on bridge {config['system']['bridge_intf']} -> {sta_list}")
    child_mac = None
    child_count = 0
    topology_valid = True
    for sta in sta_list:
        mac = get_station_mac(current_extender, sta, ssh)
        # Skip invalid or missing MAC values
        if not mac:
            continue
        child_count += 1
        child_mac = mac
    # Validation: linear topology must have a maximum of one child
    if child_count > 1:
        print_error(request, f"{current_extender}: detected {child_count} child extenders; expected maximum 1 for linear daisy-chain topology")
        topology_valid = False
    elif child_count == 1:
        print(f"{current_extender}: child extender detected with MAC {child_mac}")
    else:
        print(f"{current_extender}: no child extender detected (end of chain)")
    return child_mac, topology_valid

def validate_daisy_topology(parent_mac, extender_mac_map, config, request, ssh):
    # Validate the linear daisy-chain topology
    visited_extenders = []
    topology_ok = True
    traversal_complete = False
    expected_count = len(extender_mac_map)
    while not traversal_complete:
        current_extender = extender_mac_map.get(parent_mac)
        if not current_extender:
            print_error(request, f"Extender mapping not found for MAC address {parent_mac}")
            topology_ok = False
            break
        # Prevent revisiting a node
        if current_extender in visited_extenders:
            print_error(request, f"Topology loop detected: extender {current_extender} - {parent_mac} was already visited")
            topology_ok = False
            break
        # Mark extender as visited
        visited_extenders.append(current_extender)
        print(f"Topology traversal: visiting extender {current_extender}")
        child_mac, topology_valid = get_child_mac(current_extender, config, request, ssh)
        if not topology_valid:
            topology_ok = False
            break
        # End of chain
        if not child_mac:
            traversal_complete = True
        else:
            parent_mac = child_mac
    if len(visited_extenders) < 2:
        topology_ok = False
        print_error(request, f"Invalid topology. At least two extenders are required for topology validation, but only {len(visited_extenders)} extender was observed.")
    elif len(visited_extenders) == expected_count:
        print_success(f"Topology traversal completed successfully: visited {len(visited_extenders)} extender(s)")
    else:
        topology_ok = False
        print_error(request, f"Topology traversal incomplete: visited {len(visited_extenders)} extender(s), expected {expected_count}")
    # Final topology validation
    print_step("Step 3.4: Validate final mesh topology result.")
    if topology_ok:
        print_success("Daisy-chain mesh topology detected.")
    else:
        print_error(request,"Invalid mesh topology detected.")

def validate_all_configured_vaps_are_up(config, ssh):
    print("\n[Mesh Setup Verification 1/5] Verifying if all the configured VAPs are up...")    
    errors = []
    ssid_map = config["database"]["network_ssid_map"]
    expected_ssids = [ssid_map[name]["default_ssid"] for name in ["Fronthaul", "IoT", "Backhaul"]]
    for device in ssh.device_list:
        try:
            out = run_command_fetch_output_from_device("iw dev | grep ssid", device, ssh)
        except Exception as e:
            errors.append(f"Unable to fetch configured VAPs on {device}: {e}")
            continue
        missing = [
            ssid for ssid in expected_ssids
            if ssid not in out
        ]
        if missing:
            print(f"Fail: Missing VAPs on {device} device. Command Output: \n{out}\n")
            errors.append(f"Missing VAPs on {device}: {missing}. Command Output: \n{out}")
        else:
            print(f"Pass: All configured VAPs are up on the {device} device. Command Output: \n{out}\n")
    return errors

def verify_mld0_interface_presence(ssh):
    """
    Verify that mld0 interface is present on all devices (controller and extenders).
    """
    print("\n[Mesh Setup Verification 2/5] Verifying mld0 interface presence on all devices...")
    errors = []
    command = "iw dev mld0 info && (iw dev mld0 info | wc -l)"
    for step, device in enumerate(ssh.device_list, start=1):
        try:
            out = run_command_fetch_output_from_device(command, device, ssh)
        except Exception as e:
            errors.append(f"Unable to verify mld0 interface on {device}: {e}")
            continue
        print(f"Step {step}: Verify mld0 interface on {device}")
        lines = out.strip().splitlines()
        try:
            line_count = int(lines[-1])  # last line is wc -l output
        except (IndexError, ValueError):
            errors.append(f"Unexpected output from {device}: {out}")
            continue
        clean_output = "\n".join(lines[:-1])  # remove wc -l output
        if line_count == 0:
            print(f"Fail: mld0 interface is NOT present on {device}. Output:\n{clean_output}")
            errors.append(f"mld0 interface is NOT present on {device}. Output:\n{clean_output}")
        else:
            print(f"Pass: mld0 interface is present on {device}. Output:\n{clean_output}")
    return errors

def verify_mld0_links_to_privatevaps(ssh):
    """
    Verify that mld0 has correct number of links and each link maps to the corresponding wifi interface.
    """
    print("\n[Mesh Setup Verification 3/5] Verifying mld0 links map to private VAPs...")    
    errors = []
    expected_links = 3
    # Verify number of mld0 links
    command_links = "iw dev mld0 info | grep 'link ID' | wc -l"
    for step, device in enumerate(ssh.device_list, start=1):
        try:
            out = run_command_fetch_output_from_device(command_links, device, ssh)
        except Exception as e:
            errors.append(f"Unable to check mld0 link count on {device}: {e}")
            continue
        links = out.strip()
        print(f"  Step {step}: Checking mld0 link count on {device}: {links}")        
        if links != str(expected_links):
            errors.append(f"{device} expected {expected_links} links but found {links}")
        else:
            print(f"Pass: {device} has expected {expected_links} links")

    # Verify MAC mapping for each link
    for count, link_id in enumerate(range(expected_links), start=4):
        print(f"  Step {count}: Verifying link ID {link_id} corresponds to wifi{link_id}")

        for device in ssh.device_list:
            # Get wifi MAC
            wifi_cmd = f"iw dev wifi{link_id} info | awk '/addr/ {{print $2}}'"
            try:
                wifi_mac = run_command_fetch_output_from_device(wifi_cmd, device, ssh).strip().replace("\r", "")
            except Exception as e:
                errors.append(f"Unable to fetch wifi{link_id} MAC on {device}: {e}")
                continue
            # Get mld0 MAC for this link (parse in Python)
            try:
                mld_out = run_command_fetch_output_from_device("iw dev mld0 info", device, ssh)
            except Exception as e:
                errors.append(f"Unable to fetch mld0 details on {device} for link {link_id}: {e}")
                continue
            mld_mac = None
            for line in mld_out.splitlines():
                line = line.strip()
                if line.startswith(f"- link ID  {link_id} link addr"):
                    mld_mac = line.split()[-1].strip()
                    break
            if not mld_mac:
                errors.append(f"{device} mld0 MAC for link {link_id} not found")
                continue
            print(f"  {device} wifi{link_id} MAC: {wifi_mac}")
            print(f"  {device} mld0 link {link_id} MAC: {mld_mac}")
            if wifi_mac != mld_mac:
                errors.append(
                    f"{device} mismatch for link {link_id}. "
                    f"wifi{link_id}: {wifi_mac}, mld0: {mld_mac}"
                )
                print(f"Fail: {device} mismatch for link {link_id}. wifi{link_id}: {wifi_mac}, mld0: {mld_mac}")
                continue

            print(f"Pass: {device} link {link_id} correctly maps to wifi{link_id}")
    return errors

def verify_mesh_backhaul_interfaces(config, ssh):
    """
    Verify that mesh backhaul interfaces have the correct SSID configured.
    """
    print("\n[Mesh Setup Verification 4/5] Verifying mesh backhaul interface SSIDs...")
    errors = []
    
    # Get expected backhaul SSID from config.yaml
    ssid_map = config["database"]["network_ssid_map"]
    expected_ssid = ssid_map["Backhaul"]["default_ssid"]
    
    def get_interface(device):
        return "wifi1.1" if device == "controller" else "wifi1.3"
    
    for count, device in enumerate(ssh.device_list, start=1):
        interface = get_interface(device)
        print(f"  Step {count}: Verifying mesh backhaul SSID on {device} interface {interface}")
        cmd = f"iw dev {interface} info | grep ssid | awk '{{print $2}}'"
        try:
            out = run_command_fetch_output_from_device(cmd, device, ssh).strip()
        except Exception as e:
            errors.append(f"Unable to verify mesh backhaul SSID on {device} interface {interface}: {e}")
            continue
        print(f"  {device.capitalize()} {interface} SSID: {out}")
        if out != expected_ssid:
            print(f"Fail: {device} interface {interface} has incorrect SSID. Expected: {expected_ssid}, Found: {out}")
            errors.append(
                f"Mesh backhaul SSID mismatch on {device} interface {interface}. "
                f"Expected: {expected_ssid}, Found: {out}"
            )
        else:
            print(f"Pass:{device} interface {interface} correctly has SSID '{expected_ssid}'")
    return errors

def verify_mesh_backhaul_extenders_connected(config, ssh):
    """
    Verify that extenders are connected via mesh backhaul STA interfaces on the controller.
    """
    print("\n[Mesh Setup Verification 5/5] Verifying extenders connected via mesh backhaul...")
    errors = []
    # Get STA interfaces from the bridge
    try:
        sta_interfaces = get_sta_interfaces_from_bridge(ssh, "controller", config["system"]["bridge_intf"])
    except Exception as e:
        errors.append(f"Failed to fetch STA interfaces from bridge {config['system']['bridge_intf']}: {e}")
        return errors
    if not sta_interfaces:
        errors.append(f"No STA interfaces found on bridge {config['system']['bridge_intf']} on controller")
        return errors
    print(f"Found STA interfaces on {config['system']['bridge_intf']}: {sta_interfaces}")
    # Check each STA interface
    for count, interface in enumerate(sta_interfaces, start=1):
        print(f"  Step {count}: Verifying mesh backhaul interface {interface}")
        # Get full interface info
        cmd_info = f"iw dev {interface} info"
        try:
            info_out = run_command_fetch_output_from_device(cmd_info, "controller", ssh).strip()
        except Exception as e:
            errors.append(f"Failed to fetch interface info for {interface}: {e}")
            continue
        print(f"  Output of 'iw dev {interface} info':\n{info_out}")
        # Check connected extenders
        cmd_dump = f"iw dev {interface} station dump"
        try:
            station_out = run_command_fetch_output_from_device(cmd_dump, "controller", ssh).strip()
        except Exception as e:
            errors.append(f"Failed to fetch station dump for {interface}: {e}")
            continue
        print(f"  Output of 'iw dev {interface} station dump':\n{station_out}")
        if not station_out:
            print(f"Fail: No extenders connected to mesh backhaul interface {interface}\n")
            errors.append(f"No extenders connected to mesh backhaul interface {interface}")
        else:
            print(f"Pass: Interface {interface} has extenders connected\n")
    return errors

def verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, step):
    # Retry ssid update check logic after wait time
    max_retries = 10
    retry_interval = 10000  # 10 sec
    print_step(f"Step {step}: Initial wait before device ssid verification")
    page.wait_for_timeout(20000)
    print_step(f"Step {step+1}: Verify SSID update on both controller and agent.")
    for attempt in range(max_retries):
        print(f"SSID verification attempt : {attempt + 1}")
        results = {}
        for device in ssh.device_list:
            out = run_command_fetch_output_from_device("iw dev mld0 info | awk '/ssid/ {print $2}'", device, ssh)
            value = out.strip() if out else ""
            if value != "":
                print(f"Updated SSID from {device} device: {value}")
            else:
                print_error(request, f"Failed to fetch SSID from {device} device on attempt {attempt + 1}")
            results[device] = value
        if all(v == new_ssid for v in results.values()):
            print_success(f"SSID successfully updated on all devices. Expected: {new_ssid}, Results: {results}")
            return True
        # Retry attempt logic
        if attempt < max_retries:
            print(f"SSID not updated yet. Expected: {new_ssid}, Results: {results}. Retrying in {retry_interval // 1000} seconds.")
            page.wait_for_timeout(retry_interval)
    # SSID failure
    print_error(request, f"SSID update FAILED after retries. Expected: {new_ssid}, Results: {results}")
    return False

def verify_password_update_in_controller_and_agent(config, request, ssh, new_pass, step):
    #Add 35s delay to allow changes to apply on device before SSH verification
    time.sleep(35)
    #Verify Password update on device via SSH command execution
    print_step(f"Step {step}: Fetch updated Password from controller device")
    query = (
        f"SELECT PassPhrase FROM {config['database']['ssid_table']} "
        "WHERE ID='Fronthaul@OneWifiMesh' LIMIT 1;"
    )
    query_out = get_db_values(config, ssh, query)
    if not query_out or not query_out.strip():
        print_error(request, "DB query returned empty output. Unable to fetch password.")
        return False
    else:
        rows = _get_non_empty_mysql_rows(query_out)
        if len(rows) != 1:
            print_error(request, f"Expected exactly 1 password row, found {len(rows)} rows")
            return False

        fronthaul_password = rows[0].strip()
        if not fronthaul_password:
            print_error(request, "Fetched Password from DB is empty")
            return False

        print_success(f"Updated Password from controller device: {fronthaul_password}")
        #Final validation to check if Password updates are consistent on controller device and match the expected value from test data. If there is a mismatch, print appropriate error message and fail the test.
        print_step(f"Step {step+1}: Validate if updated Password is consistent on controller device and matches the expected value")
        if len(fronthaul_password.strip()) != 0 and fronthaul_password.strip() != new_pass:
            print_error(request, f"Password update validation failed on controller device. Expected: {new_pass}, Actual: {fronthaul_password.strip()}")
            return False       
        else:
            print_success(f"Password update verification passed on controller device with expected value '{new_pass}'.")
            return True

def perform_wifi_scan_and_extract_bssid(client_name, wifi_client, fronthaul_ssid, request, ssh, step):
    # Execute WiFi scan on the client and filter results for the target SSID
    print_step(f"Step {step}: Perform WiFi Scan from {client_name} to discover available BSSIDs for SSID : {fronthaul_ssid}")
    # Before performing a Wi-Fi scan, it's best to disconnect the Wi-Fi interface if it is currently connected to any network to avoid scan issues.
    scan_cmd = f"nmcli -t -f BSSID,SSID device wifi list | grep {fronthaul_ssid}"
    print_step(f"Performing Wi-Fi scan from {client_name}")
    client_ip = wifi_client["ip"]
    client_user = wifi_client["user"]
    client_pass = wifi_client["pass"]
    client_scan = get_wifi_scan_result(client_ip, client_user, client_pass, fronthaul_ssid, ssh, scan_cmd)
    if client_scan:
        print_success("WiFi scan completed successfully.")
    else:
        print_error(request, "WiFi scan returned no results.")
        return []
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
        return []
    # Parse visible BSSIDs
    visible_bssids = []
    for line in client_scan_lines:
        bssid = line.split(":")[0] + ":" + ":".join(line.split(":")[1:6])
        visible_bssids.append(bssid.lower())
    print(f"Visible BSSIDs on {client_name}: {visible_bssids}")
    return visible_bssids

def connect_client_to_target_bssid(client_name, wifi_client, fronthaul_ssid, fronthaul_password, bssids, visible_bssids, request, ssh, device, step):
    # Select the first AP BSSID that is currently visible to the client
    print_step(f"Step {step}: Select the {device} BSSID that is currently visible")
    target_bssid = next((mac for mac in bssids if mac in visible_bssids), None)
    if target_bssid:
        print(f"Selected BSSID for {client_name} connection: {target_bssid}")
        print_success(f"Selected target BSSID: {target_bssid}")
    else:
        print_error(request, f"No fronthaul {device} BSSIDs are visible on client for SSID {fronthaul_ssid}")
        return False
    target_bssid = target_bssid.upper()
    # Connect the client to the selected fronthaul BSSID
    print_step(f"Step {step+1}: Connect the client to BSSID :{target_bssid} via nmcli")
    client_ip = wifi_client["ip"]
    client_user = wifi_client["user"]
    client_pass = wifi_client["pass"]
    # Fetch wireless interface of client
    client_wifi_intf = get_client_wifi_intf(client_ip, client_user, client_pass, ssh)
    connect_cmd = f"sudo -S nmcli device wifi connect '{fronthaul_ssid}' password '{fronthaul_password}' bssid {target_bssid} ifname {client_wifi_intf}"
    # Execute the command on the client device via SSH
    client_connect_out = ssh.run_client(client_ip, client_user, client_pass, connect_cmd, sudo_password=client_pass)
    # Fail the test if the connection was not successful
    if "successfully activated" in client_connect_out.lower():
        print_success(f"Client connected to fronthaul network of {device} successfully via the {target_bssid}")
        print_step(f"\nValidate {client_name}'s IP address assignment and internet connectivity on the wireless interface")
        # Verify Client IP assignment and internet connectivity
        try:
            verify_client_ip_and_internet(client_ip, client_user, client_pass, ssh, step+2)
            print_success("Client IP/internet verification successful")
            return True
        except Exception as e:
            print_error(request, f"Client IP/internet verification failed: {str(e)}")
            return False
    else:
        print_error(request, f"Client failed to connect to fronthaul network via BSSID {target_bssid}")
        return False

def validate_fronthaul_client_connectivity(config, request, ssh, step):
    fronthaul_ssid, fronthaul_password = get_fronthaul_credentials(config, request, ssh, step)
    if not fronthaul_ssid or not fronthaul_password:
        return
    for device in ssh.device_list:
        print_step(f"\nWireless client connectivity verification on {device}")
        print("Use the fronthaul credentials obtained in Step 1 as the common credentials for all devices.")
        bssids = get_fronthaul_bssids(device, request, ssh, step+1)
        if not bssids:
            continue
        for client_name, wifi_client in ssh.enabled_wifi_clients.items():
            # Perform WiFi scan from each Wi-Fi client and extract target BSSID for client connection
            print(f"\nVerify {client_name} connectivity with the {device}")
            visible_bssids = perform_wifi_scan_and_extract_bssid(client_name, wifi_client, fronthaul_ssid, request, ssh, step+2)
            if not visible_bssids:
                continue
            connect_client_to_target_bssid(client_name, wifi_client, fronthaul_ssid, fronthaul_password, bssids, visible_bssids, request, ssh, device, step+3)
