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
import shlex
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
    cmd = "nmcli -t -f DEVICE,TYPE device status | awk -F: '$2 == \"wifi\" {print $1; exit}'"
    result = ssh.run_client(client_ip, client_user, client_pass, cmd)
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
    expected_ssids = {
        name: ssid_map[name]["default_ssid"]
        for name in ["Fronthaul", "IoT", "Backhaul"]
    }
    for device in ssh.device_list:
        try:
            out = run_command_fetch_output_from_device("iw dev | grep ssid", device, ssh)
        except Exception as e:
            errors.append(f"Unable to fetch configured VAPs on {device}: {e}")
            continue
        detected_ssids = [line.strip().removeprefix("ssid ").strip() for line in out.splitlines() if line.strip()]
        missing = {
            profile: ssid for profile, ssid in expected_ssids.items()
            if ssid not in detected_ssids
        }
        if missing:
            expected_details = ", ".join(f"{profile}='{ssid}'" for profile, ssid in expected_ssids.items())
            missing_details = ", ".join(f"{profile}='{ssid}'" for profile, ssid in missing.items())
            detected_details = ", ".join(f"'{ssid}'" for ssid in detected_ssids) or "none"
            message = (
                f"VAP validation failed on {device}. Missing configured profile(s): {missing_details}. "
                f"Expected default SSIDs: {expected_details}. Detected SSIDs: {detected_details}."
            )
            print(f"Fail: {message}\n")
            errors.append(message)
        else:
            print(f"Pass: All configured VAPs are up on the {device} device. Detected SSIDs: {', '.join(detected_ssids)}\n")
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
                # Transient empty reads are expected during propagation; only fail at terminal retry.
                print(f"WARN: Failed to fetch SSID from {device} device on attempt {attempt + 1}")
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

def verify_password_update_in_controller_db(config, request, ssh, new_pass, step):
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
    # Execute WiFi scan on the client and extract visible BSSIDs for the target SSID.
    print_step(f"Step {step}: Perform WiFi Scan from {client_name} to discover available BSSIDs for SSID : {fronthaul_ssid}")
    print_step(f"Performing Wi-Fi scan from {client_name}")
    client_ip = wifi_client["ip"]
    client_user = wifi_client["user"]
    client_pass = wifi_client["pass"]

    # Identify Wi-Fi interface explicitly so scan/rescan use a deterministic interface.
    try:
        client_wifi_intf = get_client_wifi_intf(client_ip, client_user, client_pass, ssh)
    except Exception:
        print_error(request, f"{client_name}: Wi-Fi interface was not found")
        return [], None

    # Disconnect first so nmcli does a clean scan and doesn't bias cached connected profile info.
    check_cmd = f"nmcli -t -f DEVICE,STATE device status | grep -E '^{client_wifi_intf}:(connected|connecting)'"
    check_output = ssh.run_client(client_ip, client_user, client_pass, check_cmd)
    if check_output.strip():
        disconnect_cmd = f"sudo -S nmcli device disconnect {shlex.quote(client_wifi_intf)}"
        ssh.run_client(client_ip, client_user, client_pass, disconnect_cmd, sudo_password=client_pass)

    scan_cmd = "nmcli -t --escape no -f BSSID,SSID device wifi list"
    visible_bssids = []
    last_seen_ssids = []
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        # Force a fresh scan before listing results to avoid stale nmcli cache.
        rescan_cmd = f"sudo -S nmcli device wifi rescan ifname {shlex.quote(client_wifi_intf)}"
        ssh.run_client(client_ip, client_user, client_pass, rescan_cmd, sudo_password=client_pass)
        time.sleep(5)

        # Read BSSID/SSID using stable machine-friendly output.
        scan_output = ssh.run_client(client_ip, client_user, client_pass, scan_cmd)
        if not scan_output or not scan_output.strip():
            continue

        visible_bssids = []
        seen_ssids = []
        for line in scan_output.splitlines():
            row = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", line).strip().replace("\\:", ":")
            if len(row) > 18 and row[17] == ":":
                scanned_bssid = row[:17]
                scanned_ssid = row[18:]
                if re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", scanned_bssid):
                    if scanned_ssid:
                        seen_ssids.append(scanned_ssid)
                    if scanned_ssid == fronthaul_ssid:
                        visible_bssids.append(scanned_bssid.lower())

        last_seen_ssids = sorted(set(seen_ssids))[:15]
        if visible_bssids:
            break
        print(f"{client_name}: scan attempt {attempt}/{max_attempts} did not find SSID '{fronthaul_ssid}'.")

    if not visible_bssids:
        print_error(
            request,
            f"No {fronthaul_ssid} networks found on client. "
            f"Recently seen SSIDs: {last_seen_ssids}"
        )
        return [], client_wifi_intf

    print_success(f"Valid BSSIDs found in scan: {visible_bssids}")
    print(f"Visible BSSIDs on {client_name}: {visible_bssids}")
    return visible_bssids, client_wifi_intf

def connect_client_to_target_bssid(client_name, wifi_client, fronthaul_ssid, fronthaul_password, bssids, visible_bssids, client_wifi_intf, request, ssh, device, step):
    # Select the first AP BSSID that is currently visible to the client
    print_step(f"Step {step}: Select the {device} BSSID that is currently visible")
    target_bssid = next((mac for mac in bssids if mac in visible_bssids), None)
    if target_bssid:
        print(f"Selected BSSID for {client_name} connection: {target_bssid}")
        print_success(f"Selected target BSSID: {target_bssid}")
    else:
        print(
            f"No {device} BSSID matched the scan. Expected: {bssids}; "
            f"visible: {visible_bssids}"
        )
        target_bssid = next(iter(visible_bssids), None)
        if not target_bssid:
            print_error(request, f"No fronthaul {device} BSSIDs are visible on client for SSID {fronthaul_ssid}")
            return False
    target_bssid = target_bssid.upper()
    # Connect the client to the selected fronthaul BSSID
    print_step(f"Step {step+1}: Connect the client to BSSID :{target_bssid} via nmcli")
    client_ip = wifi_client["ip"]
    client_user = wifi_client["user"]
    client_pass = wifi_client["pass"]
    connect_cmd = (
        f"sudo -S nmcli device wifi connect {shlex.quote(fronthaul_ssid)} "
        f"password {shlex.quote(fronthaul_password)} bssid {target_bssid} "
        f"ifname {shlex.quote(client_wifi_intf)}"
    )
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
            visible_bssids, client_wifi_intf = perform_wifi_scan_and_extract_bssid(client_name, wifi_client, fronthaul_ssid, request, ssh, step+2)
            if not visible_bssids:
                continue
            connect_client_to_target_bssid(client_name, wifi_client, fronthaul_ssid, fronthaul_password, bssids, visible_bssids, client_wifi_intf, request, ssh, device, step+3)

def verify_iw_dev_interface_value(config, ssh, request, expected_type, step):
    # Verify SSID values for each interface using iw dev against expected configuration
    print_step(f"Step {step}: Verify that ALL interface SSIDs match expected {expected_type} configuration via iw dev.")
    verification_failed = False
    ssid_map = config["database"]["network_ssid_map"]
    expected_map = {
        "Fronthaul": ssid_map["Fronthaul"][f"{expected_type}_ssid"],
        "Backhaul": ssid_map["Backhaul"][f"{expected_type}_ssid"],
        "IoT": ssid_map["IoT"][f"{expected_type}_ssid"]
    }
    # Expected mandatory interfaces
    expected_interfaces = {
        "mld0": "Fronthaul"
    }
    for i in range(3):
        expected_interfaces[f"wifi{i}.1"] = "Backhaul"
        expected_interfaces[f"wifi{i}.2"] = "IoT"
    for device in ssh.device_list:
        try:
            output = run_command_fetch_output_from_device("iw dev", device, ssh)
        except Exception as e:
            verification_failed = True
            print_error(request, f"{device}: Failed to retrieve interface details. Error: {str(e)}")
            continue
        current_iface = None
        iface_ssid_map = {}
        # Parse iw dev output
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                current_iface = line.split()[1]
            elif line.startswith("ssid") and current_iface:
                ssid = line.split("ssid", 1)[1].strip()
                iface_ssid_map[current_iface] = ssid
        device_failed = False
        # Check missing interfaces first
        for expected_iface in expected_interfaces:
            if expected_iface not in iface_ssid_map:
                device_failed = True
                verification_failed = True
                print_error(request, f"{device}: Missing interface {expected_iface}")
        # Validate SSID values
        for iface, expected_band in expected_interfaces.items():
            if iface not in iface_ssid_map:
                continue
            ssid = iface_ssid_map[iface]
            expected_ssid = expected_map[expected_band]
            if ssid == expected_ssid:
                print_success(f"{device} - {expected_band}: SSID '{ssid}' is correctly configured on {iface} after Wi-Fi Reset.")
            else:
                device_failed = True
                verification_failed = True
                print_error(request, f"{device} - {expected_band}: SSID mismatch on {iface}. Expected: {expected_ssid}, Actual: {ssid}")
        if device_failed:
            print_error(request, f"{device}: Interface SSID validation failed.\nCommand Output:\n{output}")
    if verification_failed:
        pytest.fail(f"Interface SSID values do not match expected {expected_type} configuration.")
    print_success(f"Completed verification of interface SSID values via iw dev for {expected_type} configuration.")

def verify_wifi_db_values(config, ssh, request, expected_type, step):
    # Verify the OneWifiMesh DB values correspond to the expected values for each haul type.
    print_step(f"Step {step}: Verify the OneWifiMesh DB values correspond to the expected {expected_type} values for each haul type.")
    verification_failed = False
    ssid_map = config["database"]["network_ssid_map"]
    for haul_id, cfg in ssid_map.items():
        expected_ssid = cfg[f"{expected_type}_ssid"]
        expected_pass = cfg[f"{expected_type}_pass"]
        print(
            f"Haul Type: {haul_id}\n"
            f"Expected SSID: {expected_ssid}\n"
            f"Expected Password: {expected_pass}"
        )
        query = (
            f"SELECT SSID, PassPhrase FROM {config['database']['ssid_table']} "
            f"WHERE ID LIKE '%{haul_id}%OneWifiMesh%';"
        )
        query_out = get_db_values(config, ssh, query)
        db_output = query_out.strip().split()
        if len(db_output) < 2:
            verification_failed = True
            print_error(request, f"Invalid DB response (expected 2 values): {query_out}")
            continue
        db_ssid, db_pass = db_output[0], db_output[1]
        if db_ssid == expected_ssid and db_pass == expected_pass:
            print_success(f"{haul_id} DB Data - SSID: {db_ssid} Password: {db_pass}")
            if expected_type == "default":
                print_success(f"Wi-Fi reset completed successfully for haul type {haul_id}; default SSID and password restored correctly.")
            else:
                print_success("Wi-Fi reset completed successfully; custom SSID and password applied correctly.")
        else:
            verification_failed = True
            if db_ssid != expected_ssid:
                print_error(request, f"{haul_id}: SSID mismatch after Wi-Fi reset. Expected: {expected_ssid}, Actual: {db_ssid}")
            if db_pass != expected_pass:
                print_error(request, f"{haul_id}: Password mismatch after Wi-Fi reset. Expected: {expected_pass}, Actual: {db_pass}")
    if verification_failed:
        pytest.fail(f"OneWifiMesh DB values do not match expected {expected_type} values.")
    print_success(f"Completed verification of OneWifiMesh DB values with expected {expected_type} values for each haul type.")

def reboot_device_after_wifi_reset(ssh, request, step):
    # Reboot all connected devices (extenders first, then controller)
    print_step(f"Step {step}: Reboot all connected devices after Wi-Fi reset and verify reachability.")
    # Reboot all the connected extenders
    print_step(f"Step {step}.1: Initiating reboot on all extenders.")
    for extender in ssh.enabled_extenders:
        try:
            print(f"Triggering reboot on extender: {extender}")
            run_command_fetch_output_from_device("reboot", extender, ssh)
            print_success(f"Reboot command executed successfully on extender: {extender}")
        except Exception as e:
            print_error(request, f"Failed to reboot extender {extender}: {str(e)}")
    # Reboot the controller
    print_step(f"Step {step}.2: Triggering reboot on controller device.")
    try:
        run_command_fetch_output_from_device("systemctl reboot", "controller", ssh)
        print_success("Reboot command executed successfully on controller.")
    except Exception as e:
        print_error(request, f"Failed to reboot controller: {str(e)}")
    # Wait for reboot completion
    print_step(f"Step {step}.3: Wait and verify the controller connection after reboot.")
    # Initial wait after controller reboot.
    time.sleep(180)
    assert ssh.wait_for_controller(timeout=180, interval=60), "Controller did not come back after reboot"
    print_success("Controller is back. Clearing stale extender tunnels.")
    # Clear stale extender tunnels
    ssh.clear_extender_sessions()
    # Wait for mesh formation.
    time.sleep(120)
    print_step(f" Step {step}.4: Wait and verify all the extender connection after reboot.")
    for device in ssh.enabled_extenders:
        assert ssh.wait_for_extender(device, timeout=360, interval=60), f"{device} did not come back after reboot"
    print_success("All extenders are back after reboot.")
    # After reboot, wait for the mesh connection to stabilize.
    print("Allow EasyMesh to stabilize (wait 1 minute).")
    time.sleep(60)
