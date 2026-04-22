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

from scapy.all import rdpcap, Ether
from UI_Automation.conftest import *
from UI_Automation.utils import *
from ieee1905_utils import *
import re

ETHERTYPE_1905 = 0x893A
#TODO IMPLEMENT ACTUAL LOGIC FOR number_of_agents and supported_bands_of_controller
#number_of_agents = 1
#supported_bands_of_controller = 3

#MSG_TYPE_AP_AUTOCONFIGURATION_RENEW = 0x000A
#MSG_TYPE_AP_TOPOLOGY_QUERY = 0x0002
#MSG_TYPE_AP_TOPOLOGY_RESPONSE = 0x0003
#MSG_TYPE_AP_AUTOCONFIG_WSC = 0x0009
#MSG_TYPE_AP_AUTOCONFIG_RENEW = 0x000A
#MSG_TYPE_TOPOLOGY_DISCOVERY = 0x0000
#CMDU_AP_ERROR = 0x0055

fragment_store = {}
m1_message_store = {}
header_1905 = ""

global controller_mac
global agent_mac
controller_mac = None
agent_mac = None

#########################################################
# EXPECTED_SEQUENCE = ["0x000a", "0x0009", "0x0009"]

# def validate_sequence(filename):
#     """
#     filename: path to pcap file
#     """

#     global controller_mac
#     global agent_mac

#     packets = rdpcap(filename)

#     # Step 1: Filter packets between controller and agent
#     flow_packets = [
#         pkt for pkt in packets
#         if pkt.haslayer(Ether) and
#            ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
#             (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
#     ]

#     # Step 2: Extract only relevant message types
#     sequence = []
#     for pkt in flow_packets:

#         eth = pkt[Ether]

#         if eth.type != ETHERTYPE_1905:
#             continue

#         payload = bytes(eth.payload)

#         # Extract fields from CMDU header
#         message_type = (payload[2] << 8) | payload[3]

#         if message_type == 0x000a:
#             sequence.append("0x000a")
#         elif message_type == 0x0009:
#             sequence.append("0x0009")

#     # Step 3: Validate order
#     expected_index = 0

#     print(f"============== {len(EXPECTED_SEQUENCE)}")

#     for msg in sequence:
#         print(f"====>{msg}")
#         # if msg == EXPECTED_SEQUENCE[expected_index]:
#         #     expected_index += 1
#         #     # If full sequence matched
#         #     if expected_index == len(EXPECTED_SEQUENCE):
#         #         expected_index = 0
#         # else:
#         #     return False
            
#     return True

#########################################################

def get_message_type_name(message_type):
    """
    Convert hex message type to human-readable string
    """
    message_names = {
        0x000A: "AP Autoconfiguration Renew message",
        0x0009: "AP Autoconfig WSC message",
        0x0002: "Topology Query Message",
        0x0003: "Topology Response Message",
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
        0x08: "Link Metric Query TLV",
        0x09: "Transmitter Link Metric TLV",
        0x0A: "Receiver Link Metric TLV",
        0x0D: "Searched Role TLV",
        0x0E: "Autoconfig Frequency Band TLV",
        0x0F: "Supported Role TLV",
        0x10: "Supported Frequency Band TLV",
        0x11: "WSC TLV",
        0x82: "AP Radio Identifier TLV",
        0x83: "AP Operational BSS TLV",
        0x85: "AP Radio Basic Capabilities TLV",
        0xB3: "Multi-AP Profile TLV",
        0xB4: "Profile 2 AP Capability TLV",
        0xB7: "BSS Config Report TLV",
        0xBE: "AP Radio Advanced Capabilities TLV",
    }
    return tlv_names.get(tlv_type, f"Unknown TLV type: 0x{tlv_type:02X}")

def verify_ssidname_in_topology_response(filename, ssid_name):
    found_tlvs = ""
    tlv_values = ""
    packets = rdpcap(filename)
   
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
            ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]
 
    if not flow_packets:
        print_error(f"Topology Response Message Not Present")
        return False
 
    for pkt in flow_packets:
        eth = pkt[Ether]
       
        if eth.type != ETHERTYPE_1905:
            continue
       
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]
       
        if MSG_TYPE_AP_TOPOLOGY_RESPONSE == message_type:
            # print(payload.hex())
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
                    if text == ssid_name:
                        print_success(f"SSID name in the AP Operational BSS TLV of the Topology Response message was updated successfully : {text}")
                        return True     
    print_error(f"SSID name in the AP Operational BSS TLV of the Topology Response message was not updated successfully")              
    return False

def verify_tlv_presence_with_type(filename, requested_message_type, tlv_to_verify, wsc_type=0x04):
    """
    Verify if a specific TLV type is present in a message
    
    Args:
        filename: path to pcap file
        requested_message_type: CMDU message type to search for
        tlv_to_verify: TLV type to verify presence
        wsc_type: WSC message type to filter on (default: 1)
    
    Returns:
        True if TLV is found, False otherwise
    """

    msg_type = get_message_type_name(requested_message_type)
    packets = rdpcap(filename)
    
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
            ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"{msg_type} Not Present")
        return False
    
    for pkt in flow_packets:
        eth = pkt[Ether]
        
        if eth.type != ETHERTYPE_1905:
            continue
        
        payload = bytes(eth.payload)
        message_type = (payload[2] << 8) | payload[3]
        
        if requested_message_type == message_type:
            found_tlvs, _, tlv_values, _, _ = parse_tlvs(payload)
            
            # Filter by wsc_type if message is WSC
            if requested_message_type == MSG_TYPE_AP_AUTOCONFIG_WSC:
                for tlv_type, tlv_value in zip(found_tlvs, tlv_values):
                    if tlv_type == TLV_TYPE_WSC and tlv_value[9] == wsc_type:
                        if tlv_to_verify in found_tlvs:
                            print_success(f"{get_tlv_type_name(tlv_to_verify)} present in the {get_message_type_name(requested_message_type)}")
                            return True
            else:
                if tlv_to_verify in found_tlvs:
                    print_success(f"{get_tlv_type_name(tlv_to_verify)} present in the {get_message_type_name(requested_message_type)}")
                    return True

    
    print_error(f"{get_tlv_type_name(tlv_to_verify)} not present in the {get_message_type_name(requested_message_type)}")
    return False




def verify_relay_indicator_flag_status(filename, requested_message_type):

    msg_type = get_message_type_name(requested_message_type)
    packets = rdpcap(filename)

    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
           ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"{msg_type} Not Present")
        return False

    for pkt in flow_packets:

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

            if not relay_indicator:
                print_error("Relay indicator flag is 0")
                return False
            else:
                print_success("Relay indicator flag is 1")
                return True

def verify_cmdu_presence(filename, expected_cmdu, expected_count = 0):
    msg_type = get_message_type_name(expected_cmdu)
    message_count = 0

    packets = rdpcap(filename)
    # Step 1: Filter packets between controller and agent
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
           ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"{msg_type} Not Present")
        return False

    for pkt in flow_packets:

        eth = pkt[Ether]

        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)

        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]

        if message_type == expected_cmdu:
            message_count += 1

    # return message_count
    if message_count < expected_count:
        print_error(f" number of {msg_type} : {message_count} Expected count : {expected_count}")
        return False
    else:
        print_success(f"{msg_type} is present")
        return True
    

def verify_change_from_topology_response(file):
    #TODO
    return "private_prasad"

def verify_1905_al_mac_address(filename, requested_message_type):
    msg_type = get_message_type_name(requested_message_type)
    packets = rdpcap(filename)
    # Step 1: Filter packets between controller and agent
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
           ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"{msg_type} Not Present")
        return False

    for pkt in flow_packets:

        eth = pkt[Ether]

        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)

        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        if message_type == requested_message_type: 
            print(f"Message type: 0x{message_type:04X}")           
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
