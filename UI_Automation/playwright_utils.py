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

def verify_ssid_update_in_controller_and_agent(config, page, request, ssh, new_ssid, step, paths):
    # Navigate to RDKB CLI page
    navigate_to_rdkbcli_page(config, page, step)
    # Navigate to Wireless Settings page
    navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', step+1, paths)
    # Update SSID value in input field and save changes
    update_input_save_changes(page, request, "#profile-ssid", new_ssid, step+2, paths)
    print("SSID updated triggered from RDKB CLI successfully. Waiting for changes to apply in UI.")
    # Short wait for UI update
    page.wait_for_timeout(5000)
    # Screenshot
    print_step(f"Step {step+3}: Take screenshot of updated SSID value in RDKB CLI page after update")
    take_screenshot(page, request, paths["screenshots"] / "updated_ssid.png")
    # Verify updated SSID in UI
    fetch_and_verify_home_network_input(page, request, "SSID", "#profile-ssid", new_ssid, step+4, paths)
    # Retry ssid update check logic after wait time
    max_retries = 6
    retry_interval = 10000  # 10 sec
    print_step(f"Step {step+5}: Initial wait before device ssid verification")
    page.wait_for_timeout(20000)
    print_step(f"Step {step+6}: Verify SSID update on both controller and agent.")
    for attempt in range(max_retries + 1):
        print(f"SSID verification attempt : {attempt + 1}")
        results = {}
        for device in ssh.device_list:
            out = ssh.run(device, "iw dev mld0 info | awk '/ssid/ {print $2}'")
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

def verify_password_update_in_controller_and_agent(config, page, request, ssh, new_pass, step, paths):
    #Navigate to Rdkbcli page
    navigate_to_rdkbcli_page(config, page, step)
    #Navigate to Wireless Settings page
    navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings', step+1, paths)
    #Update SSID value in input field and save changes
    update_input_save_changes(page, request, "#profile-passphrase", new_pass, step+2, paths)
    print_success("Password updated triggered from RDKB CLI successfully. Waiting for changes to reflect in RDKBCLI.")
    page.wait_for_timeout(15000)
    # Screenshot (avoid full_page on docs sites)
    print_step(f"Step {step+3}: Take screenshot of updated Password value in RDKB CLI page after update")
    take_screenshot(page, request, paths["screenshots"] / "rdkbcli_updated_password.png")        
    #Print updated password value from input fields for verification
    fetch_and_verify_home_network_input(page, request, "Passphrase", "#profile-passphrase", new_pass, step+4, paths)
    #Add 30s delay to allow changes to apply on device before SSH verification
    time.sleep(30)
    #Verify Password update on device via SSH command execution
    print_step(f"Step {step+5}: Fetch updated Password from controller device")
    query_out = get_db_values(config, ssh, f"SELECT SSID, PassPhrase FROM {config['database']['ssid_table']} WHERE ID='Fronthaul@OneWifiMesh';")
    if not query_out or not query_out.strip():
        print_error(request, "DB query returned empty output. Unable to fetch password.")
    else:
        fronthaul_password = query_out.strip().split("\t")[1]
        print_success(f"Updated Password from controller device: {fronthaul_password}")
        #Final validation to check if Password updates are consistent on controller device and match the expected value from test data. If there is a mismatch, print appropriate error message and fail the test.
        print_step(f"Step {step+6}: Validate if updated Password is consistent on controller device and matches the expected value")
        if len(fronthaul_password.strip()) != 0 and fronthaul_password.strip() != new_pass:
            print_error(request, f"Password update validation failed on controller device. Expected: {new_pass}, Actual: {fronthaul_password.strip()}")        
        else:
            print_success(f"Password update verification passed on controller device with expected value '{new_pass}'.")

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

def update_input_save_changes(page, request, id_field, id_value, step, paths):
    try:
        print_step(f"Step {step} : Click 'Home Network' Edit button and update SSID")
        page.locator("button[onclick*=\"editProfile('Fronthaul')\"]").click()
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

def fetch_and_verify_home_network_input(page, request, field_name, locator_id, expected_value, step, paths):
    try:
        print_step(f"Step {step}: Fetch updated {field_name} value from RDKB CLI page for verification")
        actual_value = page.locator(locator_id).input_value()
        print(f"Fronthaul {field_name} from RDKBCLI page:", actual_value)
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