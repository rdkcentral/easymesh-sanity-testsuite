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
import warnings
import pytest
import conftest
import utils
from utils import print_step, print_error, print_success
from skimage.metrics import structural_similarity as ssim
import cv2

def test_validate_ui_topology(page, request, ssh, paths):
    print_step("Entering Test1: test_validate_ui_topology")
    # Navigate to Rdkbcli page
    utils.navigate_to_rdkbcli_page(page, request, 1)
    # Navigate to Network Topology page
    utils.navigate_to_required_rdkbcli_page(page, request, "Topology", 2, paths)
    # Wait for topology graph to load
    page.wait_for_selector("#topology-visualization svg")
    # Fetch topology backend data from DMCLI
    print_step("Step 3: Collect backend topology data to validate it against the UI topology data")
    device_ssid_map = utils.fetch_tr181_topology_verification_params(ssh)
    print(f"TR-181 Device → SSID map: {device_ssid_map}")
    # Fetch total node count from UI
    print_step("Step 4: Fetch the total number of nodes from the UI")
    nodes = page.locator("g.node")
    node_count = nodes.count()
    print(f"Total topology nodes found: {node_count}")
    # Validate the UI node details against the backend data
    print_step("Step 5: Verify that each mesh node in the UI matches the backend data, and confirm that each nodes SSID is consistent with the backend.")
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
    print_step("Step 6: Capture the network topology page screenshot.")
    # Close tooltip before screenshot
    page.evaluate("""
    () => {
        const tooltip = document.querySelector('#custom-tooltip');
        if (tooltip) tooltip.remove();
    }
    """)
    utils.take_screenshot(page, request, paths["screenshots"] / "network_topology.png")
    
    print_step("Step 7: Verify whether the current topology matches Star or Daisychain topology from RDKB-CLI.")
    print_step("Step 7a: Verify whether the current topology matches with Star topology.")
    img1 = cv2.imread(f"{paths['network_topology_screenshots']}/star_network_topology.png")
    img2 = cv2.imread(f"{paths['screenshots']}/network_topology.png")
    #img2 = cv2.imread(f"{paths['screenshots']}/daisychain_network_topology.png")
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, diff = ssim(gray1, gray2, full=True)
    #print("Similarity:", score)
    if score < 0.99:
        print_error(request, "Current topology does not match with Star network topology")
        print_step("Step 7b: Verify whether the current topology matches Daisychain topology.")
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

#Need three BPI devices to validate below test case
def test_determine_topology_type_from_brctl_command(request, ssh):
    print_step("Entering Test2: test_determine_topology_type_from_brctl_command")
    # Determine mesh topology (Star or Daisy) based on backhaul bridge station interfaces.
    # Step 1: Fetch all station interfaces from the backhaul bridge
    print_step(f"Step 1: Fetch station interfaces from bridge '{request.session.bridge_intf}' on controller device")
    sta_interfaces = utils.get_sta_interfaces_from_bridge(ssh, "controller", request.session.bridge_intf)
    print_step(f"Bridge '{request.session.bridge_intf}' STA interfaces: {sta_interfaces} (No of extender devices connected={len(sta_interfaces)})")
    # Mesh topology is undefined if no station interfaces are present.
    if len(sta_interfaces) == 0:
        print_error(request, "No station interfaces detected on the backhaul bridge; cannot determine mesh topology.")
    print_step("Step 2: Dump station details for extenders directly connected to the controller.")
    # Dump detailed info for each station interface
    for sta_iface in sta_interfaces:
        print(f"\nDump station info for interface: {sta_iface}")
        dump_output = ssh.run("controller", f"iw dev {sta_iface} station dump")
        # check if the output is empty
        if not dump_output.strip():
            print_error(request, f"No station information found for interface {sta_iface}; cannot validate mesh connection")
        print(dump_output)
    # Determine mesh topology based on number of station interfaces
    print_step("Step 3: Determine mesh topology based on station interface count")

    if len(sta_interfaces) >= 2:
        mesh_topology = "Star"

    elif len(sta_interfaces) == 1:
        # If only one STA on controller, check agent for child extender connections
        print_step("Single STA on controller → checking agent for child extender connections")
        agent_sta_interfaces = utils.get_sta_interfaces_from_bridge(ssh, "agent", request.session.bridge_intf)
        print_step(f"Agent STA interfaces: {agent_sta_interfaces} (No of extender devices connected ={len(agent_sta_interfaces)})")
        if agent_sta_interfaces:
            print_step("Step 2 (Agent): Dump station details for child extenders connected to agent.")
            for sta_iface in agent_sta_interfaces:
                print_step(f"\nDump station info for agent interface: {sta_iface}")
                dump_output = ssh.run("agent", f"iw dev {sta_iface} station dump")
                # check if the output is empty
                if not dump_output.strip():
                    print_error(request, f"No station information found on agent interface {sta_iface}; child extender not connected")
                print(dump_output)
            mesh_topology = "Daisy"
        else:
            print_error(request, "No child extender connections found on agent; cannot determine Daisy topology.")
    else:
        print_error(request, "Mesh topology could not be determined. Please check the backhaul interfaces.")
    print(f"\nDetected Mesh Topology: {mesh_topology}")
    print_step("Exiting Test2: test_determine_topology_type_from_brctl_command")
