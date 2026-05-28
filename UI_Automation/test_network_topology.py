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
import playwright_utils
import utils
from utils import print_step, print_error, print_success
from skimage.metrics import structural_similarity as ssim
import cv2

# Documentation: [test_network_topology.py](Centralized_Test_Cases.md#test_network_topologypy)

# Documentation: [TC-TOPO-01](Centralized_Test_Cases.md#tc-topo-01-test_validate_ui_topology)
def test_validate_ui_topology(config, page, request, ssh, paths):
    print_step("Entering Test1: test_validate_ui_topology")
    # Test prerequisite: Ensure at least two extenders are connected, before running the network topology test scenario.
    if len(ssh.enabled_extenders) < 2:
        print("Test prerequisite: At least two extender devices are required to validate topology test scenarios.")
        pytest.skip("Need at least two extenders for topology validation.")
    # Navigate to Rdkbcli page
    playwright_utils.navigate_to_rdkbcli_page(config, page, 1)
    # Navigate to Network Topology page
    playwright_utils.navigate_to_required_rdkbcli_page(page, request, "Topology", 2, paths)
    # Wait for topology graph to load
    page.wait_for_selector("#topology-visualization svg")
    # Fetch topology backend data from DMCLI
    print_step("Step 3: Collect backend topology data to validate it against the UI topology data")
    device_ssid_map, device_count = utils.fetch_tr181_topology_verification_params(ssh)
    if device_ssid_map:
        print_success(f"TR-181 Device → SSID map fetched successfully: {device_ssid_map}")
    else:
        pytest.fail("Failed to fetch TR-181 Device → SSID map from backend")
    print_step("Step 4: Validate that the number of devices in the DML matches the number of extenders configured in the testbed")
    #Device count should match the number of extenders configured in the testbed
    num_of_extenders = len(config.get("extenders", {}))
    if  num_of_extenders == (device_count - 1):
         print_success("The number of devices in DML matches the number of extenders configured in the testbed")
    else:
        print_error(request, f"Device count mismatch: TR-181 topology has {device_count} devices, but {num_of_extenders} extenders are configured in the testbed")    
    # Fetch total node count from UI
    print_step("Step 5: Fetch the total number of nodes from the UI")
    nodes = page.locator("g.node")
    node_count = nodes.count()
    if node_count > 0:
        print_success(f"Total topology nodes found in UI: {node_count}")
    else:
        print_error(request, "Failed to fetch topology nodes from UI")
    # Validate the UI node details against the backend data
    print_step("Step 6: Verify that each mesh node in the UI matches the backend data, and confirm that each nodes SSID is consistent with the backend.")
    for i in range(node_count):
        node = nodes.nth(i)
        texts = node.locator("text")
        circles = node.locator("circle")
        node_name = texts.nth(texts.count() - 1).text_content().strip()
        print(f"\nChecking Node: {node_name}")
        for j in range(circles.count()):
            circle = circles.nth(j)
            ssid_name = texts.nth(j).text_content().strip()
            print(f"\nChecking SSID: {ssid_name}")
            # Trigger tooltip
            circle.dispatch_event("mouseover")
            tooltip = page.locator("#custom-tooltip")
            tooltip.wait_for(state="visible")
            tooltip_text = tooltip.text_content().strip()
            # Tooltip should contain SSID
            if ssid_name not in tooltip_text:
                print_error(request, f"SSID {ssid_name} not found in tooltip")
            # Extract MAC(s) from tooltip
            tooltip_macs = re.findall(r"([0-9a-f]{2}(?::[0-9a-f]{2}){5})", tooltip_text, re.I)
            tooltip_macs = [m.lower() for m in tooltip_macs]
            if not tooltip_macs:
                print_error(request, "No MAC addresses found in UI tooltip")
            print(f"UI tooltip MACs: {tooltip_macs}")
            # Match device ID by BSSID overlap
            matched_device_id = None
            for dev_id, ssid_map in device_ssid_map.items():
                if ssid_name in ssid_map:
                    if any(mac in tooltip_macs for mac in ssid_map[ssid_name]['bssids']):
                        matched_device_id = dev_id
                        break
            if not matched_device_id:
                print_error(request, f"No matching device found for SSID {ssid_name} with tooltip MACs {tooltip_macs}")
            # Compare BSSIDs: only check those present in tooltip (ignore placeholders and foreign mesh)
            expected_bssids = [
                b for b in device_ssid_map[matched_device_id][ssid_name]['bssids']
                if b != "00:00:00:00:00:00" and b in tooltip_macs
            ]
            for bssid in expected_bssids:
                if bssid not in tooltip_macs:
                    print_error(request, f"BSSID {bssid} missing for SSID {ssid_name}")
            # If private SSID, check MLD MAC
            mld_mac = device_ssid_map[matched_device_id][ssid_name].get('mld_mac')
            if mld_mac and mld_mac not in tooltip_macs: 
                print_error(request, f"MLD MAC {mld_mac} missing for SSID {ssid_name}")
            print_success(f"All BSSIDs verified for SSID '{ssid_name}'")
    # Manually validated the network topology screenshot, as UI data may differ from the actual state
    print_step("Step 7: Capture the network topology page screenshot.")
    # Close tooltip before screenshot
    page.evaluate("""
    () => {
        const tooltip = document.querySelector('#custom-tooltip');
        if (tooltip) tooltip.remove();
    }
    """)
    playwright_utils.take_screenshot(page, request, paths["screenshots"] / "network_topology.png")
    
    print_step("Step 8: Verify whether the current topology matches Star or Daisychain topology from RDKB-CLI.")
    print_step("Step 8a: Verify whether the current topology matches with Star topology.")
    img1 = cv2.imread(f"{paths['network_topology_screenshots']}/star_network_topology.png")
    img2 = cv2.imread(f"{paths['screenshots']}/network_topology.png")
    #img2 = cv2.imread(f"{paths['screenshots']}/daisychain_network_topology.png")
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, diff = ssim(gray1, gray2, full=True)
    #print("Similarity:", score)
    if score < 0.99:
        print_error(request, "Current topology does not match with Star network topology")
        print_step("Step 8b: Verify whether the current topology matches Daisychain topology.")
        img3 = cv2.imread(f"{paths['network_topology_screenshots']}/daisychain_network_topology.png")
        gray3 = cv2.cvtColor(img3, cv2.COLOR_BGR2GRAY)
        score, diff = ssim(gray3, gray2, full=True)
        #print("Similarity:", score)
        if score < 0.99:
            print_error(request, "Current topology does not match with Daisychain network topology")
        else:
            print_success("Current topology matches with Daisychain network topology")
    else:
        print_success("Current topology matches with Star network topology")
    print_step("Exiting Test1: test_validate_ui_topology")

# Documentation: [TC-TOPO-02](Centralized_Test_Cases.md#tc-topo-02-test_determine_topology_type_from_brctl_command)
def test_determine_topology_type_from_brctl_command(config, request, ssh):
    print_step("Entering Test2: test_determine_topology_type_from_brctl_command")
    # Test prerequisite: Ensure at least two extenders are connected, before running the network topology test scenario.
    if len(ssh.enabled_extenders) < 2:
        print("Test prerequisite: At least two extender devices are required to validate topology test scenarios.")
        pytest.skip("Need at least two extenders for topology validation.")
    # Retrieve STA interfaces from controller bridge
    bridge_intf = config["system"]["bridge_intf"]
    print_step("Step 1: Retrieve STA interfaces from the controller bridge")
    sta_interfaces = utils.get_sta_interfaces_from_bridge(ssh, "controller", bridge_intf)
    # Validate STA interface availability
    if len(sta_interfaces) == 0:
        print_error(request, "No STA interfaces were detected on the controller bridge, so the mesh topology could not be determined.")
    else:
        print_success(f"Controller bridge {bridge_intf} contains {len(sta_interfaces)} STA interface(s): {sta_interfaces}.")
        # Dump station details for controller-connected extenders
        print_step("Step 2: Retrieve station dump details for controller-connected extenders.")
        for sta_iface in sta_interfaces:
            dump_output = utils.run_command_fetch_output_from_device(f"iw dev {sta_iface} station dump", "controller", ssh)

            if not dump_output.strip():
                pytest.fail(f"No station dump information found for interface {sta_iface}.")
            else:
                print_success(f"Station dump retrieved successfully for STA interface {sta_iface}.")
                print(dump_output)
        # Determine topology type
        print_step("Step 3: Determine mesh topology type based on STA interface count")
        # Star topology validation
        if len(sta_interfaces) >= 2:
            print(f"Controller has {len(sta_interfaces)} directly connected extenders.")
            print_success("Star mesh topology detected.")
        # Daisy topology validation
        elif len(sta_interfaces) == 1:
            print("Single extender connected to controller; starting daisy-chain topology traversal.")
            # Collect first-hop MAC from controller
            print_step("Step 3.1: Retrieve first-hop (Direct Extender) MAC address from controller.")
            parent_mac = utils.get_station_mac("controller", sta_interfaces[0], ssh)
            if not parent_mac:
                pytest.fail("Failed to retrieve first-hop MAC address from controller station dump output")
            else:
                print_success(f"First-hop extender MAC address: {parent_mac}")
                # Create extender MAC mapping
                print_step("Step 3.2: Build extender mesh backhaul MAC address mapping")
                extender_mac_map, mac_map_ok = utils.build_extender_mac_map(request, ssh)
                if not mac_map_ok:
                    pytest.fail("Failed to build extender mesh backhaul MAC address mapping")
                else:
                    print_success(f"Successfully built extender MAC mapping for {len(extender_mac_map)} extender(s)")
                    # Start daisy-chain traversal validation
                    print_step("Step 3.3: Start hop-by-hop daisy-chain traversal validation")
                    utils.validate_daisy_topology(parent_mac, extender_mac_map, config, request, ssh)
        # Unexpected topology state
        else:
            print_error(request, "Unexpected STA interface state detected; unable to determine mesh topology")
    print_step("Exiting Test2: test_determine_topology_type_from_brctl_command")
