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

from playwright.sync_api import expect, sync_playwright
import message_verify
import time
import capture_utils
import pytest_check as check
import ieee1905_utils
from UI_Automation.utils import *
from UI_Automation.playwright_utils import *
from UI_Automation.conftest import *

def get_controller_agent_mac(request, ssh):
    ctrl_mac = get_interface_mac_address("controller", "eth0_virt_peer", ssh)
    ext_mac = get_interface_mac_address("agent", "eth1_virt_peer", ssh)
    return ctrl_mac, ext_mac

def test_capture_and_analyze_packets_with_ssid_update(page, paths, request, ssh, config):
    print_step("Entering test_capture_and_analyze_packets_with_ssid_update test")    
    # Initialize controller and agent MAC addresses
    ctrl_mac, agent_mac = get_controller_agent_mac(request, ssh, config)
    message_verify.controller_mac = ctrl_mac
    message_verify.agent_mac = agent_mac
    
    #Capture packets on the Wi-Fi interface
    remote_capture_file_path = "/tmp/ssid_update.pcap"
    local_capture_file_path = paths["run_dir"] / "Captured_Packets"
    local_capture_file_path.mkdir(parents=True, exist_ok=True)
    local_capture_file_name = local_capture_file_path / "ssid_update.pcap"
    new_ssid = "TDKB_Test12345"
    print_step("\nStep 1: Start packet capture on Wi-Fi interface")  
    capture_id = capture_utils.capture_packets(ssh, intf, filter, 0, remote_capture_file_path)
    time.sleep(2)
    #Update the SSID from RDKBCLI and verify update on controller and agent devices    
    verify_ssid_update_in_controller_and_agent(config, page, request, ssh, new_ssid, 2, paths)
    time.sleep(40)
    #time.sleep(5)
    print_step("\nStep 10: Stop the packet capture")
    #Stop packet capture
    capture_utils.stop_packet_capture(ssh, capture_id)
    #time.sleep(5)

    print_step("\nStep 11: Verify if captured file exists on device after stopping capture")
    #Verify if the captured packet file exists on the device after stopping capture. If not, print appropriate error message and fail the test.
    out = ssh.run("controller", f"ls -l {remote_capture_file_path}")
    file_exists = "No such file" not in out
    check.is_true(file_exists, f"\nFail: Failed to find captured file at {remote_capture_file_path} on device after stopping capture.")
    if file_exists:
        print_success(f"Captured file found at {remote_capture_file_path} on device after stopping capture.")
    else:
        print_error(request, f"Captured file not found at {remote_capture_file_path} on device. Cannot proceed with transfer and analysis.")
        pytest.fail(f"Captured file not found at {remote_capture_file_path} on device. Cannot proceed with transfer and analysis.")        

    print_step("\nStep 12: Transfer the captured packet file to local machine for analysis")
    #Transfer the captured packet file to local machine for analysis
    check.equal(capture_utils.transfer_capfile_from_device(ssh, remote_capture_file_path, f"{local_capture_file_name}"), True, "\nFail: Failed to transfer captured file from device.")

    print_step("\nStep 13: Delete the captured packet file from device to free up space")
    #Delete the captured file from device after transfer to free up space
    out = ssh.run("controller", f"rm -f {remote_capture_file_path}")
    print_success(f"Deleted captured file from device to free up space.")

    print_step("\n\nStep 14: Start analyzing captured packets to verify the presence of expected messages")
    print_step("Step 14a: Analyze the captured packets for AP-autoconfiguration renew message ")
    check.equal(message_verify.verify_cmdu_presence(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, expected_renew_count), True, f"\nFail: Expected CMDU count {expected_renew_count} not found in AP Autoconfiguration Renew message.")
    print_step("Step 14b: Analyze the captured packets for AP-autoconfiguration Wi-Fi simple configuration (WSC) message")    
    check.equal(message_verify.verify_cmdu_presence(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, expected_count_wsc), True, f"\nFail: Expected CMDU count {expected_count_wsc} not found in AP Autoconfiguration WSC message.")
    print_step("Step 14c: Analyze the captured packets for Topology query message")    
    check.equal(message_verify.verify_cmdu_presence(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_QUERY, expected_count_topology_query), True, f"\nFail: Expected CMDU count {expected_count_topology_query} not found in Topology query message.")
    print_step("Step 14d: Analyze the captured packets for Topology response message")
    check.equal(message_verify.verify_cmdu_presence(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, expected_count_topology_response), True, f"\nFail: Expected CMDU count {expected_count_topology_response} not found in Topology response message.")
    print("Completed analyzing captured packets to verify the presence of expected messages")

    print_step("\n\nStep 15: Start analyzing the AP Autoconfiguration Renew message to verify the presence of required TLVs")
    print_step("Step 15a: Analyze the AP Autoconfiguration Renew message to verify the presence of the 1905.1 AL MAC Address TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_AL_MAC_ADDRESS), True, "\nFail: Expected TLV type 'AL MAC Address TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 15b: Analyze the AP Autoconfiguration Renew message to verify the presence of the SupportedRole TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_SUPPORTED_ROLE), True, "\nFail: Expected TLV type 'Supported Role TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 15c: Analyze the AP Autoconfiguration Renew message to verify the presence of the SupportedFreqBand TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_SUPPORTED_FREQ_BAND), True, "\nFail: Expected TLV type 'Supported Freq Band TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 15d: Analyze the AP Autoconfiguration Renew message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End OF Message TLV' not found in AP Autoconfiguration Renew message.")
    print("Completed analyzing the AP Autoconfiguration Renew message to verify the presence of required TLVs")

    print_step("\n\nStep 16: Start analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of required TLVs")
    print_step("Step 16a: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the WSC TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_WSC), True, "\nFail: Expected TLV type 'WSC TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 16b: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the AP Radio Basic Capabilities TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES), True, "\nFail: Expected TLV type 'AP Radio Basic Capabilities TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 16c: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the Profile-2 AP Capability TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_PROFILE_2_AP_CAPABILITY), True, "\nFail: Expected TLV type 'Profile-2 AP Capability TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 16d: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the AP Radio Advanced Capabilities TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES), True, "\nFail: Expected TLV type 'AP Radio Advanced Capabilities TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 16e: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the End Of Message TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print("Completed analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of required TLVs")

    print_step("\n\nStep 17: Start analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of required TLVs")
    print_step("Step 17a: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the WSC TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_WSC, M2_TYPE), True, "\nFail: Expected TLV type 'WSC TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print_step("Step 17b: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the AP Radio Identifier TLV")        
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_IDENTIFIER, M2_TYPE), True, "\nFail: Expected TLV type 'AP Radio Identifier TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print_step("Step 17c: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_END_OF_TLV, M2_TYPE), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print("Completed analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of required TLVs")

    print_step("\n\nStep 18: Start analyzing the Topology query message to verify the presence of required TLVs")
    print_step("Step 18a: Analyze the Topology query message to verify the presence of the  Multi-AP Profile TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_QUERY, ieee1905_utils.TLV_TYPE_MULTI_AP_PROFILE), True, "\nFail: Expected TLV type 'Multi-AP Profile TLV' not found in Topology query message.")
    print_step("Step 18b: Analyze the Topology query message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_QUERY, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in Topology query message.")
    print("Completed analyzing the Topology query message to verify the presence of required TLVs")

    print_step("\n\nStep 19: Start analyzing the Topology response message to verify the presence of required TLVs")
    print_step("Step 19a: Analyze the Topology response message to verify the presence of the device information type TLV") 
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_DEVICE_INFORMATION), True, "\nFail: Expected TLV type 'Device Information TLV' not found in Topology response message.")
    print_step("Step 19b: Analyze the Topology response message to verify the presence of the Multi-AP Profile TLV")  
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_MULTI_AP_PROFILE), True, "\nFail: Expected TLV type 'Multi-AP Profile TLV' not found in Topology response message.")
    print_step("Step 19c: Analyze the Topology response message to verify the presence of the AP Operational BSS TLV")      
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_AP_OPERATIONAL_BSS), True, "\nFail: Expected TLV type 'AP Operational BSS TLV' not found in Topology response message.")
    print_step("Step 19d: Analyze the Topology response message to verify the presence of the BSS Configuration Report TLV")      
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_BSS_CONFIG_REPORT), True, "\nFail: Expected TLV type 'BSS Configuration Report TLV' not found in Topology response message.")
    print_step("Step 19e: Analyze the Topology response message to verify the presence of the End Of Message TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{local_capture_file_name}", MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in Topology response message.")
    print("Completed analyzing the Topology response message to verify the presence of required TLVs")

    print_step("\n\nStep 20: Start analyzing the AP Autoconfiguration Renew message to verify the status of relay indicator flag: expected status : 1")
    check.equal(message_verify.verify_relay_indicator_flag_status(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_RENEW), True, "\nFail: Expected relay indicator flag status not found in captured packets.")
    print("Completed analyzing the AP Autoconfiguration Renew message to verify the status of relay indicator flag")

    print_step("\n\nStep 21: Start analyzing the AP Autoconfiguration Renew message to ensure the transmitter MAC and the 1905.1 AL MAC Address TLV value are identical")
    check.equal(message_verify.verify_1905_al_mac_address(f"{local_capture_file_name}", MSG_TYPE_AP_AUTOCONFIG_RENEW), True, "\nFail: 1905.1 AL MAC Address TLV value in autoconfiguration renew message is not matching with Transmitter MAC")
    print("Completed analyzing the AP Autoconfiguration Renew message to ensure the transmitter MAC and the 1905.1 AL MAC Address TLV value are identical")

    print_step("\n\nStep 22: Start analyzing the Topology response message to verify the presence of the updated SSID in the AP Operational BSS TLV")
    check.equal(message_verify.verify_ssidname_in_topology_response(f"{local_capture_file_name}", new_ssid), True, "\nFail: Updated SSID not found in AP Operational BSS TLV of Topology response message.")
    print("Completed analyzing the Topology response message to verify the presence of the updated SSID in the AP Operational BSS TLV")
    print_step("Exiting test_capture_and_analyze_packets_with_ssid_update")
