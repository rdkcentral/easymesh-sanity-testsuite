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

def get_interface_mac_address(config, ssh):
    ctrl_ip = config["controller"]["ip"]
    # Run ifconfig remotely via SSH
    interface_name = config["system"]["wifi_reset_interface"]
    print(f"Fetch MAC address of interface '{interface_name}' on {ctrl_ip} via SSH")
    output = ssh.run("controller", f"ifconfig {interface_name}")
    # Parse MAC address
    mac_match = re.search(r"(?:HWaddr|ether)\s+([0-9a-fA-F:]{17})", output, re.IGNORECASE)
    if not mac_match:
        pytest.fail(f"MAC address not found for {interface_name}")
    mac_address = mac_match.group(1)
    print_success(f"MAC address of {interface_name} on {ctrl_ip}: {mac_address}")
    return mac_address

def get_db_values(config, ssh, query):
    #Run MySQL query on device via SSH and return output
    cmd = f"mysql -N --batch -u {config["database"]["user"]} -p{config["database"]["pass"]} -D {config["database"]["name"]} -e \"{query}\""
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
        query = (f"SELECT SSID, PassPhrase FROM {config["database"]["ssid_table"]} WHERE ID LIKE '%Fronthaul%OneWifiMesh%';")
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