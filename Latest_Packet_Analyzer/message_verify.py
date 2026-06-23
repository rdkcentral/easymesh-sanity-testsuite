import sys
from scapy.all import rdpcap, Ether
import conftest
from ieee1905_utils import *
import re
import yaml
import pytest
import pytest_check as check
import test_logic

ETHERTYPE_1905 = 0x893A

fragment_store = {}
m1_message_store = {}
header_1905 = ""

controller_mac = conftest.controller_mac
agent_mac = conftest.agent_mac
M2_TYPE = conftest.M2_TYPE

MSG_TYPE_AP_AUTOCONFIGURATION_RENEW = conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RENEW
MSG_TYPE_AP_TOPOLOGY_QUERY = conftest.MSG_TYPE_AP_TOPOLOGY_QUERY
MSG_TYPE_AP_TOPOLOGY_RESPONSE = conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE
MSG_TYPE_AP_AUTOCONFIG_WSC = conftest.MSG_TYPE_AP_AUTOCONFIG_WSC
MSG_TYPE_AP_AUTOCONFIG_RENEW = conftest.CMDU_AP_AUTOCONFIGURATION_RENEW
MSG_TYPE_TOPOLOGY_NOTIFICATION = conftest.MSG_TYPE_TOPOLOGY_NOTIFICATION
MSG_TYPE_AP_AUTOCONFIG_SEARCH = conftest.MSG_TYPE_AP_AUTOCONFIG_SEARCH
MSG_TYPE_TOPOLOGY_DISCOVERY = conftest.MSG_TYPE_TOPOLOGY_DISCOVERY
MSG_TYPE_AP_POLICY_CONFIG_REQUEST = conftest.MSG_TYPE_POLICY_CONFIG_REQUEST
MSG_TYPE_CHANNEL_SELECTION_REQUEST = conftest.MSG_TYPE_CHANNEL_SELECTION_REQUEST
MSG_TYPE_CHANNEL_SELECTION_RESPONSE = conftest.MSG_TYPE_CHANNEL_SELECTION_RESPONSE
MSG_TYPE_OPERATING_CHANNEL_REPORT = conftest.MSG_TYPE_OPERATING_CHANNEL_REPORT
MSG_TYPE_AP_CAPABILITY_REPORT  = conftest.MSG_TYPE_AP_CAPABILITY_REPORT
MSG_TYPE_AP_CAPABILITY_QUERY = conftest.MSG_TYPE_AP_CAPABILITY_QUERY
MSG_TYPE_1905_ACK = conftest.MSG_TYPE_1905_ACK
MSG_TYPE_CHANNEL_PREFERENCE_QUERY = conftest.MSG_TYPE_CHANNEL_PREFERENCE_QUERY
MSG_TYPE_CHANNEL_PREFERENCE_REPORT = conftest.MSG_TYPE_CHANNEL_PREFERENCE_REPORT

expected_message_types = [MSG_TYPE_AP_AUTOCONFIG_RENEW,
MSG_TYPE_AP_AUTOCONFIG_WSC,
MSG_TYPE_AP_TOPOLOGY_QUERY,
MSG_TYPE_AP_TOPOLOGY_RESPONSE,
MSG_TYPE_AP_CAPABILITY_REPORT,
MSG_TYPE_AP_CAPABILITY_QUERY,
MSG_TYPE_1905_ACK,
MSG_TYPE_CHANNEL_PREFERENCE_QUERY,
MSG_TYPE_CHANNEL_PREFERENCE_REPORT]

#further items will populate if the key exists in the dictionary, otherwise it will be created with the default value of {"message_ids": set()}
message_count_details = {
    msg: {"message_ids": set()}
    for msg in expected_message_types
}

message_details = {}

#########################################################

def load_yaml(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)
    
def get_profile_name(profile_type):
    profile_names = {
        0x01: "Profile 1",
        0x02: "Profile 2",
        0x03: "Profile 3"
    }
    return profile_names.get(profile_type, f"Unknown profile type: 0x{profile_type:02X}")

def get_message_type_name(message_type):
    """
    Convert hex message type to human-readable string
    """
    message_names = {
        0x000A: "AP Autoconfiguration Renew message",
        0x0009: "AP Autoconfiguration WSC message",
        0x0002: "Topology Query Message",
        0x0003: "Topology Response Message",
        0x0000: "Topology Discovery Message",
        0x8000: "1905 ACK Message",
        0x8001: "AP Capability Query Message",
        0x8002: "AP Capability Report Message",
        0x0001: "Topology Notification Message",
        0x0007: "AP Autoconfiguration Search Message",
        0x0008: "AP Autoconfiguration response message",
        0x8003: "Multi-AP Policy Config Request Message",
        0x8004: "Channel Preference Query Message",
        0x8005: "Channel Preference Report Message",
        0x8006: "Channel Selection Request Message",
        0x8007: "Channel Selection Response Message",
        0x8008: "Operating Channel Report Message",

        0x0055: "AP Error message"
    }
    return message_names.get(message_type, f"Unknown message type: 0x{message_type:04X}")


def get_tlv_type_name(tlv_type):
    """
    Convert hex TLV type to human-readable string
    """
    tlv_names = {
        0x00: "End OF Message TLV",
        0x01: "AL MAC Address TLV",
        0x02: "MAC Address TLV",
        0x03: "Device Information TLV",
        0x04: "Device Bridging Capability TLV",
        0x06: "Non-1905 neighbor device list TLV",
        0x07: "1905.1 neighbor device list TLV",
        0x08: "Link Metric Query TLV",
        0x09: "Transmitter Link Metric TLV",
        0x0A: "Receiver Link Metric TLV",
        0x0D: "Searched Role TLV",
        0x0E: "Autoconfig Frequency Band TLV",
        0x0F: "Supported Role TLV",
        0x10: "Supported Frequency Band TLV",
        0x11: "WSC TLV",
        0x80: "SupportedService TLV",
        0x81: "SearchedService TLV",
        0x82: "AP Radio Identifier TLV",
        0x83: "AP Operational BSS TLV",
        0x84: "Associated Clients TLV",
        0x85: "AP Radio Basic Capabilities TLV",
        0x86: "AP HT Capabilities TLV",
        0x87: "AP VHT Capabilities TLV",
        0x88: "AP HE Capabilities TLV",
        0x89: "Steering Policy TLV",
        0x8A: "Metric Reporting Policy TLV",
        0x8B: "Channel Preference TLV",
        0x8C: "Radio Operation Restriction TLV",
        0x8D: "Transmit Power Limit TLV",
        0x8E: "Channel Selection Response TLV",
        0x8F: "Operating Channel Report TLV",
        0x92: "Client Association Event TLV",
        0xA1: "AP Capability TLV",
        0xA3: "Error Code TLV",
        0xA4: "Channel Scan Reporting Policy TLV",
        0xA5: "Channel Scan Capabilities TLV",
        0xA9: "1905 Layer Security Capability TLV",
        0xAA: "AP Wi-Fi 6 Capabilities TLV",
        0xAF: "CAC Completion Report TLV",
        0xB1: "CAC Status Report TLV",
        0xB2: "CAC Capabilities TLV",
        0xB3: "Multi-AP Profile TLV",
        0xB4: "Profile 2 AP Capability TLV",
        0xB5: "Default 802.1Q Settings TLV",
        0xB6: "Traffic Separation Policy TLV",
        0xB7: "BSS Config Report TLV",
        0xBC: "Profile-2 Error Code TLV",
        0xBE: "AP Radio Advanced Capabilities TLV",
        0xC4: "Unsuccessful Association Policy TLV",
        0xC5: "Metric Collection Interval TLV",
        0xCB: "Backhaul STA Radio Capabilities TLV",
        0xCC: "AKM Suite Capabilities TLV",
        0xD0: "Backhaul BSS Configuration TLV",
        0xD3: "DPP Chirp Value TLV",
        0xD4: "Device Inventory TLV",
        0xD8: "Spatial Reuse Request TLV",
        0xD9: "Spatial Reuse Report TLV",
        0xDA: "Spatial Reuse Config Response TLV",
        0xDB: "QoS Management Policy TLV",
        0xDD: "Controller Capability TLV",
        0xDF: "Wi-Fi 7 Agent Capabilities TLV",
        0xE0: "Agent AP MLD Configuration TLV",
        0xE1: "Backhaul STA MLD Configuration TLV",
        0xE2: "Associated STA MLD Configuration TLV",
        0xE6: "TID-to-Link Mapping Policy TLV",
        0xE7: "EHT Operations TLV",
        0xEB: "RSN Parameters Configuration TLV",
        0xEC: "BSS Advanced Configuration TLV"
    }
    return tlv_names.get(tlv_type, f"Unknown TLV type: 0x{tlv_type:02X}")

def verify_channel_selection_response_code():
    message_presence = False
    tlv_presence = False
    tlv_value = None

    for pkt in test_logic.reassembled_packets:
        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]

        if message_type == MSG_TYPE_CHANNEL_SELECTION_RESPONSE:
            message_presence = True
            found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)

            for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                if tlv_type == TLV_TYPE_CHANNEL_SELECTION_RESPONSE:
                    tlv_presence = True
                    break
            
            if tlv_presence:
                break

    if not message_presence:
        print_error(f"{get_message_type_name(MSG_TYPE_CHANNEL_SELECTION_RESPONSE)} not found in capture file")
        return False
    
    if not tlv_presence:
        print_error(f"{get_tlv_type_name(TLV_TYPE_CHANNEL_SELECTION_RESPONSE)} TLV not found in {get_message_type_name(MSG_TYPE_CHANNEL_SELECTION_RESPONSE)}")
        return False
    
    # Assuming the first byte of the TLV value represents the response code
    if tlv_value is not None and tlv_value[6] == 0x00:  # 0x00 indicates success
        print_success(f"{get_tlv_type_name(TLV_TYPE_CHANNEL_SELECTION_RESPONSE)} indicates successful channel selection : response code {tlv_value[6]}")
        return True
    else:
        print_error(f"{get_tlv_type_name(TLV_TYPE_CHANNEL_SELECTION_RESPONSE)} does not indicate successful channel selection. Expected response code: 0x00, actual response code: {tlv_value[6] if tlv_value is not None else 'N/A'}")
        return False


def verify_supported_services_tlv():
    message_presence = False
    tlv_presence = False
    tlv_value = None

    for pkt in test_logic.reassembled_packets:
        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]

        if message_type == MSG_TYPE_AP_TOPOLOGY_RESPONSE:
            message_presence = True
            found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)

            for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                if tlv_type == TLV_TYPE_SUPPORTED_SERVICE:
                    tlv_presence = True
                    break
            
            if tlv_presence:
                break

    if not message_presence:
        print_error(f"{get_message_type_name(MSG_TYPE_AP_TOPOLOGY_RESPONSE)} not found in capture file")
        return False
    
    if not tlv_presence:
        print_error(f"{get_tlv_type_name(TLV_TYPE_SUPPORTED_SERVICE)} TLV not found in {get_message_type_name(MSG_TYPE_AP_TOPOLOGY_RESPONSE)}")
        return False
    
    # Assuming the supported services are represented as a bitmask in the TLV value
    # and that bit 0x01 represents a specific service we are interested in.
    if tlv_value is not None and (tlv_value[0] & 0x01):
        print_success(f"{get_tlv_type_name(TLV_TYPE_SUPPORTED_SERVICE)} indicates support for the Multi-AP Agent.")
        return True
    else:
        print_error(f"{get_tlv_type_name(TLV_TYPE_SUPPORTED_SERVICE)} does not indicate support for the Multi-AP Agent.")
        return False

def verify_ssidname_in_topology_response():
    message_presence = False
    ssid_update_flag = False
    text = ""

 
    for pkt in test_logic.reassembled_packets:
        eth = pkt[Ether]
       
        if eth.type != ETHERTYPE_1905:
            continue
       
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]
       
        if MSG_TYPE_AP_TOPOLOGY_RESPONSE == message_type:
            message_presence = True
            found_tlvs, _, tlv_values, _, _ = parse_tlvs(payload)
   
            if TLV_TYPE_AP_OPERATIONAL_BSS not in found_tlvs:
                print_error(f"AP Operational BSS TLV not present")
                return False
        
            else:
                for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                    if tlv_type == TLV_TYPE_AP_OPERATIONAL_BSS:
                        strings = re.findall(rb'[ -~]+', tlv_value)  # printable ASCII
                        for s in strings:
                            text = s.decode()
                            if text == conftest.ssid_name:
                                ssid_update_flag = True
                                print_success(f"SSID name in the AP Operational BSS TLV of the Topology Response message was updated successfully : {text}")
                                return True
    if not message_presence:
        print_error(f"{get_message_type_name(MSG_TYPE_AP_TOPOLOGY_RESPONSE)} not found in capture file")
        return False
    if not ssid_update_flag:
        print_error(f"SSID name in the AP Operational BSS TLV of the Topology Response message is not updated. Expected SSID name: {conftest.ssid_name} Actual SSID name: {text}")            
        return False


def verify_tlv_presence_with_type(requested_message_type, tlv_to_verify, agent_or_controller = ""):
    """
    Verify if a specific TLV type is present in a message
    
    Args:
        filename: path to pcap file
        requested_message_type: CMDU message type to search for
        tlv_to_verify: TLV type to verify presence
    
    Returns:
        True if TLV is found, False otherwise
    """

    msg_type = get_message_type_name(requested_message_type)

    tlv_presence_flag = False
    tlv_length_valid_flag = False
    expected_tlv_length = ""
    message_presence_flag = False
    wsc_msg_type = None
    wsc_msg_type_from_tlv = None


    if agent_or_controller == "agent":
        wsc_msg_type = 0x04

    if agent_or_controller == "controller":
        wsc_msg_type = 0x05

    # print("length of reassembled packets is ", len(test_logic.reassembled_packets))

    for pkt in test_logic.reassembled_packets:
    # for pkt in flow_packets:
        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]
        
        found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)
        

        if message_type == MSG_TYPE_AP_AUTOCONFIG_WSC == requested_message_type:
            for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                if tlv_type == TLV_TYPE_WSC:
                    if wsc_msg_type == tlv_value[9]:
                        wsc_msg_type_from_tlv = tlv_value[9]
                        break

            if wsc_msg_type_from_tlv is None:
                continue

        if requested_message_type == message_type and wsc_msg_type == wsc_msg_type_from_tlv:
            message_presence_flag = True
            # found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)

            for tlv_type, tlv_length, tlv_value in zip(found_tlvs, tlv_length, tlv_values):
                if tlv_type == tlv_to_verify:
                    tlv_presence_flag = True
                    expected_tlv_length, tlv_length_valid_flag = validate_tlv_length(tlv_to_verify, tlv_length)
                else:
                    continue

                if tlv_presence_flag and tlv_length_valid_flag:
                    print_success(f"{get_tlv_type_name(tlv_to_verify)} is present in the {get_message_type_name(requested_message_type)} and the expected tlv length is {expected_tlv_length} and actual tlv length is {tlv_length}")
                    # tlv_flags[tlv_to_verify] = True
                    return True
                
                if tlv_presence_flag and not tlv_length_valid_flag:
                    print_success(f"{get_tlv_type_name(tlv_to_verify)} present in the {get_message_type_name(requested_message_type)}")
                    print_error(f"{get_tlv_type_name(tlv_to_verify)} length is invalid in the {get_message_type_name(requested_message_type)}, expected tlv length is {expected_tlv_length} and actual tlv length is {tlv_length}")
                    return False
            
            if not tlv_presence_flag:
                print_error(f"{get_tlv_type_name(tlv_to_verify)} not found in {get_message_type_name(requested_message_type)}")
                return False

    if not message_presence_flag:
        print_error(f"{get_message_type_name(requested_message_type)}"f"{f' with WSC Message Type {wsc_msg_type}' if agent_or_controller else ''} not found in capture file")
        return False
    
    if not tlv_presence_flag:
        print_error(f"{get_tlv_type_name(tlv_to_verify)} not present in the {get_message_type_name(requested_message_type)}")
        return False
    
    if wsc_msg_type != wsc_msg_type_from_tlv:
        print_error(f"WSC Message Type in WSC TLV does not match expected value for {agent_or_controller}, expected WSC Message Type: {wsc_msg_type}, actual WSC Message Type from WSC TLV: {wsc_msg_type_from_tlv}")
        return False

# ---------------------------------------------------------
# TLV length validation
# ---------------------------------------------------------

def validate_tlv_length(tlv_type, tlv_length):
    """
    Validate TLV length based on spec.

    Returns:
        Tuple of (expected_length: str, is_valid: bool)
    """
    if tlv_type == TLV_TYPE_AL_MAC_ADDRESS:
        return ("6", tlv_length == 6)

    if tlv_type == TLV_TYPE_MAC_ADDRESS:
        return ("6", tlv_length == 6)

    if tlv_type == TLV_TYPE_LINK_METRIC_QUERY:
        return ("41 or more", tlv_length >= 41)

    if tlv_type == TLV_TYPE_TX_LINK_METRIC:
        return ("41 or more", tlv_length >= 41)

    if tlv_type == TLV_TYPE_RX_LINK_METRIC:
        return ("35 or more", tlv_length >= 35)

    if tlv_type == TLV_TYPE_SEARCHED_ROLE:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_AUTOCONFIG_FREQ_BAND:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_SUPPORTED_ROLE:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_SUPPORTED_FREQ_BAND:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_MULTI_AP_PROFILE:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_DEVICE_INFORMATION:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_AP_OPERATIONAL_BSS:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_BSS_CONFIG_REPORT:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_WSC:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_PROFILE_2_AP_CAPABILITY:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES:
        return ("1 or more", tlv_length >= 1)

    if tlv_type == TLV_TYPE_AP_RADIO_IDENTIFIER:
        return ("6", tlv_length == 6)

    if tlv_type == TLV_TYPE_END_OF_TLV:
        return ("0", tlv_length == 0)
    
    if tlv_type == TLV_TYPE_AP_CAPABILITY:
        return ("1", tlv_length == 1)
    
    if tlv_type == TLV_TYPE_CHANNEL_SCAN_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_CAC_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_METRIC_COLLECTION_INTERVAL:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_1905_LAYER_SECURITY_CAPABILITY:
        return ("3", tlv_length == 3)
    
    if tlv_type == TLV_TYPE_DEVICE_INVENTORY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_AP_HT_CAPABILITIES:
        return ("7", tlv_length == 7)

    if tlv_type == TLV_TYPE_AP_VHT_CAPABILITIES:
        return ("12", tlv_length == 12)
    
    if tlv_type == TLV_TYPE_AP_HE_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_AP_WIFI_6_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_SUPPORTED_SERVICE:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_BACKHAUL_STA_RADIO_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_DEFAULT_802_1Q_SETTINGS:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_TRAFFIC_SEPARATION_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_STEERING_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_METRIC_REPORTING_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_CHANNEL_SCAN_REPORTING_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_UNSUCCESSFUL_ASSOCIATION_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_BACKHAUL_BSS_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_QOS_MANAGEMENT_POLICY:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_ERROR_CODE:
        return ("7", tlv_length == 7)

    if tlv_type == TLV_TYPE_CHANNEL_PREFERENCE:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_RADIO_OPERATION_RESTRICTION:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_CAC_COMPLETION_REPORT:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_CAC_STATUS_REPORT:
        return ("greater than 0", tlv_length > 0)
    
    if tlv_type == TLV_TYPE_CHANNEL_SELECTION_RESPONSE:
        return ("7", tlv_length == 7)

    if tlv_type == TLV_TYPE_OPERATING_CHANNEL:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_CLIENT_ASSOCIATION_EVENT:
        return ("13", tlv_length == 13)

    if tlv_type == TLV_TYPE_DEVICE_BRIDGING_CAPABILITY:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_NON_1905_NEIGHBOR_DEVICE_LIST:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_1905_NEIGHBOR_DEVICE_LIST:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_SEARCHED_SERVICE:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_ASSOCIATED_CLIENTS:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_TRANSMIT_POWER_LIMIT:
        return ("7", tlv_length == 7)

    if tlv_type == TLV_TYPE_PROFILE_2_ERROR_CODE:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_DPP_CHIRP_VALUE:
        return ("1", tlv_length == 1)

    if tlv_type == TLV_TYPE_CONTROLLER_CAPABILITY:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_AKM_SUITE_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_SPATIAL_REUSE_CONFIG_RESPONSE:
        return ("7", tlv_length == 7)

    if tlv_type == TLV_TYPE_SPATIAL_REUSE_REQUEST:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_SPATIAL_REUSE_REPORT:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_WIFI_7_AGENT_CAPABILITIES:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_AGENT_AP_MLD_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_BACKHAUL_STA_MLD_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_ASSOCIATED_STA_MLD_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_TID_TO_LINK_MAPPING_POLICY:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_EHT_OPERATIONS:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_RSN_PARAMETERS_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)

    if tlv_type == TLV_TYPE_BSS_ADVANCED_CONFIGURATION:
        return ("greater than 0", tlv_length > 0)
    
    return ("unknown", True)


def verify_relay_indicator_flag_status(requested_message_type, expected_relay_indicator_status):
    msg_type = get_message_type_name(requested_message_type)    
    for pkt in test_logic.reassembled_packets:

        if not pkt.haslayer(Ether):
            continue

        eth = pkt[Ether]

        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)

        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        relay_indicator = 0
        if message_type == requested_message_type:
            relay_indicator = (payload[7] >> 6) & 0x01

            if expected_relay_indicator_status == relay_indicator:
                print_success(f"Expected relay indicator value: {expected_relay_indicator_status}, Actual relay indicator value is {relay_indicator}")
                return True
            else:
                print_error(f"Expected relay indicator value: {expected_relay_indicator_status}, Actual relay indicator value is {relay_indicator}")
                return False

def verify_cmdu_presence(expected_cmdu, agent_or_controller="", expected_count = 1):
    msg_type = get_message_type_name(expected_cmdu)
    message_count = 0

    if agent_or_controller == "agent":
        wsc_msg_type = 0x04
        expected_cmdu_key = f"{expected_cmdu}_agent"

    elif agent_or_controller == "controller":
        wsc_msg_type = 0x05
        expected_cmdu_key = f"{expected_cmdu}_controller"

    else:
        expected_cmdu_key = f"{expected_cmdu}"

    global message_details
    message_details = message_count_details.setdefault(
        expected_cmdu_key, {"message_ids": set()}
    )
    for pkt in test_logic.reassembled_packets:
        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)
        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)
        # Extrat message id from CMDU header for counting specific message types
        message_id = '0x' + payload[4:6].hex().upper()
        if message_type == expected_cmdu:
            if not agent_or_controller:
                message_details["message_ids"].add(message_id)
                message_count += 1
            else:
                for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                    if tlv_type == TLV_TYPE_WSC:
                        if wsc_msg_type == tlv_value[9]:
                            message_details["message_ids"].add(message_id)
                            message_count += 1
            
    # return message_count
    if message_count < expected_count:
        print_error(f"No {msg_type} found between controller {controller_mac} and agent {agent_mac} in capture file {conftest.capture_file_path}")
        check.fail(f"No {msg_type} found between controller {controller_mac} and agent {agent_mac} in capture file {conftest.capture_file_path}")
        return False
    else:
        print_success(f"{msg_type} is present")
        return True
    

def verify_1905_al_mac_address(requested_message_type):
    msg_type = get_message_type_name(requested_message_type)

    for pkt in test_logic.reassembled_packets:

        eth = pkt[Ether]

        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)

        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        if message_type == requested_message_type:          
            found_tlvs, tlv_lengths, tlv_values, end_found, error = parse_tlvs(payload)
            # Extract AL MAC Address
            al_mac = ""
            for tlv_type, tlv_length, tlv_value in zip(found_tlvs, tlv_lengths, tlv_values):
                if tlv_type == TLV_TYPE_AL_MAC_ADDRESS:
                    al_mac = ':'.join(f'{b:02X}' for b in tlv_value)
                    break
            
            if al_mac.lower() == eth.src.lower():
                print_success(f"1905.1 AL MAC Address TLV value matching with transmitter mac, 1905.1 AL MAC Address TLV value: {al_mac.lower()} and transmitter mac: {eth.src.lower()} ")
                return True
            else:
                print_error(f"1905.1 AL MAC Address TLV value not matching with transmitter mac, 1905.1 AL MAC Address TLV value: {al_mac.lower()} and transmitter mac: {eth.src.lower()} ")
                return False

def extract_profile_type_from_autoconfig_response(filename):
    """
    Extract profile type from autoconfiguration response message.
    
    Args:
        filename: path to pcap file
    
    Returns:
        Profile type value if found, None otherwise
    """
    message_presence = False
    tlv_presence = False
    packets = rdpcap(filename)
    
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
           ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"No messages between controller {controller_mac} and agent {agent_mac} found in the capture file.")
        check.fail(f"No messages between controller {controller_mac} and agent {agent_mac} found in the capture file.")
        return None
    
    for pkt in flow_packets:
        eth = pkt[Ether]
        
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]
        
        if message_type == conftest.MSG_TYPE_AP_AUTOCONFIGURATION_RESPONSE:
            message_presence = True
            found_tlvs, _, tlv_values, _, _ = parse_tlvs(payload)
            
            for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                if tlv_type == TLV_TYPE_MULTI_AP_PROFILE:
                    tlv_presence = True
                    # Profile type is typically at offset 0 in AP Radio Basic Capabilities TLV
                    if len(tlv_value) == 1:
                        profile_type = tlv_value[0]
                        if profile_type in [0x01, 0x02, 0x03]:
                            profile_name = get_profile_name(profile_type)
                            print_success(f"Profile type extracted: 0x{profile_type:02X} ({profile_name})")
                            return profile_type
                        else:
                            print_error(f"Profile type extracted: 0x{profile_type:02X} (Unknown profile type)")
                            pytest.fail(f"Profile type extracted: 0x{profile_type:02X} (Unknown profile type)", pytrace=False)
                    else:
                        print_error("Multi-AP Profile TLV found but length is insufficient to extract profile type")
                        pytest.fail("Multi-AP Profile  TLV found but length is insufficient to extract profile type", pytrace=False)
    
    if not message_presence:
        print_error("AP Autoconfiguration Response message not found in the capture file.")
        pytest.fail("AP Autoconfiguration Response message not found in the capture file", pytrace=False)
    if not tlv_presence:
        print_error("Multi-AP Profile TLV not found in AP Autoconfiguration Response message.")
        pytest.fail("Multi-AP Profile TLV not found in AP Autoconfiguration Response message", pytrace=False)


def verify_no_additional_tlvs(message_type, mandatory_tlvs, optional_tlvs, agent_or_controller=None):
    """
    Check for additional TLVs in a message beyond the mandatory ones.

    Input:
        filename (str): Path to pcap file
        message_type (int): CMDU message type to search for
        mandatory_tlvs (set): Set of mandatory TLV types
        optional_tlvs (set): Set of optional TLV types

    Returns:
        additional_tlvs (set): Set of additional TLV types found beyond mandatory ones, or empty if none found
    """

    if agent_or_controller == "agent":
        wsc_msg_type = 0x04

    if agent_or_controller == "controller":
        wsc_msg_type = 0x05
    
    for pkt in test_logic.reassembled_packets:
        eth = pkt[Ether]
        
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        msg_type = (payload[2] << 8) | payload[3]


        if message_type == msg_type == MSG_TYPE_AP_AUTOCONFIG_WSC:
            found_tlvs, tlv_length, tlv_values, _, _ = parse_tlvs(payload)
            wsc_msg_type_from_tlv = None
            for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                if tlv_type == TLV_TYPE_WSC:
                    if wsc_msg_type == tlv_value[9]: #verifying WSC Message is M1 or M2
                        found_set = set(found_tlvs)
                        mandatory_set = set(mandatory_tlvs)
                        optional_set = set(optional_tlvs)
                        extra_tlvs = found_set - mandatory_set - optional_set

                        if extra_tlvs:
                            extra_tlvs_list = [f"{get_tlv_type_name(tlv)} (0x{tlv:02X})" for tlv in sorted(extra_tlvs)]
                            print_error(f" Found Extra TLVs (neither mandatory nor optional) in {get_message_type_name(message_type)}: {extra_tlvs_list}")
                            return False
                        else:
                            print_success(f"No extra TLVs found beyond mandatory and optional tlvs in {get_message_type_name(message_type)}.")
                            return True
            
        
        if message_type == msg_type and message_type != MSG_TYPE_AP_AUTOCONFIG_WSC:
            found_tlvs, _, _, _, _ = parse_tlvs(payload)
            found_set = set(found_tlvs)
            mandatory_set = set(mandatory_tlvs)
            optional_set = set(optional_tlvs)
            
            extra_tlvs = found_set - mandatory_set - optional_set
            
            if extra_tlvs:
                extra_tlvs_list = [f"{get_tlv_type_name(tlv)} (0x{tlv:02X})" for tlv in sorted(extra_tlvs)]
                print_error(f" Found Extra TLVs (neither mandatory nor optional) in {get_message_type_name(message_type)}: {extra_tlvs_list}")
                return False
            else:
                print_success(f"No extra TLVs found beyond mandatory and optional tlvs in {get_message_type_name(message_type)}.")
                return True
            

def validate_supported_role(expected_role):
    for pkt in test_logic.reassembled_packets:

        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)

        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        if message_type == MSG_TYPE_AP_AUTOCONFIGURATION_RENEW:            
            found_tlvs, tlv_lengths, tlv_values, end_found, error = parse_tlvs(payload)
            for tlv_type, tlv_length, tlv_value in zip(found_tlvs, tlv_lengths, tlv_values):
                if tlv_type == TLV_TYPE_SUPPORTED_ROLE:
                    if tlv_value == bytes([expected_role]):
                        print_success(f"Supported Role TLV found with expected value: 0x{expected_role:02X}")
                        return True
                    else:
                        print_error(f"expected Supported Role value: 0x{expected_role:02X}, actual Supported Role value: 0x{tlv_value[0]:02X}")
                        return False



def validate_1905_message(config, profiletype, message, controller_or_agent = None):
    """
    Validate a 1905 message against expected mandatory and optional TLVs based on profile and message type.

    Args:
        config: Configuration dictionary loaded from YAML
        profiletype: Multi-AP profile type (1, 2, or 3)
        message: CMDU message type to validate
        controller_or_agent (str, optional): Specify "controller" or "agent" to validate

    Returns: None. Prints validation results and errors.
    """
    #setting tlv flags to false before validation
    # for tlv in tlv_flags:
    #     tlv_flags[tlv] = False
    message_type_string = get_message_type_name(message)

    if controller_or_agent == "controller":
        mandatory = config["profiles"][profiletype][message]["controller_tlvs"]["mandatory_tlvs"]
        optional = config["profiles"][profiletype][message]["controller_tlvs"]["optional_tlvs"]
    elif controller_or_agent == "agent":
        mandatory = config["profiles"][profiletype][message]["agent_tlvs"]["mandatory_tlvs"]
        optional = config["profiles"][profiletype][message]["agent_tlvs"]["optional_tlvs"]
    else:
        mandatory = config["profiles"][profiletype][message]["mandatory_tlvs"]
        optional = config["profiles"][profiletype][message]["optional_tlvs"]
    
    # if not mandatory and not optional:
    #     print_completed_step(f"{message_type_string}"+(f" from {controller_or_agent}" if controller_or_agent else ""))
    #     return True

    if not mandatory:
        print_warning(f"No mandatory TLVs defined for {message_type_string} in the profile. Skipping mandatory TLV presence verification.")
    else:
        for index, tlv in enumerate(mandatory, start=1):
            tlv_type_string = get_tlv_type_name(tlv)
            print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+f" to verify the presence of the {tlv_type_string}")
            if controller_or_agent:
                tlv_validation_result = verify_tlv_presence_with_type(message, tlv, controller_or_agent)
                check.equal(tlv_validation_result, True, f"\nFail: Expected TLV type '{tlv_type_string}' not found in {message_type_string}.")
            else:
                tlv_validation_result = verify_tlv_presence_with_type(message, tlv)
                check.equal(tlv_validation_result, True, f"\nFail: Expected TLV type '{tlv_type_string}' not found in {message_type_string}.")

            if conftest.VALIDATION_LEVEL >= 3 and tlv_validation_result:

                if message in [MSG_TYPE_AP_AUTOCONFIG_SEARCH, MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, MSG_TYPE_TOPOLOGY_NOTIFICATION, MSG_TYPE_TOPOLOGY_DISCOVERY] and tlv == TLV_TYPE_AL_MAC_ADDRESS:
                    print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+" Validate that the value of the IEEE 1905.1 AL MAC Address TLV matches the transmitter MAC address.")
                    check.equal(verify_1905_al_mac_address(message), True, "\nFail: 1905.1 AL MAC Address TLV presence and value validation failed in captured packets.")

                if message == MSG_TYPE_AP_AUTOCONFIGURATION_RENEW and tlv == TLV_TYPE_SUPPORTED_ROLE:
                        print_sub_step(f"Analyzing the {message_type_string} for supported role value validation")
                        check.equal(validate_supported_role(0x00), True, f"\nFail: Supported Role TLV value is not valid in captured packets for {message_type_string}.")

        print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+" to check for any unexpected TLVs that are not defined as mandatory or optional in the profile")
        if controller_or_agent:
            check.equal(verify_no_additional_tlvs(message, mandatory, optional, controller_or_agent), True, f"\nFail: Extra TLVs found in {message_type_string} from {controller_or_agent} that are not listed as mandatory or optional in the profile definition.")
        else:
            check.equal(verify_no_additional_tlvs(message, mandatory, optional), True, f"\nFail: Extra TLVs found in {message_type_string} that are not listed as mandatory or optional in the profile definition.")

    # if not optional:
    #     print_warning(f"No optional TLVs defined for {message_type_string} in the profile. Skipping optional TLV presence verification.")
    # else:
    #     print_warning(f" Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+f" to verify the presence of optional TLVs")
    #     for index, tlv in enumerate(optional, start=1):
    #         tlv_type_string = get_tlv_type_name(tlv)
    #         print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+f" to verify the presence of the optional TLV: {tlv_type_string}")
    #         if controller_or_agent:
    #             check.equal(verify_tlv_presence_with_type(message, tlv, controller_or_agent), True, f"\nFail: Expected optional TLV type '{tlv_type_string}' not found in {message_type_string}.")
    #         else:
    #             check.equal(verify_tlv_presence_with_type(message, tlv), True, f"\nFail: Expected optional TLV type '{tlv_type_string}' not found in {message_type_string}.")
    #     print_warning(f"Completed analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+" to verify the presence of optional TLVs")

    if conftest.VALIDATION_LEVEL >= 3:

        if message in [MSG_TYPE_TOPOLOGY_NOTIFICATION, MSG_TYPE_AP_AUTOCONFIG_RENEW, MSG_TYPE_AP_AUTOCONFIG_SEARCH]:
            print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+" to verify the presence of the expected relay indicator flag status in the message")
            check.equal(verify_relay_indicator_flag_status(message, 1), True, "\nFail: Expected relay indicator flag status not found in captured packets.")
        else:
            check.equal(verify_relay_indicator_flag_status(message, 0), True, "\nFail: Expected relay indicator flag status not found in captured packets.")

        # if message in [MSG_TYPE_AP_AUTOCONFIG_SEARCH, MSG_TYPE_AP_AUTOCONFIGURATION_RENEW, MSG_TYPE_TOPOLOGY_NOTIFICATION, MSG_TYPE_TOPOLOGY_DISCOVERY]:
        #     print_sub_step(f"Analyzing the {message_type_string}" +(f" from {controller_or_agent}" if controller_or_agent else "")+" to verify the presence of the 1905.1 AL MAC Address TLV and validate the value of the TLV to match with transmitter mac address")
        #     check.equal(verify_1905_al_mac_address(message), True, "\nFail: 1905.1 AL MAC Address TLV presence and value validation failed in captured packets.")

        # if message == MSG_TYPE_AP_AUTOCONFIGURATION_RENEW:
        #     if tlv_flags[TLV_TYPE_SUPPORTED_ROLE]:
        #         print_sub_step(f"Analyzing the {message_type_string} for supported role value validation")
        #         check.equal(validate_supported_role(0x00), True, f"\nFail: Supported Role TLV value is not valid in captured packets for {message_type_string}.")



