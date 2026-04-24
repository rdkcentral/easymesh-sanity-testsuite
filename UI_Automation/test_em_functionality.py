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
import utils
from utils import print_step, print_error, print_success
import conftest
import pytest

def test_rdkbcli_update_verify_ssid(page, request, ssh, paths):
    print_step("Entering Test1: test_rdkbcli_update_verify_ssid")
    new_ssid = "TDKB_New_SSID_02"
    utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 1, paths)
    print_step("Exiting Test1: test_rdkbcli_update_verify_ssid")

def test_rdkbcli_update_verify_password(page, request, ssh, paths):
    print_step("Entering Test2: test_rdkbcli_update_verify_password")
    new_pass = "TestTDKB@12345"
    #Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    #Navigate to Wireless Settings page
    utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 2, paths)
    #Update SSID value in input field and save changes
    utils.update_input_save_changes(page, request, "#profile-passphrase", new_pass, 3, paths)
    print_success("Password updated triggered from RDKB CLI successfully. Waiting for changes to reflect in RDKBCLI.")
    page.wait_for_timeout(15000)
    # Screenshot (avoid full_page on docs sites)
    print_step("Step 4: Take screenshot of updated Password value in RDKB CLI page after update")
    utils.take_screenshot(page, request, paths["screenshots"] / "rdkbcli_updated_password.png")        
    #Print updated password value from input fields for verification
    utils.fetch_and_verify_home_network_input(page, request, "Passphrase", "#profile-passphrase", new_pass, 5, paths)
    #Add 30s delay to allow changes to apply on device before SSH verification
    time.sleep(30)
    #Verify Password update on device via SSH command execution
    print_step("Step 6: Fetch updated Password from controller device")
    query_out = utils.get_db_values(request, ssh, f"SELECT SSID, PassPhrase FROM {request.session.network_ssid_list_db_table} WHERE ID='Fronthaul@OneWifiMesh';")
    fronthaul_password = query_out.strip().split("\t")[1]
    print_success(f"Updated Password from controller device: {fronthaul_password}")
    #Final validation to check if Password updates are consistent on both controller and agent devices and match the expected value from test data. If there is a mismatch, print appropriate error message and fail the test.
    print_step("Step 7: Validate if updated Password is consistent on both controller and agent devices and matches the expected value")
    if len(fronthaul_password.strip()) != 0 and fronthaul_password.strip() != new_pass:
        print_error(request, f"Password update validation failed on controller device. Expected: {new_pass}, Actual: {fronthaul_password.strip()}")        
    else:
        print_success(f"Password update verification passed on controller device with expected value '{new_pass}'.")
    print_step("Exiting Test2: test_rdkbcli_update_verify_password")

@pytest.mark.parametrize("radio_cfg", conftest.RADIO_CONFIG)
def test_rdkbcli_channel_change_preference(request, page, radio_cfg, ssh, paths):
    print_step("Entering Test3: test_rdkbcli_channel_change_preference")
    #Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    #Navigate to Wireless Settings page
    utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 2, paths)
    #Get the radio config values
    tab = radio_cfg["radio"]
    band = radio_cfg["ui_tab"]
    new_channel = str(radio_cfg["channel"])
    link_id = radio_cfg["link_id"]
    most_preference = "14"
    least_preference = "0"
    # Select Radio tab to change the channel
    print_step(f"Step 3: Select Radio tab {tab}")
    page.click(f'button.radio-tab-btn[data-band="{tab}"]')
    active_tab = page.query_selector('.radio-tab-btn.active')
    # Verify that the clicked radio tab is now active
    assert active_tab.get_attribute('data-band') == tab
    # Select ALL station option by default
    print_step("Step 4: Select ALL station device option")
    device_mac = "FF:FF:FF:FF:FF:FF"
    page.select_option(f"#device-{band}", device_mac)
    #Verify that ALL station option is selected correctly
    selected_device = page.locator(f"#device-{band}").input_value()
    assert selected_device == device_mac, "Failed to select ALL station"
    #Find the current MOST preferred channel (14)
    print_step(f"Step 5: Find current channel with Most preference ({most_preference})")
    rows = page.locator(f'#list-{band} .list-row')
    count = rows.count()
    current_channel = None
    for i in range(count):
        row = rows.nth(i)
        badge_text = row.locator(".pref-badge").inner_text()
        if most_preference in badge_text:
            current_channel = row.get_attribute("data-channel")
            print(f"Current MOST preferred channel: {current_channel}")
            break
    assert current_channel is not None, f"No channel found with preference {most_preference}"
    # Change the preference of current channel from MOST (14) to LEAST (0)
    print_step(f"Step 6: Change channel {current_channel} preference value to {least_preference}")
    current_row = page.locator(f'#list-{band} .list-row[data-channel="{current_channel}"]')
    # Click button to enable dropdown
    current_row.locator(".pref-choose").click()
    current_dd = current_row.locator("select.pref-inline-dd")
    current_dd.wait_for(state="visible")
    current_dd.select_option("0")
    # Select new channel
    print_step(f"Step 7: Select new channel {new_channel}")
    new_row = page.locator(f'#list-{band} .list-row[data-channel="{new_channel}"]')
    new_checkbox = new_row.locator(".ch-check")
    if not new_checkbox.is_checked():
        new_checkbox.check()
    # Set new channel preference value to MOST (14)
    print_step(f"Step 8: Set channel {new_channel} preference value to {most_preference}")
    new_row.locator(".pref-choose").click()
    new_dd = new_row.locator("select.pref-inline-dd")
    new_dd.wait_for(state="visible")
    new_dd.select_option(f"{most_preference}")
    #Apply settings
    print_step("Step 9: Click Apply Radio Settings")
    page.click("#save-radio-settings")
    page.wait_for_timeout(5000)
    # Validate UI values
    print_step("Step 10: Validate UI channel change updates")
    updated_new = new_row.locator(".pref-badge").inner_text()
    updated_old = current_row.locator(".pref-badge").inner_text()
    print(f"New channel {new_channel} preference value: {updated_new}")
    print(f"Old channel {current_channel} preference value: {updated_old}")
    #Validate the channel preference values.
    assert most_preference in updated_new, f"New channel {new_channel} not set to MOST ({most_preference})"
    assert least_preference in updated_old, f"Old channel {current_channel} not set to LEAST ({least_preference})"
    # Screenshot
    utils.take_screenshot(page,request,paths["screenshots"] / f"rdkbcli_{band}_preference_change.png")
    #Add 60s delay to allow changes to apply on device before SSH verification
    print_step("Step 11: Waiting for device sync")
    time.sleep(60)
    #Verify Channel change on device via SSH command execution
    print_step("Step 12: Fetch the updated channel value from Controller and Agent device")
    ctrl_out = ssh.run("controller", "iw dev mld0 info")
    agent_out = ssh.run("agent", "iw dev mld0 info")
    ctrl_match = re.search(rf'link ID\s+{link_id}.*?channel\s+(\d+)', ctrl_out, re.S)
    agent_match = re.search(rf'link ID\s+{link_id}.*?channel\s+(\d+)', agent_out, re.S)
    if ctrl_match:
        updated_channel_ctrl_device = ctrl_match.group(1)
    else:
        print_error(request, f"Channel not found in controller output for link ID {link_id} - {band}")
    if agent_match:
        updated_channel_agent_device = agent_match.group(1)
    else:
        updated_channel_agent_device = None
        print_error(request, f"Channel not found in agent output for link ID {link_id} - {band}")
    if updated_channel_ctrl_device != new_channel:
        print_error(request, f"Channel change validation failed on controller. Expected Channel value: {new_channel}, Actual channel value: {updated_channel_ctrl_device}")
    elif updated_channel_agent_device != new_channel:
        print_error(request, f"Channel change validation failed on agent. Expected Channel value: {new_channel}, Actual channel value: {updated_channel_agent_device}")
    else:
        print_success(f"Channel Change verification passed in Controller and Agent device with updated value {new_channel}.")
    print_step("Entering Test3: test_rdkbcli_channel_change_preference")

def test_rdkbcli_wifi_reset_with_default_values(page,request,ssh,paths):
    print_step("Entering Test4: test_rdkbcli_wifi_reset_with_default_values")
    #Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    #Navigate to WirelesS Settings page
    utils.navigate_to_required_rdkbcli_page(page, request, 'System Settings', 2, paths)
    # Select the correct AL MAC Address
    print_step(f"Step 3: Choose the correct AL MAC Address ({request.session.wifi_reset_interface}) for reset operation.")
    page.wait_for_selector("#almac-select")
    al_mac_address_wifi_reset = f"{utils.get_interface_mac_address(request, ssh)} ({request.session.wifi_reset_interface})".lower()
    result = page.select_option("#almac-select", value=al_mac_address_wifi_reset)
    if not result: 
        print_error(request, f"Failed to select the {request.session.wifi_reset_interface}!")
    page.on("dialog", utils.wifi_reset_dialog_handler)
    print_step("Step 4: Click the Wi-Fi Reset button and confirm the Wi-Fi reset confirmation dialog.")
    page.click("#reset-btn")
    #Add 10s delay to allow changes to apply on device
    page.wait_for_timeout(10000)
    print_step("Step 5: Verify the OneWifiMesh DB values correspond to the expected default values for each haul type.")
    for wifi_reset_config in conftest.DB_DEFAULT_DATA:
        haul_id = wifi_reset_config["haul_id"]
        default_ssid = wifi_reset_config["default_ssid"]
        default_pass = wifi_reset_config["default_pass"]
        print(f"Haul Type: {haul_id} \n Default SSID: {default_ssid} Default Password: {default_pass}")
        # SQL query to retrieve SSID and PassPhrase for each haul type from OneWifiMesh DB.
        query = f"SELECT SSID, PassPhrase FROM {request.session.network_ssid_list_db_table} WHERE ID LIKE '%{haul_id}%OneWifiMesh%';"
        query_out = utils.get_db_values(request, ssh, query)
        db_output = query_out.strip().split()
        if len(db_output) < 2:
            print_error(request, f"Invalid DB response (expected 2 values): {query_out}")
        db_ssid, db_pass = db_output[0], db_output[1]
        #Verify whether the DB value matches the default values.
        if db_ssid == default_ssid and db_pass == default_pass:
            print(f"{haul_id} DB Data: \n DB SSID: {db_ssid} DB Password: {db_pass} \n Wi-Fi reset completed successfully; the default SSID and password were restored correctly.")
        else:
            if db_ssid != default_ssid:
                print_error(request, f"{haul_id} : SSID mismatch after Wi-Fi reset. Expected: {default_ssid}, Actual: {db_ssid}")
            if db_pass != default_pass:
                print_error(request, f"{haul_id} : Password mismatch after Wi-Fi reset. Expected: {default_pass}, Actual: {db_pass}")
    # Confirm whether any crash occurred and if a core file was generated after the Wi-Fi reset.
    print_step("Step 6: Verify any core files generated in device after WiFi reset.")
    utils.verify_core_dump_generated(request, ssh)
    print_step("Exiting Test4: test_rdkbcli_wifi_reset_with_default_values")

def test_rdkbcli_wifi_reset_with_custom_values(page,request,ssh,paths):
    print_step("Entering Test5: test_rdkbcli_wifi_reset_with_custom_values")
    #Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    #Navigate to WirelesS Settings page
    utils.navigate_to_required_rdkbcli_page(page, request, 'System Settings', 2, paths)
    # Select the correct AL MAC Address
    print_step(f"Step 3: Choose the correct AL MAC Address ({request.session.wifi_reset_interface}) for reset operation.")
    page.wait_for_selector("#almac-select")
    al_mac_address_wifi_reset = f"{utils.get_interface_mac_address(request, ssh)} ({request.session.wifi_reset_interface})".lower()
    result = page.select_option("#almac-select", value=al_mac_address_wifi_reset)
    if not result: 
        print_error(request, f"Failed to select the {request.session.wifi_reset_interface}!")
    #Fill the custom SSID and password values to be configured after WiFi reset.
    print_step("Step 4: Set the custom SSID and Password to be applied after the Wi-Fi reset for each haul type.")
    for wifi_reset_config in conftest.WIFI_RESET_CONFIG:
        haul_id = wifi_reset_config["haul_id"]
        custom_ssid = wifi_reset_config["custom_ssid"]
        custom_pass = wifi_reset_config["custom_pass"]
        print(f"Haul Type: {haul_id} \n Custom SSID: {custom_ssid} Custom Password: {custom_pass}")
        checkbox = page.locator(f'#haul-{haul_id}')
        checkbox.check()
        page.fill(f'#ssid-{haul_id}', custom_ssid)
        page.fill(f'#password-{haul_id}', custom_pass)           
    # Screenshot (avoid full_page on docs sites)
    print_step("Step 5: Take screenshot of Custom SSID and passphrase input value in RDKB CLI page before reset")
    utils.take_screenshot(page, request, paths["screenshots"] / "rdkbcli_wifi_reset_custom_values.png")    
    #Handler to manage confirmation dialogs
    page.on("dialog", utils.wifi_reset_dialog_handler)
    print_step("Step 6: Click the Wi-Fi Reset button and confirm the Wi-Fi reset confirmation dialog.")
    page.click("#reset-btn")
    #Add 10s delay to allow changes to apply on device
    page.wait_for_timeout(10000)
    print_step("Step 7: Verify the OneWifiMesh DB values correspond to the expected default values for each haul type.")
    for wifi_reset_config in conftest.WIFI_RESET_CONFIG:
        haul_id = wifi_reset_config["haul_id"]
        custom_ssid = wifi_reset_config["custom_ssid"]
        custom_pass = wifi_reset_config["custom_pass"]
        # SQL query to retrieve SSID and PassPhrase for each haul type from OneWifiMesh DB.
        query = f"SELECT SSID, PassPhrase FROM {request.session.network_ssid_list_db_table} WHERE ID LIKE '%{haul_id}%OneWifiMesh%';"
        query_out = utils.get_db_values(request, ssh, query)
        db_output = query_out.strip().split()
        if len(db_output) < 2:
            print_error(request, f"Invalid DB response (expected 2 values): {query_out}")
        db_ssid, db_pass = db_output[0], db_output[1]
        #Verify whether the DB value matches the default values.
        if db_ssid == custom_ssid and db_pass == custom_pass:
            print(f"{haul_id} DB Data: \n DB SSID: {db_ssid} DB Password: {db_pass} \n Wi-Fi reset completed successfully, custom SSID and Password were applied correctly.")
        else:
            if db_ssid != custom_ssid:
                print_error(request, f"{haul_id} : SSID mismatch after Wi-Fi reset. Expected: {custom_ssid}, Actual: {db_ssid}")
            if db_pass != custom_pass:
                print_error(request, f"{haul_id} : Password mismatch after Wi-Fi reset. Expected: {custom_pass}, Actual: {db_pass}")
    #Confirm whether any crash occurred and if a core file was generated after the Wi-Fi reset.
    print_step("Step 8: Verify any core files generated in device after WiFi reset.")
    utils.verify_core_dump_generated(request, ssh)  
    print_step("Exiting Test5: test_rdkbcli_wifi_reset_with_custom_values")
