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
import pytest
import utils
import playwright_utils
import time
from utils import print_step, print_error, print_success

# Documentation: [test_wifi_client_connectivity.py](Sanity_Tests_Documentation.md#test_wifi_client_connectivitypy)

@pytest.fixture(scope="module", autouse=True)
def check_wifi_clients(ssh):
    if len(ssh.enabled_wifi_clients) == 0:
        print("No enabled Wi-Fi client detected. Please ensure at least one Wi-Fi client is available. Skipping wireless client connectivity test cases.")
        pytest.skip("Test setup pre-requisite not met: at least one enabled Wi-Fi client is required.")

# Documentation: [TC-WIFI-01](Sanity_Tests_Documentation.md#tc-wifi-01-test_fronthaul_wifi_client_connectivity)
def test_fronthaul_wifi_client_connectivity(config, request, ssh):
    print_step("Entering Test1: test_fronthaul_wifi_client_connectivity")
    # Verify client connectivity using fronthaul credentials
    utils.validate_fronthaul_client_connectivity(config, request, ssh, step=1)
    print_step("Exiting Test1: test_fronthaul_wifi_client_connectivity")

# Documentation: [TC-WIFI-02](Sanity_Tests_Documentation.md#tc-wifi-02-test_fronthaul_wifi_client_connectivity_with_updated_ssid)
def test_fronthaul_wifi_client_connectivity_with_updated_ssid(config, page, request, ssh, paths):
    print_step("Entering Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
    print("Update fronthaul SSID via RDKB-CLI and validate on controller and extender devices")
    new_ssid = "TDKB_New_SSID_01"
    playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 1, "ssid", new_ssid, 'Fronthaul', 5000)
    ssid_update_status = utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, new_ssid, 6)
    if ssid_update_status:
        # Wait 60 sec for the updated ssid to broadcast
        time.sleep(60)
        # Verify client connectivity after successful SSID update on controller and extender
        print_step("\nValidate fronthaul client connectivity after SSID update")
        utils.validate_fronthaul_client_connectivity(config, request, ssh, step=1)
        # Revert the SSID back to default value
        print_step("\nStep 8: Revert the SSID value back to default in RDKB CLI and verify the update on device")
        default_ssid = config["database"]["network_ssid_map"]["Fronthaul"]["default_ssid"]
        playwright_utils.update_verify_required_field_from_rdkbcli(config, page, request, paths, 1, "ssid", default_ssid, 'Fronthaul', 5000)
        ssid_revert_status = utils.verify_ssid_update_in_controller_and_agent(page, request, ssh, default_ssid, 6)
        if ssid_revert_status:
            print_success(f"Successfully reverted back the SSID to default value {default_value}")
        else:
            print_error(request, f"Failed to revert back the SSID to default value {default_value")
    else:
        print_error(request, f"Failed to set SSID to the new value {new_ssid}")
    print_step("Exiting Test2: test_fronthaul_wifi_client_connectivity_with_updated_ssid")
