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

# Documentation: [test_basic_sanity_tc.py](Sanity_Tests_Documentation.md#test_basic_sanity_tcpy)

from playwright.sync_api import expect, sync_playwright
import pytest
import conftest
import utils
import playwright_utils
from utils import print_step, print_error, print_success
import json
import time

# Documentation: [TC-BASIC-01](Sanity_Tests_Documentation.md#tc-basic-01)
def test_onewifi_service_status(request, ssh):
    print_step("Entering Test1: test_onewifi_service_status")
    for step, device in enumerate(ssh.device_list, start=1):
        utils.verify_service_status(request, device, "onewifi", ssh, step)
    print_step("Exiting Test1: test_onewifi_service_status")
	
# Documentation: [TC-BASIC-02](Sanity_Tests_Documentation.md#tc-basic-02)
def test_verify_core_files_presence(request, ssh):
    print_step("Entering Test2: test_verify_core_files_presence")
    utils.verify_core_dump_generated(request, ssh)
    print_step("Exiting Test2: test_verify_core_files_presence")

# Documentation: [TC-BASIC-03](Sanity_Tests_Documentation.md#tc-basic-03)
def test_ieee1905_em_ctrl_service_status(request, ssh):
    print_step("Entering Test3: test_ieee1905_em_ctrl_service_status")
    utils.verify_service_status(request, "controller", "ieee1905_em_ctrl", ssh, 1)
    print_step("Exiting Test3: test_ieee1905_em_ctrl_service_status")

# Documentation: [TC-BASIC-04](Sanity_Tests_Documentation.md#tc-basic-04)
def test_em_ctrl_service_status(request, ssh):
    print_step("Entering Test4: test_em_ctrl_service_status")
    utils.verify_service_status(request, "controller", "em_ctrl", ssh, 1)
    print_step("Exiting Test4: test_em_ctrl_service_status")

# Documentation: [TC-BASIC-05](Sanity_Tests_Documentation.md#tc-basic-05)
def test_ieee1905_em_agent_service_status(request, ssh):
    print_step("Entering Test5: test_ieee1905_em_agent_service_status")
    for step, device in enumerate(ssh.device_list, start=1):
        utils.verify_service_status(request, device, "ieee1905_em_agent", ssh, step)
    print_step("Exiting Test5: test_ieee1905_em_agent_service_status")

# Documentation: [TC-BASIC-06](Sanity_Tests_Documentation.md#tc-basic-06)
def test_em_agent_service_status(request, ssh):
    print_step("Entering Test6: test_em_agent_service_status")
    for step, device in enumerate(ssh.device_list, start=1):
        utils.verify_service_status(request, device, "em_agent", ssh, step)
    print_step("Exiting Test6: test_em_agent_service_status")

# Documentation: [TC-BASIC-07](Sanity_Tests_Documentation.md#tc-basic-07)
def test_db_values_match_default_json(config, request, ssh): 
    print_step("Entering Test7: test_db_values_match_default_json")
    # Validate all SSID entries from Reset.json against DB dynamically.
    print_step(f"Step 1: Read the {config['system']['reset_json_file']} from Controller device")
    reset_json = utils.get_reset_json_data(config, ssh)
    json_ssids = reset_json.get(f"{config['database']['ssid_table']}")
    if not json_ssids:
        pytest.fail(f"Reset.json does not contain {config['database']['ssid_table']} entries")
    else:
        print_success(f"Reset.json contains {config['database']['ssid_table']} table")
    print_step(f"Step 2: Get the {config['database']['ssid_table']} table values from {config['database']['name']} database")
    db_ssids = utils.get_network_ssid_list_db(config, ssh)
    if db_ssids:
        print_success(f"{config['database']['name']} database contains {config['database']['ssid_table']} table.")
    else:
        print_error(request,f"{config['database']['name']} database doesn't contain {config['database']['ssid_table']} table.")
    # Use JSON HaulType to locate DB row by ID, then validate all other fields.
    print_step(f"Step 3: Validate all JSON and DB entries by using Haultype as ID")
    for json_entry in json_ssids:
        haul_type = json_entry.get("HaulType")
        if not haul_type:
            print_error(request, f"JSON entry missing HaulType: {json_entry}")
        if not isinstance(haul_type, list):
            haul_type = [haul_type]
        # Lookup DB row by matching ID containing HaulType
        db_row = next(
            (row for row in db_ssids if any(ht in row.get("ID", "") for ht in haul_type)),None)
        if not db_row:
            print_error(request, f"No DB row found with ID containing HaulType={haul_type}")
        print(f"\nValidating HaulType={haul_type} against DB ID={db_row.get('ID')}")
        print("DB row:", db_row)
        print("JSON entry:", json.dumps(json_entry, indent=4))
        # Prepare DB row with lowercase keys to resolve the case sensitive column values
        db_row_lower = {k.lower(): v for k, v in db_row.items()}
        all_fields_match = True
        for json_key, json_val in json_entry.items():
            if json_key == "ID":
                continue
            db_val = db_row_lower.get(json_key.lower())
            if db_val is None:
                print_error(request, f"{haul_type}: DB column for JSON key '{json_key}' not found")
                all_fields_match = False
            print(f"Validating field: {json_key} | DB={db_val} JSON={json_val}")
            # Boolean normalization: Checking fields that represent Boolean values
            if str(db_val).lower() in ["1", "0", "true", "false", "yes", "no"]:
                db_val_norm = utils.normalize_bool(db_val)
                json_val_norm = json_val if isinstance(json_val, bool) else utils.normalize_bool(json_val)
                if db_val_norm != json_val_norm:
                    print_error(request, f"{haul_type}: {json_key} mismatch. DB={db_val} JSON={json_val}")
                    all_fields_match = False
            # List comparison: # Checking fields that represent list values
            elif isinstance(json_val, list):
                for val in json_val:
                    if val not in db_val:
                        print_error(request, f"{haul_type}: {json_key} mismatch. DB={db_val} JSON={json_val}")
                        all_fields_match = False
            # Comparing fields as-is without any transformation
            elif str(db_val) != str(json_val):
                print_error(request, f"{haul_type}: {json_key} mismatch. DB={db_val} JSON={json_val}")
                all_fields_match = False
        if all_fields_match:
            print_success(f"HaulType={haul_type} validated successfully.\n")
    print_step("Exiting Test7: test_db_values_match_default_json")

@pytest.mark.parametrize(
    "pattern, ctrl_expected, agent_expected",
    [
        ("em*.log", 3, 1),
        ("ieee1905*.txt", 2, 1),
    ]
)
# Documentation: [TC-BASIC-08](Sanity_Tests_Documentation.md#tc-basic-08)
def test_log_files_presence(request, ssh, pattern, ctrl_expected, agent_expected):
    print_step("Entering Test8: test_log_files_presence")
    for count, device in enumerate(ssh.device_list, start=1):
        print_step(f"Step {count}: Verify if {pattern} log files are present on {device}")
        count_found = utils.run_command_fetch_output_from_device(f"find /tmp -maxdepth 1 -type f -name '{pattern}' | wc -l", device, ssh)
        expected_count = ctrl_expected if device == "controller" else agent_expected
        if int(count_found.strip()) != expected_count:
            print_error(request,
                f"Expected {expected_count} log files not found in /tmp on {device}.\n"
                f"Actual count: {count_found}"
            )
        print_success(f"{count_found} log files found in /tmp on {device}.")
    print_step("Exiting Test8: test_log_files_presence")

# Documentation: [TC-BASIC-09](Sanity_Tests_Documentation.md#tc-basic-09)
def test_broadcast_default_SSID(config, request, ssh):
    print_step("Entering Test9: test_broadcast_default_SSID")
    if not ssh.enabled_wifi_clients:
        print("No enabled Wi-Fi client detected. SSID broadcast verification requires at least one Wi-Fi client")
        pytest.skip("Test setup pre-requisite not met: at least one enabled Wi-Fi client is required.")
    # Expected default values
    CONFIG_MAP = config["database"]["network_ssid_map"]
    expected_fronthaul_ssid = CONFIG_MAP["Fronthaul"]["default_ssid"]
    expected_backhaul_ssid = CONFIG_MAP["Backhaul"]["default_ssid"]
    # Fetch Fronthaul SSID from DB
    print_step(f"Step 1: Fetch the default fronthaul SSID from OneWifiMesh DB")
    fronthaul_query = (f"SELECT SSID FROM {config['database']['ssid_table']} WHERE ID LIKE '%Fronthaul%OneWifiMesh%';")
    fronthaul_out = utils.get_db_values(config, ssh, fronthaul_query)
    if not fronthaul_out.strip():
        print_error(request, "No fronthaul SSID entry found in DB")
    fronthaul_ssid = fronthaul_out.strip()
    print(f"Fronthaul SSID from OneWifiMesh DB : {fronthaul_ssid}")
    if fronthaul_ssid != expected_fronthaul_ssid:
        print_error(request, f"Default fronthaul SSID mismatch In OneWifiMesh DB. Expected: {expected_fronthaul_ssid}, Found: {fronthaul_ssid}")
    print_success(f"Fronthaul SSID from OneWifiMesh DB matched the default value")
    # Fetch Backhaul SSID from DB
    print_step(f"Step 2: Fetch the default backhaul SSID from OneWifiMesh DB")
    backhaul_query = (f"SELECT SSID FROM {config['database']['ssid_table']} WHERE ID LIKE '%Backhaul%OneWifiMesh%';")
    backhaul_out = utils.get_db_values(config, ssh, backhaul_query)
    if not backhaul_out.strip():
        print_error(request, "No backhaul SSID entry found in DB")
    backhaul_ssid = backhaul_out.strip()
    print(f"Backhaul SSID from OneWifiMesh DB: {backhaul_ssid}")
    if backhaul_ssid != expected_backhaul_ssid:
        print_error(request, f"Default backhaul SSID mismatch in OneWifiMesh DB. Expected: {expected_backhaul_ssid}, Found: {backhaul_ssid}")
    print_success(f"Backhaul SSID from OneWifiMesh DB matched the default value")
    for client_name, wifi_client in ssh.enabled_wifi_clients.items():
        client_ip = wifi_client["ip"]
        client_user = wifi_client["user"]
        client_pass = wifi_client["pass"]
        # Perform a WiFi scan to verify that the default SSID is being broadcast.
        print_step(f"Step 3: Verify if SSIDs are visible from client device : {client_name}")
        # Fronthaul scan
        print(f"Scanning for SSID: {expected_fronthaul_ssid}")
        scan_cmd = f"nmcli -t -f BSSID,SSID device wifi list | grep {expected_fronthaul_ssid}"
        client_scan = utils.get_wifi_scan_result(client_ip, client_user, client_pass, expected_fronthaul_ssid, ssh, scan_cmd)
        client_scan = client_scan.replace("\\:", ":")
        print(f"Client scan result:\n{client_scan}")
        if expected_fronthaul_ssid not in client_scan:
            print_error(request, f"{client_name} cannot see SSID: {expected_fronthaul_ssid}")
        else:
            print_success(f"{client_name} detects {expected_fronthaul_ssid}")
        # Backhaul scan
        print(f"Scanning for SSID: {expected_backhaul_ssid}")
        scan_cmd = f"nmcli -t -f BSSID,SSID device wifi list | grep {expected_backhaul_ssid}"
        client_scan = utils.get_wifi_scan_result(client_ip, client_user, client_pass, expected_backhaul_ssid, ssh, scan_cmd)
        client_scan = client_scan.replace("\\:", ":")
        print(f"Client scan result:\n{client_scan}")
        if expected_backhaul_ssid not in client_scan:
            print_error(request, f"{client_name} cannot see SSID: {expected_backhaul_ssid}")
        else:
            print_success(f"{client_name} detects {expected_backhaul_ssid}")
    print_step("Exiting Test9: test_broadcast_default_SSID")

# Documentation: [TC-BASIC-10](Sanity_Tests_Documentation.md#tc-basic-10)
def test_verify_agent_connectivity_to_default_gateway(request, ssh):
    print_step("Entering Test10: test_verify_agent_connectivity_to_default_gateway")
    for extender in ssh.enabled_extenders:
        print_step(f"Step 1: Verify agent connectivity to default gateway through extender {extender}")
        agent_out = utils.run_command_fetch_output_from_device("ping 10.0.0.1 -c 5", extender, ssh)
        print_step("Step 2: Verify agent connectivity to default gateway")
        print(f"Ping output:\n{agent_out}")
        if "0% packet loss" not in agent_out:
            print_error(request, f"Agent device {extender} does NOT have connectivity to default gateway. " f"Ping output: {agent_out}")
        else:
            print_success(f"Agent device {extender} has connectivity to default gateway")
    print_step("Exiting Test10: test_verify_agent_connectivity_to_default_gateway")

# Documentation: [TC-BASIC-11](Sanity_Tests_Documentation.md#tc-basic-11)
def test_ssh_controller_agent_connectivity(ssh):
    print_step("Entering Test11: test_ssh_controller_agent_connectivity")
    for count, device in enumerate(ssh.device_list, start=1):
        print_step(f"Step {count}: Verify SSH connectivity to {device} device")
        out = utils.run_command_fetch_output_from_device("cat /version.txt", device, ssh)
        print_success(f"SSH connectivity to {device} verified successfully. Firmware version: {out.strip()}")
    print_step("Exiting Test11: test_ssh_controller_agent_connectivity")	

# Documentation: [TC-BASIC-12](Sanity_Tests_Documentation.md#tc-basic-12)
def test_verify_rdkbcli_browser_launch(config, page):
    print_step("Entering Test12: test_verify_rdkbcli_browser_launch")
    #Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 1)
    time.sleep(5)
    print_step("Exiting Test12: test_verify_rdkbcli_browser_launch")

# Documentation: [TC-BASIC-13](Sanity_Tests_Documentation.md#tc-basic-13)
def test_verify_rdkbcli_tab_navigation(config, page, request, paths):
    print_step("Entering Test13: test_verify_rdkbcli_tab_navigation")
    #Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 1)
    #Navigate to Wireless Settings page
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 2, paths)
    time.sleep(5)
    # Click "Network Topology" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Network Topology', 3, paths)
    time.sleep(5)
    # Click "Coverage Map" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Coverage Map', 4, paths)
    time.sleep(5)
    # Click "Mesh Devices" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Mesh Devices', 5, paths)
    time.sleep(5)
    # Click "Connected Clients" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Connected Clients', 6, paths)
    time.sleep(5)
    # Click "Wireless Settings" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 7, paths)
    time.sleep(5)
    # Click "Policy Settings" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Policy Settings', 8, paths)
    time.sleep(5)
    # Click "Performance" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Performance', 9, paths)
    time.sleep(5)
    # Click "RF Analysis" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'RF Analysis', 10, paths)
    time.sleep(5)
    # Click "Security Center" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Security Center', 11, paths)
    time.sleep(5)
    # Click "System Settings" from sidebar and verify correct page is loaded
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'System Settings', 12, paths)
    time.sleep(5)
    #These are yet to be implemented(blank) in RDKB CLI, so commenting out for now. Will enable once the features are available to test.
    # Click "Firmware" from sidebar and verify correct page is loaded
    #playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Firmware', 13, paths)
    #time.sleep(5)
    # Click "Reports" from sidebar and verify correct page is loaded
    #playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Reports', 14, paths)
    #time.sleep(5)    
    print_step("Exiting Test13: test_verify_rdkbcli_tab_navigation")
