import conftest
from playwright.sync_api import expect, sync_playwright
import message_verify
import utils
import time
import capture_utils
import pytest_check as check
import ieee1905_utils
from ieee1905_utils import print_success, print_error, print_step


def test_capture_and_analyze_packets_with_ssid_update(request, page, ssh):
    print_step("Entering test_capture_and_analyze_packets_with_ssid_update test")
    #Capture packets on the Wi-Fi interface
    capture_file_path = "/tmp/ssid_update.pcap"
    print_step("\nStep 1: Start packet capture on Wi-Fi interface")
    capture_id = capture_utils.capture_packets(ssh, conftest.intf, conftest.filter, 0, capture_file_path)
    
    #Update the SSID from RDKBCLI and verify update on controller and agent devices
    results = utils.verify_ssid_update_in_controller_and_agent(page, request, ssh)
    
    #Validate if SSID updates are consistent on both controller and agent devices and match the expected value from test data. If there is a mismatch, print appropriate error message and fail the test.
    print_step("\nStep 10: Validate if updated SSID is consistent on both controller and agent devices")
    check.equal(results[0], request.session.ssid, "\nFail: SSID update validation failed on controller device")
    check.equal(results[1], request.session.ssid, "\nFail: SSID update validation failed on agent device")
    if results[0] != request.session.ssid or results[1] != request.session.ssid:
        print_error(f"SSID update is NOT consistent with controller and agent devices. Expected SSID: {request.session.ssid}, Actual SSID on controller: {results[0]}, Actual SSID on agent: {results[1]}")
        check.is_true(False, f"\nSSID mismatch between controller/agent devices. Expected SSID: {request.session.ssid}, Actual SSID on controller: {results[0]}, Actual SSID on agent: {results[1]}")
    else:
        print_success(f"SSID update is consistent with controller and agent devices. Expected SSID: {request.session.ssid}, Actual SSID on controller: {results[0]}, Actual SSID on agent: {results[1]}")
    #time.sleep(10)
    #time.sleep(5)
    print_step("\nStep 11: Stop the packet capture")
    #Stop packet capture
    capture_utils.stop_packet_capture(ssh, capture_id)
    #time.sleep(5)

    print_step("\nStep 12: Verify if captured file exists on device after stopping capture")
    #Verify if the captured packet file exists on the device after stopping capture. If not, print appropriate error message and fail the test.
    out = ssh.run("controller", f"ls -l {capture_file_path}")
    if "No such file" in out:
        check.equal((False, f"\nFail: Failed to find captured file at {capture_file_path} on device after stopping capture."))
    else:
        print_success(f"Captured file found at {capture_file_path} on device after stopping capture.")
    
    print_step("\nStep 13: Transfer the captured packet file to local machine for analysis")
    #Transfer the captured packet file to local machine for analysis
    check.equal(capture_utils.transfer_capfile_from_device(ssh, capture_file_path, f"{conftest.capture_file_path}/ssid_update.pcap"), True, "\nFail: Failed to transfer captured file from device.")

    print_step("\nStep 14: Delete the captured packet file from device to free up space")
    #Delete the captured file from device after transfer to free up space
    out = ssh.run("controller", f"rm -f {capture_file_path}")
    print_success(f"Deleted captured file from device to free up space.")

    print_step("\n\nStep 15: Start analyzing captured packets to verify the presence of expected messages")
    print_step("Step 15a: Analyze the captured packets for AP-autoconfiguration renew message ")
    check.equal(message_verify.verify_cmdu_presence(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, conftest.expected_renew_count), True, f"\nFail: Expected CMDU count {conftest.expected_renew_count} not found in AP Autoconfiguration Renew message.")
    print_step("Step 15b: Analyze the captured packets for AP-autoconfiguration Wi-Fi simple configuration (WSC) message")    
    check.equal(message_verify.verify_cmdu_presence(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, conftest.expected_count_wsc), True, f"\nFail: Expected CMDU count {conftest.expected_count_wsc} not found in AP Autoconfiguration WSC message.")
    print_step("Step 15c: Analyze the captured packets for Topology query message")    
    check.equal(message_verify.verify_cmdu_presence(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_QUERY, conftest.expected_count_topology_query), True, f"\nFail: Expected CMDU count {conftest.expected_count_topology_query} not found in Topology query message.")
    print_step("Step 15d: Analyze the captured packets for Topology response message")
    check.equal(message_verify.verify_cmdu_presence(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, conftest.expected_count_topology_response), True, f"\nFail: Expected CMDU count {conftest.expected_count_topology_response} not found in Topology response message.")
    print("Completed analyzing captured packets to verify the presence of expected messages")

    print_step("\n\nStep 16: Start analyzing the AP Autoconfiguration Renew message to verify the presence of required TLVs")
    print_step("Step 16a: Analyze the AP Autoconfiguration Renew message to verify the presence of the 1905.1 AL MAC Address TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_AL_MAC_ADDRESS), True, "\nFail: Expected TLV type 'AL MAC Address TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 16b: Analyze the AP Autoconfiguration Renew message to verify the presence of the SupportedRole TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_SUPPORTED_ROLE), True, "\nFail: Expected TLV type 'Supported Role TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 16c: Analyze the AP Autoconfiguration Renew message to verify the presence of the SupportedFreqBand TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_SUPPORTED_FREQ_BAND), True, "\nFail: Expected TLV type 'Supported Freq Band TLV' not found in AP Autoconfiguration Renew message.")
    print_step("Step 16d: Analyze the AP Autoconfiguration Renew message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End OF Message TLV' not found in AP Autoconfiguration Renew message.")
    print("Completed analyzing the AP Autoconfiguration Renew message to verify the presence of required TLVs")

    print_step("\n\nStep 17: Start analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of required TLVs")
    print_step("Step 17a: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the WSC TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_WSC), True, "\nFail: Expected TLV type 'WSC TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 17b: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the AP Radio Basic Capabilities TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES), True, "\nFail: Expected TLV type 'AP Radio Basic Capabilities TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 17c: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the Profile-2 AP Capability TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_PROFILE_2_AP_CAPABILITY), True, "\nFail: Expected TLV type 'Profile-2 AP Capability TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 17d: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the AP Radio Advanced Capabilities TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES), True, "\nFail: Expected TLV type 'AP Radio Advanced Capabilities TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print_step("Step 17e: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of the End Of Message TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message.")
    print("Completed analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M1) message to verify the presence of required TLVs")

    print_step("\n\nStep 18: Start analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of required TLVs")
    print_step("Step 18a: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the WSC TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_WSC, conftest.M2_TYPE), True, "\nFail: Expected TLV type 'WSC TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print_step("Step 18b: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the AP Radio Identifier TLV")        
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_AP_RADIO_IDENTIFIER, conftest.M2_TYPE), True, "\nFail: Expected TLV type 'AP Radio Identifier TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print_step("Step 18c: Analyze the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, ieee1905_utils.TLV_TYPE_END_OF_TLV, conftest.M2_TYPE), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message.")
    print("Completed analyzing the AP-autoconfiguration Wi-Fi simple configuration (WSC - M2) message to verify the presence of required TLVs")

    print_step("\n\nStep 19: Start analyzing the Topology query message to verify the presence of required TLVs")
    print_step("Step 19a: Analyze the Topology query message to verify the presence of the  Multi-AP Profile TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_QUERY, ieee1905_utils.TLV_TYPE_MULTI_AP_PROFILE), True, "\nFail: Expected TLV type 'Multi-AP Profile TLV' not found in Topology query message.")
    print_step("Step 19b: Analyze the Topology query message to verify the presence of the End Of Message TLV")    
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_QUERY, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in Topology query message.")
    print("Completed analyzing the Topology query message to verify the presence of required TLVs")

    print_step("\n\nStep 20: Start analyzing the Topology response message to verify the presence of required TLVs")
    print_step("Step 20a: Analyze the Topology response message to verify the presence of the device information type TLV") 
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_DEVICE_INFORMATION), True, "\nFail: Expected TLV type 'Device Information TLV' not found in Topology response message.")
    print_step("Step 20b: Analyze the Topology response message to verify the presence of the Multi-AP Profile TLV")  
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_MULTI_AP_PROFILE), True, "\nFail: Expected TLV type 'Multi-AP Profile TLV' not found in Topology response message.")
    print_step("Step 20c: Analyze the Topology response message to verify the presence of the AP Operational BSS TLV")      
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_AP_OPERATIONAL_BSS), True, "\nFail: Expected TLV type 'AP Operational BSS TLV' not found in Topology response message.")
    print_step("Step 20d: Analyze the Topology response message to verify the presence of the BSS Configuration Report TLV")      
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_BSS_CONFIG_REPORT), True, "\nFail: Expected TLV type 'BSS Configuration Report TLV' not found in Topology response message.")
    print_step("Step 20e: Analyze the Topology response message to verify the presence of the End Of Message TLV")
    check.equal(message_verify.verify_tlv_presence_with_type(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE, ieee1905_utils.TLV_TYPE_END_OF_TLV), True, "\nFail: Expected TLV type 'End Of Message TLV' not found in Topology response message.")
    print("Completed analyzing the Topology response message to verify the presence of required TLVs")

    print_step("\n\nStep 21: Start analyzing the AP Autoconfiguration Renew message to verify the status of relay indicator flag: expected status : 1")
    check.equal(message_verify.verify_relay_indicator_flag_status(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW), True, "\nFail: Expected relay indicator flag status not found in captured packets.")
    print("Completed analyzing the AP Autoconfiguration Renew message to verify the status of relay indicator flag")

    print_step("\n\nStep 22: Start analyzing the AP Autoconfiguration Renew message to ensure the transmitter MAC and the 1905.1 AL MAC Address TLV value are identical")
    check.equal(message_verify.verify_1905_al_mac_address(f"{conftest.capture_file_path}/ssid_update.pcap", conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW), True, "\nFail: 1905.1 AL MAC Address TLV value in autoconfiguration renew message is not matching with Transmitter MAC")
    print("Completed analyzing the AP Autoconfiguration Renew message to ensure the transmitter MAC and the 1905.1 AL MAC Address TLV value are identical")

    print_step("\n\nStep 23: Start analyzing the Topology response message to verify the presence of the updated SSID in the AP Operational BSS TLV")
    check.equal(message_verify.verify_ssidname_in_topology_response(f"{conftest.capture_file_path}/ssid_update.pcap"), True, "\nFail: Updated SSID not found in AP Operational BSS TLV of Topology response message.")
    print("Completed analyzing the Topology response message to verify the presence of the updated SSID in the AP Operational BSS TLV")
    print_step("Exiting test_capture_and_analyze_packets_with_ssid_update")