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

from playwright.sync_api import expect, sync_playwright, TimeoutError as PlaywrightTimeoutError
import pytest
from UI_Automation.utils import *

def update_verify_required_field_from_rdkbcli(config, page, request, paths, step, field_name, new_value, profile_name, timeout_value):
    # Navigate to RDKB CLI page
    navigate_to_rdkbcli_page(config, page, step)
    # Navigate to Wireless Settings page
    navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', step+1, paths)
    # Update required field value in input field and save changes
    update_input_save_changes(page, request, f"#profile-{field_name.lower()}", new_value, step+2, paths, profile_name)
    print(f"{field_name} updated triggered from RDKB CLI successfully. Waiting for changes to apply in UI.")
    # Short wait for UI update
    page.wait_for_timeout(timeout_value)
    # Screenshot
    print_step(f"Step {step+3}: Take screenshot of updated {field_name} value in RDKB CLI page after update")
    take_screenshot(page, request, paths["screenshots"] / f"rdkbcli_updated_{field_name.lower()}.png")
    # Verify updated SSID in UI
    fetch_and_verify_home_network_input(page, request, field_name, f"#profile-{field_name.lower()}", new_value, step+4, paths, profile_name)

def navigate_to_rdkbcli_page(config, page, step):
    try:
        ctrl_ip = config["controller"]["ip"]
        print_step(f"Step {step}: Navigate to RDKB CLI page at http://{ctrl_ip}:8888/")
        page.goto(f"http://{ctrl_ip}:8888/", wait_until="domcontentloaded")
        expect(page).to_have_title("EasyMesh R6 Pro Controller")
        print_success("RDKB CLI page launched successfully and title verified.")
    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout while launching RDKB CLI page: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error while navigating to RDKB CLI page: {e}")

def navigate_to_required_rdkbcli_page(page, request, page_name, step, paths):
    try:
        print_step(f"Step {step}: Navigate to '{page_name}' from sidebar")
        page.locator(f"a:has-text('{page_name}')").first.click()
        expect(page.locator(f"h1:has-text('{page_name}')")).to_be_visible(timeout=15000)
        print_success(f"Successfully navigated to {page_name}")
    except PlaywrightTimeoutError:
        take_screenshot(page, request, paths["screenshots"] / f"{page_name}_navigation_failure.png")
        pytest.fail(f"Timeout while navigating to '{page_name}' page")
    except Exception as e:
        take_screenshot(page, request, paths["screenshots"] / f"{page_name}_navigation_error.png")
        pytest.fail(f"Error navigating to '{page_name}': {e}")

def take_screenshot(page, request, filename):
    try:
        if page.is_closed():
            print_error(request, "Page already closed. Cannot capture screenshot.")
            return
        page.screenshot(path=filename, full_page=True)
        print_success(f"Screenshot saved as {filename}")
    except Exception as e:
        print_error(request, f"Failed to capture screenshot: {e}")

def update_input_save_changes(page, request, id_field, id_value, step, paths, profile_name):
    try:
        print_step(f"Step {step} : Click '{profile_name}' Edit button and update SSID")
        page.locator(f"button[onclick*=\"editProfile('{profile_name}')\"]").click()
        page.fill(id_field, id_value)
        page.click("button[type='submit']")
        page.wait_for_selector("#save-profile-settings:not([disabled])")
        page.click("#save-profile-settings")
        print_success("Profile settings updated successfully")
    except PlaywrightTimeoutError:
        take_screenshot(page, request, paths["screenshots"] / "update_profile_timeout.png")
        pytest.fail("Timeout occurred while updating profile settings")
    except Exception as e:
        take_screenshot(page, request, paths["screenshots"] / "update_profile_error.png")
        pytest.fail(f"Failed to update profile settings: {e}")

def fetch_and_verify_home_network_input(page, request, field_name, locator_id, expected_value, step, paths, profile_name):
    try:
        print_step(f"Step {step}: Fetch updated {field_name} value from RDKB CLI page for verification")
        actual_value = page.locator(locator_id).input_value()
        print(f"{profile_name} {field_name} from RDKBCLI page:", actual_value)
        if actual_value != expected_value:
            pytest.fail(
                f"{field_name} update validation failed on RDKB CLI. "
                f"Expected: {expected_value}, Actual: {actual_value}"
            )
        else:
            print_success(f"{field_name} update validation passed with expected value: {expected_value}")
    except PlaywrightTimeoutError:
        take_screenshot(page, request, paths["screenshots"] / f"{field_name}_fetch_timeout.png")
        pytest.fail(f"Timeout while fetching {field_name} value")
    except Exception as e:
        take_screenshot(page, request, paths["screenshots"] / f"{field_name}_fetch_error.png")
        pytest.fail(f"Error while verifying {field_name}: {e}")

def select_wifi_reset_al_mac(al_mac_address, iface_name, page, request, ssh, step):
    # Select the correct AL MAC Address
    print_step(f"Step {step}: Choose the correct AL MAC Address ({iface_name}) for reset operation from RDKB-CLI.")
    page.wait_for_selector("#almac-select")
    al_mac_address_wifi_reset = f"{al_mac_address} ({iface_name})"
    result = page.select_option("#almac-select", value=al_mac_address_wifi_reset)
    if not result:
        pytest.fail(f"Failed to select the {iface_name}!")
    print_success(f"{iface_name} selected successfully for Wi-Fi reset operation.")

def configure_custom_wifi_values(page, config, step):
    # Fill the custom SSID and password values to be configured after WiFi reset.
    print_step(f"Step {step}: Set the custom SSID and Password to be applied after the Wi-Fi reset for each haul type.")
    ssid_map = config["database"]["network_ssid_map"]
    for haul_id, cfg in ssid_map.items():
        custom_ssid = cfg["custom_ssid"]
        custom_pass = cfg["custom_pass"]
        print(f"Haul Type: {haul_id} \n Custom SSID: {custom_ssid} Custom Password: {custom_pass}")
        checkbox = page.locator(f"#haul-{haul_id}")
        checkbox.check()
        page.fill(f"#ssid-{haul_id}", custom_ssid)
        page.fill(f"#password-{haul_id}", custom_pass)
    print_success("Custom values were successfully filled on the RDKBCLI Wi-Fi Reset page")

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

def perform_wifi_reset(page, step):
    # Handler to manage confirmation dialogs
    page.on("dialog", wifi_reset_dialog_handler)
    print_step(f"Step {step}: Click the Wi-Fi Reset button and confirm the Wi-Fi reset confirmation dialog.")
    page.click("#reset-btn")
    # Add 10s delay to allow changes to apply on device
    page.wait_for_timeout(10000)
