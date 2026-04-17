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
import time
import utils
from utils import print_step, print_error, print_success
import conftest
import pytest

def test_rdkbcli_update_verify_ssid(page, request, ssh, paths):
    print_step("Entering Test1: test_rdkbcli_update_verify_ssid")
    new_ssid = "TDKB_New_SSID_02"
    results = utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 1, paths)
    # Final validation to check if SSID updates are consistent on both controller and agent devices 
    print_step("Step 9: Validate if updated SSID is consistent on both controller and agent devices and matches the expected value")
    if results[0] != new_ssid:
        print_error(request, f"SSID update validation failed on controller device. Expected: {new_ssid}, Actual: {results[0]}")
    if results[1] != new_ssid:
        print_error(request, f"SSID update validation failed on agent device. Expected: {new_ssid}, Actual: {results[1]}")
    if results[0] != new_ssid or results[1] != new_ssid:
        print_error(request, f"SSID update is NOT consistent with controller and agent devices. Expected SSID: {new_ssid}, Actual SSID on controller: {results[0]}, Actual SSID on agent: {results[1]}")
    else:
        print_success(f"SSID update is consistent with controller and agent devices. Expected SSID: {new_ssid}, Actual SSID on controller: {results[0]}, Actual SSID on agent: {results[1]}")
    print_success(f"SSID update verification passed on both controller and agent devices with updated value {new_ssid}.")
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

@pytest.mark.skip(reason="Disabled due to unstable select device dropdown and operating class values")
@pytest.mark.parametrize("radio_cfg", conftest.RADIO_CONFIG)
def test_rdkbcli_verify_channel_change(request, page, radio_cfg, ssh, paths):
    print_step("Entering Test3: test_rdkbcli_verify_channel_change")
    #Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    #Navigate to Wireless Settings page
    utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 2, paths)
    page.wait_for_timeout(5000)
    #Get the radio config values
    link_id = radio_cfg["link_id"]
    band = radio_cfg["ui_tab"]
    channel = radio_cfg["channel"]
    tab1 = radio_cfg["radio"]
    print_step(f"Step 3: Select the Radio {tab1} tab to change the channel")
    page.click(f'button.radio-tab-btn[data-band="{tab1}"]')
    # Verify that the clicked radio tab is now active
    active_tab = page.query_selector('.radio-tab-btn.active')
    assert active_tab.get_attribute('data-band') == tab1
    print_step(f"Step 4: Select the channel value to change (channel: {channel})")
    page.select_option(f'#channel-{band}-manual', channel)
    page.wait_for_timeout(5000)  # wait for the router to apply
    print_step("Step 5: Click 'Apply Radio Settings' button to update channel change")
    page.click("#save-radio-settings")
    # Screenshot (avoid full_page on docs sites)
    print_step("Step 6: Take screenshot of updated Channel value in RDKB CLI page after update")
    utils.take_screenshot(page, request, paths["screenshots"] / f"rdkbcli_{band}_channel_change.png")
    #Print updated channel value from RDKB-CLI page for verification
    print_step("Step 7: Fetch Changed channel value from RDKB CLI page for verification")
    updated_channel = page.locator(f"#channel-{band}-manual").input_value()
    print(f"Updated Channel value from RDKBCLI page for {band}:", updated_channel)
    if updated_channel != channel:
        print_error(request, f"Channel change validation failed on RDKB CLI. Expected Channel value: {channel}, Actual channel value: {updated_channel}")
    else:
        print_success("Channel Change validation passed on RDKB CLI with expected value.")
    #Add 30s delay to allow changes to apply on device before SSH verification
    time.sleep(30)
    #Verify Channel change on device via SSH command execution
    print_step("Step 8: Fetch the updated channel value from Controller and Agent device")
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
    if updated_channel_ctrl_device != channel:
        print_error(request, f"Channel change validation failed on controller. Expected Channel value: {channel}, Actual channel value: {updated_channel_ctrl_device}")
    elif updated_channel_agent_device != channel:
        print_error(request, f"Channel change validation failed on agent. Expected Channel value: {channel}, Actual channel value: {updated_channel_agent_device}")
    else:
        print_success(f"Channel Change verification passed in Controller and Agent device with updated value {channel}.")
    print_step("Exiting Test3: test_rdkbcli_verify_channel_change")

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
        db_ssid, db_pass = query_out.strip().split("\t")
        #Verify whether the DB value matches the default values.
        if db_ssid == default_ssid and db_pass == default_pass:
            print(f"{haul_id} : Wi-Fi reset completed successfully; the default SSID and password were restored correctly.")
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
        db_ssid, db_pass = query_out.strip().split("\t")
        #Verify whether the DB value matches the default values.
        if db_ssid == custom_ssid and db_pass == custom_pass:
            print(f"{haul_id} : Wi-Fi reset completed successfully, custom SSID and Password were applied correctly.")
        else:
            if db_ssid != custom_ssid:
                print_error(request, f"{haul_id} : SSID mismatch after Wi-Fi reset. Expected: {custom_ssid}, Actual: {db_ssid}")
            if db_pass != custom_pass:
                print_error(request, f"{haul_id} : Password mismatch after Wi-Fi reset. Expected: {custom_pass}, Actual: {db_pass}")
    #Confirm whether any crash occurred and if a core file was generated after the Wi-Fi reset.
    print_step("Step 8: Verify any core files generated in device after WiFi reset.")
    utils.verify_core_dump_generated(request, ssh)  
    print_step("Exiting Test5: test_rdkbcli_wifi_reset_with_custom_values")
