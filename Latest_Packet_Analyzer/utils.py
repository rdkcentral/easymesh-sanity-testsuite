import re
import time
from urllib import request

from pytest_check import check
import conftest
import paramiko
from playwright.sync_api import expect, sync_playwright, TimeoutError as PlaywrightTimeoutError
import pytest
import json
from ieee1905_utils import print_step, print_success, print_error

def verify_service_status(service_name, device, output):
    print(f"{service_name} service status command output from {device}: {output}")
    if "active (running)" not in output:
        pytest.fail(f"{service_name} service is NOT running on {device}:\n{output}")
    else:
        print(f"Pass: {service_name} service is running as expected on {device} device")

def verify_ssid_update_in_controller_and_agent(page, request, ssh):
    results = []
    #Navigate to Rdkbcli page
    navigate_to_rdkbcli_page(page, request)
    #Navigate to Wireles Settings page
    navigate_to_required_rdkbcli_page(page, request, 'Wireless Settings')
    #Update SSID value in input field and save changes
    update_input_save_changes(page, "#profile-ssid", request.session.ssid)
    print_success("SSID updated in RDKB CLI successfully. Waiting for changes to apply on device...")
    #page.wait_for_timeout(15000)
    page.wait_for_timeout(5000)
    # Screenshot (avoid full_page on docs sites)
    print_step("\nStep 5: Take screenshot of updated SSID value in RDKB CLI page after update")
    take_screenshot(page, rf"{conftest.screenshots_path}/updated_ssid.png")
    #Add 15s delay to allow changes to apply on device before SSH verification
    page.wait_for_timeout(15000)
    for step, device in enumerate(["controller", "agent"], start=6):
        #Verify SSID update on device via SSH command execution
        print_step(f"\nStep {step}: Fetch updated SSID from {device} device")
        out = ssh.run(device, "iw dev mld0 info|grep ssid|cut -d' ' -f2")
        #if out == "":
        #    out = "private_ssid"
        print_success(f"Fetched updated SSID from {device} device: {out.strip()}")
        results.append(out.strip())
    #Verify updated SSID value from input field on RDKB CLI page to ensure it reflects the expected updated value
    rdkbcli_ssid, ret = fetch_and_verify_home_network_input(page, "SSID", "#profile-ssid", request.session.ssid)
    check.equal(True, ret, f"\nFail: SSID updation failed on RDKB CLI. Expected value: {request.session.ssid} Actual value: {rdkbcli_ssid}")
    print_step("\nStep 9: Validate if updated SSID is consistent on RDKB CLI page and the controller/agent devices")
    #check.equal((ret == True and results[0] == request.session.ssid and results[1] == request.session.ssid), True, "\nFail: SSID update is NOT consistent across RDKB CLI page and controller/agent devices")
    if ret == True and results[0] == request.session.ssid and results[1] == request.session.ssid:
        print_success(f"SSID update is consistent on RDKB CLI page and the controller/agent devices. SSID from RDKB CLI: {rdkbcli_ssid}, SSID on controller: {results[0]}, SSID on agent: {results[1]}")
    else:
        print_error(f"SSID update is NOT consistent across RDKB CLI page and controller/agent devices. SSID from RDKB CLI: {rdkbcli_ssid}, SSID on controller: {results[0]}, SSID on agent: {results[1]}")
        check.is_true(False, f"\nSSID update is NOT consistent across RDKB CLI page and controller/agent devices. SSID from RDKB CLI: {rdkbcli_ssid}, SSID on controller: {results[0]}, SSID on agent: {results[1]}")
    return results

def get_client_ip_interface_status(ssh, commands):
    outputs = []
    for command in commands:
        output = ssh.run("client", command)
        outputs.append(output.strip())
    ip, interface, active_status = outputs[0], outputs[1], outputs[2]
    return ip, interface, active_status

def navigate_to_rdkbcli_page(page, request):
    try:
        print_step(f"\nStep 2: Navigate to RDKB CLI page at http://{request.session.host}:8888/")
        page.goto(f"http://{request.session.host}:8888/", wait_until="domcontentloaded")
        expect(page).to_have_title("EasyMesh R6 Pro Controller")
        print_success("RDKB CLI page launched successfully and title verified.")
    except PlaywrightTimeoutError as e:
        print_error(f"Timeout while launching RDKB CLI page: {e}")
    except Exception as e:
        print_error(f"Unexpected error while navigating to RDKB CLI page: {e}")

def navigate_to_required_rdkbcli_page(page, request, page_name):
    try:
        print_step(f"\nStep 3: Navigate to '{page_name}' from sidebar")
        page.locator(f"a:has-text('{page_name}')").first.click()
        expect(page.locator(f"h1:has-text('{page_name}')")).to_be_visible(timeout=15000)
        print_success(f"Successfully navigated to {page_name}")
    except PlaywrightTimeoutError:
        take_screenshot(page, f"{page_name}_navigation_failure.png")
        print_error(f"Timeout while navigating to '{page_name}' page")
        #pytest.fail(f"Timeout while navigating to '{page_name}' page")
    except Exception as e:
        take_screenshot(page, f"{page_name}_navigation_error.png")
        print_error(f"Error navigating to '{page_name}': {e}")
        #pytest.fail(f"Error navigating to '{page_name}': {e}")

def take_screenshot(page, filename):
    try:
        if page.is_closed():
            print("Page already closed. Cannot capture screenshot.")
            return
        page.screenshot(path=filename, full_page=True)
        print_success(f"Screenshot saved as {filename}")
    except Exception as e:
        print_error(f"Failed to capture screenshot: {e}")


def update_input_save_changes(page, id_field, id_value):
    try:
        print_step("\nStep 4: Click 'Home Network' Edit button, update SSID and save profile settings")
        page.locator("button[onclick*=\"editProfile('Fronthaul')\"]").click()
        page.fill(id_field, id_value)
        page.click("button[type='submit']")
        page.wait_for_selector("#save-profile-settings:not([disabled])")
        page.click("#save-profile-settings")
        print("Profile settings updated successfully")
    except PlaywrightTimeoutError:
        take_screenshot(page, "update_profile_timeout.png")
        print_error("Timeout occurred while updating profile settings")
    except Exception as e:
        take_screenshot(page, "update_profile_error.png")
        print_error(f"Failed to update profile settings: {e}")

def fetch_and_verify_home_network_input(page, field_name, locator_id, expected_value):
    try:
        print_step(f"\nStep 8: Fetch updated {field_name} value from RDKB CLI page")
        actual_value = page.locator(locator_id).input_value()
        print(f"Fronthaul {field_name} from RDKBCLI page:", actual_value)
        if actual_value != expected_value:
            check.is_true(False, f"\n{field_name} updation failed on RDKB CLI")
            print_error(f"{field_name} updation failed on RDKB CLI. " f"Expected: {expected_value}, Actual: {actual_value}")
            return False
        print_success(f"{field_name} updation passed with expected value: {expected_value}")
        return actual_value, True
    except PlaywrightTimeoutError:
        take_screenshot(page, f"{field_name}_fetch_timeout.png")
        print_error(f"Timeout while fetching {field_name} value")
    except Exception as e:
        take_screenshot(page, f"{field_name}_fetch_error.png")
        print_error(f"Error while verifying {field_name}: {e}")
    return actual_value, False

def get_interface_mac_address(request, ssh):
    # Run ifconfig remotely via SSH
    interface_name = request.session.wifi_reset_interface
    output = ssh.run("controller", f"ifconfig {interface_name}")
    # Parse MAC address
    mac_match = re.search(r"(?:HWaddr|ether)\s+([0-9a-fA-F:]{17})", output, re.IGNORECASE)
    if not mac_match:
        pytest.fail(f"MAC address not found for {interface_name}")
    mac_address = mac_match.group(1)
    print(f"MAC address of {interface_name} on {request.session.host}: {mac_address}")
    return mac_address

def get_db_values(request, ssh, query):
    #Run MySQL query on device via SSH and return output
    cmd = f"mysql -u {request.session.db_user} -p{request.session.db_pass} -D {request.session.easy_mesh_db} -se \"{query}\""
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
        print(f"Dialog Message:\n{msg}")
        dialog.accept()
    else:
        print(f"Dialog Message:\n{msg}")
        pytest.fail("Error in handling the Wi-Fi reset confirmation dialog.")

def get_reset_json_data(request, ssh):
    #Read Reset.json from the controller and return parsed data.
    cmd = f"cat {request.session.reset_json_file}"
    out = ssh.run("controller", cmd)
    try:
        data = json.loads(out)
    except Exception as e:
        pytest.fail(f"Failed to parse Reset.json: {e}")
    return data.get("wfa-dataelements:Reset")

def get_network_ssid_list_db(request, ssh):
    #Fetch NetworkSSIDList table from DB dynamically with proper column names.
    
    #Step 1: Get column names of NetworkSSIDList table
    col_output = get_db_values(request, ssh, f"SHOW COLUMNS FROM {request.session.network_ssid_list_db_table};")
    if not col_output.strip():
        pytest.fail(f"No columns returned from {request.session.network_ssid_list_db_table}")
    columns = [line.split("\t")[0] for line in col_output.strip().splitlines()]

    #Step 2: Get NetworkSSIDList table rows
    row_output = get_db_values(request, ssh, f"SELECT * FROM {request.session.network_ssid_list_db_table};")
    if not row_output.strip():
        pytest.fail(f"No data returned from table {request.session.network_ssid_list_db_table}")
    data_rows = [line.split("\t") for line in row_output.strip().splitlines()]

    # Step 3: Map values to columns
    rows = []
    for values in data_rows:
        if len(values) != len(columns):
            pytest.fail(f"Row column count mismatch: {values}")
        rows.append(dict(zip(columns, values)))
    return rows

def normalize_bool(val):
    #Normalize DB boolean-like values (1, 0, true, false, yes, no) to Python bool.
    return str(val).lower() in ["1", "true", "yes"]