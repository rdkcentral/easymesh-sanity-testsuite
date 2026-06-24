import conftest
from scapy.all import rdpcap, Ether
import message_verify
import pytest
import pytest_check as check
from scapy.plist import PacketList
from ieee1905_utils import print_completed_step, print_success, print_error, print_step, print_warning, print_main_step, print_sub_step
from ieee1905_utils import *

controller_mac = conftest.controller_mac
agent_mac = conftest.agent_mac

fragment_store = {}
header_1905 = ""
ETHERTYPE_1905 = 0x893A
reassembled_packets = PacketList()


def packet_parser(flow_packets):
    
    global header_1905
    for pkt in flow_packets:
        if not pkt.haslayer(Ether):
            continue
        eth = pkt[Ether]
        if eth.type != ETHERTYPE_1905:
            continue

        payload = bytes(eth.payload)
        # Extract fields from CMDU header
        message_type = (payload[2] << 8) | payload[3]
        message_id   = (payload[4] << 8) | payload[5]

        fragment_id = payload[6]
        last_fragment = (payload[7] >> 7) & 0x01

        # Improved key
        key = (eth.src, message_type, message_id)

        # Case 1: Not fragmented
        if fragment_id == 0 and last_fragment == 1:
            reassembled_packets.append(pkt)
            #process_complete_message(message_type, payload, eth)
            continue
        # Extract and store 1905 header (first 8 bytes)
        if not header_1905:
            header_1905 = bytearray(payload[:8])
            header_1905[7] = 0x80

        payload = payload[8:]
        # Case 2: Fragmented packet
        if key not in fragment_store:
            fragment_store[key] = []

        fragment_store[key].append((fragment_id, payload))
        # Case 3: Last fragment received
        if last_fragment == 1:
            fragments = fragment_store[key]
            # Sort fragments by fragment id
            fragments.sort(key=lambda x: x[0])
            # Combine payloads
            reassembled = header_1905 + b''.join([f[1] for f in fragments])
            header_1905 = ""
            # Store reassembled frame as a proper Ethernet packet so downstream
            # code can safely access Ether fields (src/dst/type).
            reassembled_pkt = Ether(dst=eth.dst, src=eth.src, type=ETHERTYPE_1905) / bytes(reassembled)
            reassembled_packets.append(reassembled_pkt)
            # Clear buffer
            del fragment_store[key]


def get_profile_details():

    packets = rdpcap(conftest.capture_file_path)
    # Step 1: Filter packets between controller and agent
    flow_packets = [
        pkt for pkt in packets
        if pkt.haslayer(Ether) and
           ((pkt[Ether].src == controller_mac.lower() and pkt[Ether].dst == agent_mac.lower()) or
            (pkt[Ether].src == agent_mac.lower() and pkt[Ether].dst == controller_mac.lower()))
    ]

    if not flow_packets:
        print_error(f"No messages between controller {controller_mac} and agent {agent_mac} found in the capture file.")
        pytest.fail(f"No messages between controller {controller_mac} and agent {agent_mac} found in the capture file.", pytrace=False)

    # print(f"Total packets in flow: {len(flow_packets)}")
    packet_parser(flow_packets)
    print(f"Total packets in flow: {len(reassembled_packets)}")
    print_main_step("Trying to extract profile type from AP Autoconfiguration Response message in captured packets")
    profiletype = message_verify.extract_profile_type_from_autoconfig_response(conftest.capture_file_path)
    config_data = message_verify.load_yaml("config_ver6.yaml")
    return profiletype, config_data
    
def test_ap_configuration_renew():
    validation_level = conftest.VALIDATION_LEVEL
    wsc_m1_message_ids = set()
    profiletype, config_data = get_profile_details()
    print_main_step("Validating AP Autoconfiguration Renew message")
    print_sub_step("verifying AP Autoconfiguration Renew message presence in captured packets")
    message_presence_flag = message_verify.verify_cmdu_presence(conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW)
    if not message_presence_flag:
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW)}")
    else:
        renew_message_details = message_verify.message_count_details.setdefault(
            conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW,
            {"message_ids": set()}
        )
        renew_message_ids = renew_message_details["message_ids"]
        print_sub_step("validating AP Autoconfiguration Renew message count")
        if len(renew_message_ids) == 1:
            print_success(f"AP Autoconfiguration Renew message present with a single unique message ID, as expected : {renew_message_ids}")
        else:
            print_error(f"AP Autoconfiguration Renew message count validation failed. Expected 1 AP Autoconfiguration Renew message or multiple with the same message ID, current Message IDs: {sorted(renew_message_ids)}")   
        if validation_level >= 2:
            message_verify.validate_1905_message(config_data, profiletype, conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW)
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_RENEW)}")

    
    print_main_step("Validating AP Autoconfiguration WSC M1 message")
    print_sub_step("verifying AP Autoconfiguration WSC M1 message presence in captured packets")
    message_presence_flag = message_verify.verify_cmdu_presence(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, "agent")
    if not message_presence_flag:
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC)} with WSC M1")
    else:
        wsc_m1_message_details = message_verify.message_count_details.setdefault(
            f"{conftest.MSG_TYPE_AP_AUTOCONFIG_WSC}_agent",
            {"message_ids": set()}
        )
        wsc_m1_message_ids = wsc_m1_message_details["message_ids"]
        print_sub_step("validating AP Autoconfiguration WSC M1 message count")
        if len(wsc_m1_message_ids) == conftest.agent_front_radio_count:
            print_success(f"AP Autoconfiguration WSC M1 message count is : {len(wsc_m1_message_ids)} , which is expected as per the number of front radios in the agent, which is {conftest.agent_front_radio_count}")
        else:
            print_error(f"AP Autoconfiguration WSC M1 message count validation failed. Expected {conftest.agent_front_radio_count} AP Autoconfiguration WSC M1 messages, Actual AP Autoconfiguration WSC M1 message count : {len(wsc_m1_message_ids)}")   
        if validation_level >= 2:
            # if we need to validate all the WSC M1 messages, we can loop through the frames and validate each one. For now, we will validate the first one.
            message_verify.validate_1905_message(config_data, profiletype, conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, "agent")
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC)} with WSC M1")


    print_main_step("Validating AP Autoconfiguration WSC M2 message")
    print_sub_step("verifying AP Autoconfiguration WSC M2 message presence in captured packets")
    message_presence_flag = message_verify.verify_cmdu_presence(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, "controller")
    if not message_presence_flag:
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC)} with WSC M2")
    else:
        wsc_m2_message_details = message_verify.message_count_details.setdefault(
            f"{conftest.MSG_TYPE_AP_AUTOCONFIG_WSC}_controller",
            {"message_ids": set()}
        )
        wsc_m2_message_ids = wsc_m2_message_details["message_ids"]
        print_sub_step("validating AP Autoconfiguration WSC M2 message count")
        if len(wsc_m2_message_ids) == len(wsc_m1_message_ids):
            print_success(f"AP Autoconfiguration WSC M2 message count is : {len(wsc_m2_message_ids)}, which is expected to be same as the number of AP Autoconfiguration WSC M1 messages, which is {len(wsc_m1_message_ids)}")
        else:
            print_error(f"AP Autoconfiguration WSC M2 message count validation failed. Expected {len(wsc_m1_message_ids)} AP Autoconfiguration WSC M2 messages, Actual AP Autoconfiguration WSC M2 message count : {len(wsc_m2_message_ids)}")   
        if validation_level >= 2:
            message_verify.validate_1905_message(config_data, profiletype, conftest.MSG_TYPE_AP_AUTOCONFIG_WSC, "controller")
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_AUTOCONFIG_WSC)} with WSC M2")


    print_main_step("Validating Topology Response message")
    print_sub_step("verifying Topology Response message presence in captured packets")
    message_presence_flag = message_verify.verify_cmdu_presence(conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE)
    if not message_presence_flag:
        print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE)}")
    else:
        if validation_level >= 2:
            message_verify.validate_1905_message(config_data, profiletype, conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE)
        if validation_level >= 3:
            print_sub_step("validating updated SSID name presence in Topology Response message")
            message_verify.verify_ssidname_in_topology_response()
            print_sub_step("verifying supported services TLV value")
            message_verify.verify_supported_services_tlv()
    print_completed_step(f"{message_verify.get_message_type_name(conftest.MSG_TYPE_AP_TOPOLOGY_RESPONSE)}")
    
