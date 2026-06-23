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
import playwright_utils
from utils import print_step, print_error, print_success
import conftest
import pytest

# Documentation: [test_em_functionality.py](Sanity_Tests_Documentation.md#test_em_functionalitypy)

# Documentation: [TC-EM-01](Sanity_Tests_Documentation.md#tc-em-01-test_rdkbcli_update_verify_ssid)
def test_rdkbcli_update_verify_ssid(config, page, request, ssh, paths):
    print_step("Entering Test1: test_rdkbcli_update_verify_ssid")
    new_ssid = "TDKB_New_SSID_02"
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 1, "ssid", new_ssid, 'Fronthaul', 5000)
    if not utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 6):
        pytest.fail(f"SSID update did not propagate to all devices. Expected: {new_ssid}")
    #revert the SSID back to default value
    print_step("Step 8: Revert the SSID value back to default in RDKB CLI and verify the update on devices")
    default_ssid = config["database"]["network_ssid_map"]["Fronthaul"]["default_ssid"]
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 9, "ssid", default_ssid, 'Fronthaul', 5000)
    if not utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, default_ssid, 14):
        pytest.fail(f"SSID update did not propagate to all devices. Expected: {default_ssid}")
    print_step("Exiting Test1: test_rdkbcli_update_verify_ssid")

# Documentation: [TC-EM-02](Sanity_Tests_Documentation.md#tc-em-02-test_rdkbcli_update_verify_password)
def test_rdkbcli_update_verify_password(config, page, request, ssh, paths):
    print_step("Entering Test2: test_rdkbcli_update_verify_password")
    new_pass = "TestTDKB@12345"
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 1, "passphrase", new_pass, 'Fronthaul', 15000)
    if not utils.verify_password_update_in_controller_db(config, request, ssh, new_pass, 6):
        pytest.fail(f"Passphrase update verification failed on controller DB. Expected: {new_pass}")
    #revert the Passphrase back to default value
    print_step("Step 8: Revert the Passphrase value back to default in RDKB CLI and verify the update on device")
    default_pass = config["database"]["network_ssid_map"]["Fronthaul"]["default_pass"]
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 9, "passphrase", default_pass, 'Fronthaul', 15000)
    if not utils.verify_password_update_in_controller_db(config, request, ssh, default_pass, 14):
        pytest.fail("Passphrase update verification failed on controller DB. Expected: {default_pass}")
    print_step("Exiting Test2: test_rdkbcli_update_verify_password")

# Documentation: [TC-EM-03](Sanity_Tests_Documentation.md#tc-em-03-test_rdkbcli_channel_change_preference-skipped-in-current-suite)
@pytest.mark.skip(reason="Need clarification from dev on operating class changing intermittently. Issue is tracked as part of ticket RDKBWIFI-424")
@pytest.mark.parametrize("radio_cfg", conftest.RADIO_CONFIG)
def test_rdkbcli_channel_change_preference(config, request, page, radio_cfg, ssh, paths):
    print_step("Entering Test3: test_rdkbcli_channel_change_preference")
    #Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 1)
    #Navigate to Wireless Settings page
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', 2, paths)
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
    if active_tab and active_tab.get_attribute('data-band') == tab:
        print_success(f"Radio tab {tab} selected successfully")
    else:
        print_error(request, f"Failed to select radio tab {tab}")
        assert False
    # Select ALL station option by default
    print_step("Step 4: Select ALL station device option")
    device_mac = "FF:FF:FF:FF:FF:FF"
    page.select_option(f"#device-{band}", device_mac)
    #Verify that ALL station option is selected correctly
    selected_device = page.locator(f"#device-{band}").input_value()
    if selected_device == device_mac:
        print_success("ALL station device selected successfully")
    else:
        print_error(request, "Failed to select ALL station device")
        assert False
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
            break
    if current_channel:
        print_success(f"Found MOST preferred channel: {current_channel}")
    else:
        print_error(request, f"No channel found with preference {most_preference}")
        assert False
    # Change the preference of current channel from MOST (14) to LEAST (0)
    print_step(f"Step 6: Change channel {current_channel} preference value to {least_preference}")
    current_row = page.locator(f'#list-{band} .list-row[data-channel="{current_channel}"]')
    # Click button to enable dropdown
    current_row.locator(".pref-choose").click()
    current_dd = current_row.locator("select.pref-inline-dd")
    current_dd.wait_for(state="visible")
    current_dd.select_option("0")
    print_success(f"Channel {current_channel} preference changed to {least_preference}")
    # Select new channel
    print_step(f"Step 7: Select new channel {new_channel}")
    new_row = page.locator(f'#list-{band} .list-row[data-channel="{new_channel}"]')
    new_checkbox = new_row.locator(".ch-check")
    if not new_checkbox.is_checked():
        new_checkbox.check()
    if new_checkbox.is_checked():
        print_success(f"Channel {new_channel} selected successfully")
    else:
        print_error(request, f"Failed to select channel {new_channel}")
        assert False
    # Set new channel preference value to MOST (14)
    print_step(f"Step 8: Set channel {new_channel} preference value to {most_preference}")
    new_row.locator(".pref-choose").click()
    new_dd = new_row.locator("select.pref-inline-dd")
    new_dd.wait_for(state="visible")
    new_dd.select_option(f"{most_preference}")
    print_success(f"Channel {new_channel} preference set to {most_preference}")
    #Apply settings
    print_step("Step 9: Click Apply Radio Settings")
    page.click("#save-radio-settings")
    page.wait_for_timeout(5000)
    print_success("Radio settings applied successfully")
    # Validate UI values
    print_step("Step 10: Validate UI channel change updates")
    updated_new = new_row.locator(".pref-badge").inner_text()
    updated_old = current_row.locator(".pref-badge").inner_text()
    print(f"New channel {new_channel} preference value: {updated_new}")
    print(f"Old channel {current_channel} preference value: {updated_old}")
    #Validate the channel preference values.
    if most_preference in updated_new and least_preference in updated_old:
        print_success("UI validation passed for channel preference updates")
    else:
        print_error(request, "UI validation failed for channel preference updates")
        assert False
    # Screenshot
    playwright_utils.take_screenshot(page,request,paths["screenshots"] / f"rdkbcli_{band}_preference_change.png")
    #Add 60s delay to allow changes to apply on device before SSH verification
    print_step("Step 11: Waiting for device sync")
    time.sleep(60)
    print("Device sync completed")
    #Verify Channel change on device via SSH command execution
    print_step("Step 12: Fetch the updated channel value from Controller device")
    ctrl_out = utils.run_command_fetch_output_from_device("iw dev mld0 info", "controller", ssh)
    ctrl_match = re.search(rf'link ID\s+{link_id}.*?channel\s+(\d+)', ctrl_out, re.S)
    if ctrl_match:
        updated_channel_ctrl_device = ctrl_match.group(1)
    if not agent_match:
        print_error(request, f"Channel not found in agent output for link ID {link_id}")
        assert False
    else:
        print_error(request, f"Channel not found in controller output for link ID {link_id}")
    if updated_channel_ctrl_device != new_channel:
        print_error(request, f"Channel change validation failed on controller. Expected Channel value: {new_channel}, Actual channel value: {updated_channel_ctrl_device}")
    else:
        print_success(f"Channel Change verification passed in Controller device with updated value {new_channel}.")
    print_step("Step 13: Fetch the updated channel value from Agent devices")
    for extender in ssh.enabled_extenders:
        print_step(f"Fetching updated channel value from Agent device: {extender}")
        agent_out = utils.run_command_fetch_output_from_device("iw dev mld0 info", extender, ssh)
        agent_match = re.search(rf'link ID\s+{link_id}.*?channel\s+(\d+)', agent_out, re.S)
        if agent_match:
            updated_channel_agent_device = agent_match.group(1)
        else:
            updated_channel_agent_device = None
            print_error(request, f"Channel not found in agent output for link ID {link_id} - {band}")    
    
        if updated_channel_agent_device != new_channel:
            print_error(request, f"Channel change validation failed on agent. Expected Channel value: {new_channel}, Actual channel value: {updated_channel_agent_device}")
        else:
            print_success(f"Channel Change verification passed in Agent device with updated value {new_channel}.")
    print_step("Exiting Test3: test_rdkbcli_channel_change_preference")

# Documentation: [TC-EM-04](Sanity_Tests_Documentation.md#tc-em-04-test_rdkbcli_wifi_reset_with_default_values)
def test_rdkbcli_wifi_reset_with_default_values(config, page, request, ssh, paths):
    print_step("Entering Test4: test_rdkbcli_wifi_reset_with_default_values")
    # Set Wi-Fi SSID and Passphrase to non-default values before performing Wi-Fi reset with default values to validate the reset functionality.
    new_ssid = "TDKB_New_SSID_03"
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 1, "ssid", new_ssid, 'Fronthaul', 5000)
    if not utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 6):
        pytest.fail(f"SSID update did not propagate to all devices. Expected: {new_ssid}")
    new_pass = "TestTDKB@1234"
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 8, "passphrase", new_pass, 'Fronthaul', 15000)
    if not utils.verify_password_update_in_controller_db(config, request, ssh, new_pass, 13):
        pytest.fail(f"Passphrase update verification failed on controller DB. Expected: {new_pass}")
    # Wait for a few seconds to ensure the changes are applied before proceeding with Wi-Fi reset.
    time.sleep(20)
    # Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 15)
    # Navigate to System Settings page
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, "System Settings", 16, paths)
    # Retrieve the Wi-Fi reset interface mac address from controller.
    iface_name = config["system"]["wifi_reset_interface"]
    print_step(f"Step 17: Retrieve the {iface_name} interface MAC from the controller.")
    al_mac_address = utils.get_interface_mac_address("controller", iface_name, ssh)
    if al_mac_address:
        print_success("AL MAC address retrieved successfully from controller device.")
    else:
        pytest.fail("Failed to retrieve AL MAC address from controller device.")
    # Select the Wi-Fi reset interface from dropdown in UI.
    playwright_utils.select_wifi_reset_al_mac(al_mac_address, iface_name, page, request, ssh, step=18)
    # Confirm the pop-up to trigger the Wi-Fi reset.
    playwright_utils.perform_wifi_reset(page, step=19)
    # Reboot the device after Wi-Fi reset and wait for the device to come back.
    utils.reboot_device_after_wifi_reset(ssh, request, step=20)
    # Verify that the OneWifiMesh DB values match the expected default values.
    utils.verify_wifi_db_values(config, ssh, request, expected_type="default",step=21)
    # Verify SSID values for each interface using iw dev against the expected default values.
    utils.verify_iw_dev_interface_value(config, ssh, request, expected_type="default", step=22)
    # Confirm whether any crash occurred and if a core file was generated after the Wi-Fi reset.
    print_step("Step 23: Verify any core files generated in the devices after WiFi reset.")
    utils.verify_core_dump_generated(request, ssh)
    print_step("Exiting Test4: test_rdkbcli_wifi_reset_with_default_values")

# Documentation: [TC-EM-05](Sanity_Tests_Documentation.md#tc-em-05-test_rdkbcli_wifi_reset_with_custom_values)
def test_rdkbcli_wifi_reset_with_custom_values(config, page, request, ssh, paths):
    print_step("Entering Test5: test_rdkbcli_wifi_reset_with_custom_values")
    # Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 1)
    # Navigate to System Settings page
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, "System Settings", 2, paths)
    # Retrieve the Wi-Fi reset interface mac address from controller.
    iface_name = config["system"]["wifi_reset_interface"]
    print_step(f"Step 3: Retrieve the {iface_name} interface MAC from the controller.")
    al_mac_address = utils.get_interface_mac_address("controller", iface_name, ssh)
    if al_mac_address:
        print_success("AL MAC address retrieved successfully from controller device.")
    else:
        pytest.fail("Failed to retrieve AL MAC address from controller device.")
    # Select the Wi-Fi reset interface from dropdown in UI.
    playwright_utils.select_wifi_reset_al_mac(al_mac_address, iface_name, page, request, ssh, step=4)
    # Configure the custom Wi-Fi ssid/password values.
    playwright_utils.configure_custom_wifi_values(page, config, step=5)
    # Take screenshot after filling the custom values.
    print_step("Step 6: Take screenshot of Custom SSID and passphrase input value in RDKB CLI page before reset")
    playwright_utils.take_screenshot(page, request, paths["screenshots"] / "rdkbcli_wifi_reset_custom_values.png")
    # Confirm the pop-up to trigger the Wi-Fi reset.
    playwright_utils.perform_wifi_reset(page, step=7)
    # Reboot the device after Wi-Fi reset and wait for the device to come back.
    utils.reboot_device_after_wifi_reset(ssh, request, step=8)
    # Verify that the OneWifiMesh DB values match the expected custom values.
    utils.verify_wifi_db_values(config, ssh, request, expected_type="custom", step=9)
    # Verify SSID values for each interface using iw dev against the expected custom values.
    utils.verify_iw_dev_interface_value(config, ssh, request, expected_type="custom", step=10)
    # Confirm whether any crash occurred and if a core file was generated after the Wi-Fi reset.
    print_step("Step 11: Verify any core files generated in the devices after WiFi reset.")
    utils.verify_core_dump_generated(request, ssh)
    print_step("Exiting Test5: test_rdkbcli_wifi_reset_with_custom_values")
