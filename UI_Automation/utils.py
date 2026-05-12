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

def verify_service_status(request, service_name, device, output):
    print(f"{service_name} service status command output from {device}: {output}")
    if "active" not in output:
        print_error(request, f"{service_name} service is NOT running on {device}:\n{output}")
    else:
        print_success(f"{service_name} service is running as expected on {device} device")
    
def get_client_ip_interface_status(request, ssh, commands, client_ip, client_user, client_pass):
    outputs = []
    for command in commands:
        output = ssh.run_client(client_ip, client_user, client_pass, command, sudo_password = client_pass)
        outputs.append(output.strip())
    ip, interface, active_status = outputs[0], outputs[1], outputs[2]
    return ip, interface, active_status

def verify_core_dump_generated(config, request, ssh):
    device_list = ["controller"] + list(config.get("extenders", {}).keys())
    for device in device_list:
        out = ssh.run(device, command="ls /tmp/*dmp* 2>/dev/null")        
        print(f"Core files presence command output from {device}: {out}")
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
    output = ssh.run(device, f"ifconfig {interface_name}")
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
    ctrl_out = ssh.run("controller", cmd)
    return ctrl_out

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
    out = ssh.run("controller", cmd)
    try:
        data = json.loads(out)
    except Exception as e:
        pytest.fail(f"Failed to parse Reset.json: {e}")
    return data.get("wfa-dataelements:Reset")

def get_network_ssid_list_db(config, request, ssh):
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

def get_fronthaul_credentials(config, ssh):
    #Fetch the current fronthaul SSID and password from OneWifiMesh DB
    try:
        query = (f"SELECT SSID, PassPhrase FROM {config['database']['ssid_table']} WHERE ID LIKE '%Fronthaul%OneWifiMesh%';")
        query_out = get_db_values(config, ssh, query)
        # Check if query returned anything
        if not query_out.strip():
            pytest.fail("No fronthaul SSID entry found in DB matching pattern")
        # Split lines in case multiple rows returned
        rows = query_out.strip().splitlines()
        if len(rows) != 1:
            pytest.fail(f"Expected exactly 1 matching fronthaul SSID row, found {len(rows)} rows")
        # Extract SSID and password from query output
        ssid, password = rows[0].split("\t")
        if not ssid or not password:
            pytest.fail("Fetched fronthaul SSID or password is empty")
        print(f"Fetched fronthaul credentials: SSID={ssid}, Password={password}")
        return ssid, password
    except Exception as e:
        pytest.fail(f"Failed to fetch fronthaul credentials from DB: {e}")

def get_fronthaul_bssids(device, ssh):
    # Fetch all BSSID values for the fronthaul network, includes 2.4GHz, 5GHz, and 6GHz radios.
    try:
        iw_output = ssh.run(device, "iw dev mld0 info")
    except Exception as e:
        pytest.fail(f"Failed to fetch BSSIDs from {device}: {e}")
    bssids = re.findall(r"link addr ([0-9a-fA-F:]{17})", iw_output)
    if not bssids:
        pytest.fail(f"No fronthaul BSSIDs found on {device}")
    print(f"Fetched BSSIDs from {device}: {bssids}")
    return bssids

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
        print_step(f"Step {step}b: Verify internet connectivity from client interface '{client_wifi_intf}' by pinging www.google.com")
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
    output = ssh.run("controller", cmd_device_count)
    if not output:
        pytest.fail(f"SSH command returned empty output: {cmd_device_count}")
    device_count = int(re.search(r"value:\s*(\d+)", output).group(1))
    device_ssid_map = {}
    for i in range(1, device_count + 1):
        # Get unique ID (Mac address) for each device
        cmd_device_id = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.ID | grep 'value:'"
        output = ssh.run("controller", cmd_device_id)
        device_id = re.search(r"value:\s*(.+)", output).group(1).strip()
        device_ssid_map[device_id] = {}
        # Get number of Radios for each device
        cmd_radio_count = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.RadioNumberOfEntries | grep 'value:'"
        output = ssh.run("controller", cmd_radio_count)
        radio_count = int(re.search(r"value:\s*(\d+)", output).group(1))
        for r in range(1, radio_count + 1):
            # Get number of BSS entries for each Radio
            cmd_bss_count = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSSNumberOfEntries | grep 'value:'"
            output = ssh.run("controller", cmd_bss_count)
            bss_count = int(re.search(r"value:\s*(\d+)", output).group(1))
            for b in range(1, bss_count + 1):
                # Get SSID value for each BSS
                cmd_ssid = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSS.{b}.SSID | grep 'value:'"
                ssid_output = ssh.run("controller", cmd_ssid)
                ssid = re.search(r"value:\s*(.+)", ssid_output).group(1).strip()
                # Get BSSID value for each BSS
                cmd_bssid = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.Radio.{r}.BSS.{b}.BSSID | grep 'value:'"
                bssid_output = ssh.run("controller", cmd_bssid)
                bssid = re.search(r"value:\s*([0-9a-f:]{17})", bssid_output).group(1).lower()
                if ssid not in device_ssid_map[device_id]:
                    device_ssid_map[device_id][ssid] = {'bssids': [], 'mld_mac': None}
                device_ssid_map[device_id][ssid]['bssids'].append(bssid)
        # Only fetch first MLD entry, if private SSID exists (This is because of limited info available)
        for ssid_name in device_ssid_map[device_id]:
            if ssid_name.lower().startswith("private"):
                cmd_mld_mac = f"dmcli eRT getv Device.WiFi.DataElements.Network.Device.{i}.APMLD.1.MLDMACAddress | grep 'value:'"
                output = ssh.run("controller", cmd_mld_mac)
                if output:
                    mld_mac_match = re.search(r"value:\s*([0-9a-f:]{17})", output)
                    if mld_mac_match:
                        device_ssid_map[device_id][ssid_name]['mld_mac'] = mld_mac_match.group(1).lower()
                break
    return device_ssid_map, device_count

def get_sta_interfaces_from_bridge(ssh, device, bridge_intf):
    # Get the list of station interfaces from the bridge.
    br_output = ssh.run(device, f"brctl show {bridge_intf}")
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
    dump = ssh.run(device, f"iw dev {sta_iface} station dump")
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
    CONFIG_MAP = {
        item["haul_id"]: item
        for item in conftest.DB_DEFAULT_DATA
    }
    expected_ssids = [
        CONFIG_MAP["Fronthaul"]["default_ssid"],
        CONFIG_MAP["IoT"]["default_ssid"],
        CONFIG_MAP["Backhaul"]["default_ssid"],
    ]
    device_list = ["controller"] + list(
        config.get("extenders", {}).keys()
    )
    for device in device_list:
        out = ssh.run(device, "iw dev | grep ssid")        
        missing = [
            ssid for ssid in expected_ssids
            if ssid not in out
        ]
        if missing:
            pytest.fail(f"Missing VAPs on {device}: {missing}\n Command Output:\n{out}")
        else:
            print(f"All configured VAPs are up on the {device} device:\n{out}")

def verify_mld0_interface_presence(config, ssh, db_default_data):
    """
    Verify that mld0 interface is present on all devices (controller and extenders).
    """
    print("\n[Mesh Setup Verification 2/5] Verifying mld0 interface presence on all devices...")
    command = "iw dev mld0 info && (iw dev mld0 info | wc -l)"
    device_list = ["controller"] + list(config.get("extenders", {}).keys())
    for step, device in enumerate(device_list, start=1):
        out = ssh.run(device, command)
        print(f"  Step {step}: Verify mld0 interface on {device}")
        try:
            line_count = int(out.split()[-1])
        except (IndexError, ValueError):
            pytest.fail(f"Unexpected output from {device}: {out}")
        if line_count == 0:
            pytest.fail(f"mld0 interface is NOT present on {device}. Output: {out}")
        print(f"mld0 interface is present on {device}")

def verify_mld0_links_to_privatevaps(config, ssh, db_default_data):
    """
    Verify that mld0 has correct number of links and each link maps to the corresponding wifi interface.
    """
    print("\n[Mesh Setup Verification 3/5] Verifying mld0 links map to private VAPs...")    
    device_list = ["controller"] + list(config.get("extenders", {}).keys())
    expected_links = 3
    # Verify number of mld0 links
    command_links = "iw dev mld0 info | grep 'link ID' | wc -l"
    for step, device in enumerate(device_list, start=1):
        out = ssh.run(device, command_links)
        links = out.strip()
        print(f"  Step {step}: Checking mld0 link count on {device}: {links}")        
        if links != str(expected_links):
            pytest.fail(f"{device} expected {expected_links} links but found {links}")            
        print(f"Step {step}: {device} has expected {expected_links} links")

    # Verify MAC mapping for each link
    for count, link_id in enumerate(range(expected_links), start=3):
        print(f"  Step {count}: Verifying link ID {link_id} corresponds to wifi{link_id}")

        for device in device_list:
            # Get wifi MAC
            wifi_cmd = f"iw dev wifi{link_id} info | awk '/addr/ {{print $2}}'"
            wifi_mac = ssh.run(device, wifi_cmd).strip().replace("\r", "")
            # Get mld0 MAC for this link (parse in Python)
            mld_out = ssh.run(device, "iw dev mld0 info")
            mld_mac = None
            for line in mld_out.splitlines():
                line = line.strip()
                if line.startswith(f"- link ID  {link_id} link addr"):
                    mld_mac = line.split()[-1].strip()
                    break
            if not mld_mac:
                pytest.fail(f"{device} mld0 MAC for link {link_id} not found")                
            print(f"  {device} wifi{link_id} MAC: {wifi_mac}")
            print(f"  {device} mld0 link {link_id} MAC: {mld_mac}")
            if wifi_mac != mld_mac:
                pytest.fail(
                    f"{device} mismatch for link {link_id}. "
                    f"wifi{link_id}: {wifi_mac}, mld0: {mld_mac}"
                )

            print(f"Step {count}: {device} link {link_id} correctly maps to wifi{link_id}")

def verify_mesh_backhaul_interfaces(config, ssh, db_default_data):
    """
    Verify that mesh backhaul interfaces have the correct SSID configured.
    """
    print("\n[Mesh Setup Verification 4/5] Verifying mesh backhaul interface SSIDs...")
    device_list = ["controller"] + list(config.get("extenders", {}).keys())
    
    # Get expected backhaul SSID from DB_DEFAULT_DATA
    config_map = {item["haul_id"]: item for item in db_default_data}
    expected_ssid = config_map["Backhaul"]["default_ssid"]
    
    def get_interface(device):
        return "wifi1.1" if device == "controller" else "wifi1.3"
    
    for count, device in enumerate(device_list, start=1):
        interface = get_interface(device)
        print(f"  Step {count}: Verifying mesh backhaul SSID on {device} interface {interface}")
        cmd = f"iw dev {interface} info | grep ssid | awk '{{print $2}}'"
        out = ssh.run(device, cmd).strip()
        print(f"  {device.capitalize()} {interface} SSID: {out}")
        if out != expected_ssid:
            pytest.fail(
                f"Mesh backhaul SSID mismatch on {device} interface {interface}. "
                f"Expected: {expected_ssid}, Found: {out}"
            )            
        else:
            print(f"Step {count}: {device} interface {interface} correctly has SSID '{expected_ssid}'")

def verify_mesh_backhaul_extenders_connected(config, ssh, db_default_data):
    """
    Verify that extenders are connected via mesh backhaul STA interfaces on the controller.
    """
    print("\n[Mesh Setup Verification 5/5] Verifying extenders connected via mesh backhaul...")
    # Get STA interfaces from the bridge
    sta_interfaces = get_sta_interfaces_from_bridge(ssh, "controller", config["system"]["bridge_intf"])
    if not sta_interfaces:
        pytest.fail(f"No STA interfaces found on bridge {config['system']['bridge_intf']} on controller")        
    print(f"Found STA interfaces on {config['system']['bridge_intf']}: {sta_interfaces}")
    # Check each STA interface
    for count, interface in enumerate(sta_interfaces, start=1):
        print(f"  Step {count}: Verifying mesh backhaul interface {interface}")
        # Get full interface info
        cmd_info = f"iw dev {interface} info"
        info_out = ssh.run("controller", cmd_info).strip()
        print(f"  Output of 'iw dev {interface} info':\n{info_out}")
        # Check connected extenders
        cmd_dump = f"iw dev {interface} station dump"
        station_out = ssh.run("controller", cmd_dump).strip()
        print(f"  Output of 'iw dev {interface} station dump':\n{station_out}")
        if not station_out:
            pytest.fail(f"No extenders connected to mesh backhaul interface {interface}")
        print(f"Step {count}: Interface {interface} has extenders connected\n")