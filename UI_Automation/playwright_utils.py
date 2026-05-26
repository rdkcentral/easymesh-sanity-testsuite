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