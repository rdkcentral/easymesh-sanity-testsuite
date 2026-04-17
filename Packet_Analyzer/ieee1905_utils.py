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

"""
ieee1905_utils.py

Reusable utility library for IEEE 1905.1 / EasyMesh frame validation.

Provides functions for:
- Multicast validation
- TLV parsing
- Mandatory TLV validation
- TLV length validation
"""

# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

# IEEE 1905.1 Control Multicast Address
IEEE1905_CONTROL_ADDRESS = "01:80:c2:00:00:13"

# TLV Types
TLV_TYPE_END_OF_MESSAGE = 0x00

# Example TLV Types
# TLV Types
TLV_TYPE_AL_MAC_ADDRESS = 0x01
TLV_TYPE_MAC_ADDRESS = 0x02
TLV_TYPE_LINK_METRIC_QUERY = 0x08
TLV_TYPE_TX_LINK_METRIC = 0x09
TLV_TYPE_RX_LINK_METRIC = 0x0A
TLV_TYPE_SEARCHED_ROLE = 0x0D
TLV_TYPE_AUTOCONFIG_FREQ_BAND = 0x0E
TLV_TYPE_SUPPORTED_ROLE = 0x0F
TLV_TYPE_SUPPORTED_FREQ_BAND = 0x10
TLV_TYPE_MULTI_AP_PROFILE = 0xB3
TLV_TYPE_DEVICE_INFORMATION = 0x03
TLV_TYPE_AP_OPERATIONAL_BSS = 0x83
TLV_TYPE_BSS_CONFIG_REPORT = 0xB7
TLV_TYPE_WSC = 0x11
TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES = 0x85
TLV_TYPE_PROFILE_2_AP_CAPABILITY = 0xB4
TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES = 0xBE
TLV_TYPE_AP_RADIO_IDENTIFIER = 0x82
TLV_TYPE_END_OF_TLV = 0x00


MANDATORY_TLVS_AP_AUTOCONFIG_SEARCH = {
    TLV_TYPE_AL_MAC_ADDRESS,
    TLV_TYPE_SEARCHED_ROLE,
    TLV_TYPE_AUTOCONFIG_FREQ_BAND,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_AP_AUTOCONFIG_RESPONSE = {
    TLV_TYPE_SUPPORTED_ROLE,
    TLV_TYPE_SUPPORTED_FREQ_BAND,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_AP_AUTOCONFIG_RENEW = {
    TLV_TYPE_AL_MAC_ADDRESS,
    TLV_TYPE_SUPPORTED_ROLE,
    TLV_TYPE_SUPPORTED_FREQ_BAND,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_TOPOLOGY_QUERY = {
    TLV_TYPE_MULTI_AP_PROFILE,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_TOPOLOGY_DISCOVERY = {
    TLV_TYPE_AL_MAC_ADDRESS,
    TLV_TYPE_MAC_ADDRESS,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_TOPOLOGY_NOTIFICATION = {
    TLV_TYPE_AL_MAC_ADDRESS,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_LINK_METRIC_QUERY = {
    TLV_TYPE_LINK_METRIC_QUERY,
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_LINK_METRIC_RESPONSE = {
    TLV_TYPE_END_OF_TLV,
}

MANDATORY_TLVS_AUTOCONFIG_WSC_AGENT = {
    TLV_TYPE_WSC,
    TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES,
    TLV_TYPE_PROFILE_2_AP_CAPABILITY,
    TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES,
    TLV_TYPE_END_OF_TLV,
}


MANDATORY_TLVS_AUTOCONFIG_WSC_CONTROLLER = {
    TLV_TYPE_WSC,
    TLV_TYPE_AP_RADIO_IDENTIFIER,
    TLV_TYPE_END_OF_TLV,
    0x75,
}


MANDATORY_TLVS_TOPOLOGY_RESPONSE = {
    TLV_TYPE_DEVICE_INFORMATION,
    TLV_TYPE_MULTI_AP_PROFILE,
    TLV_TYPE_AP_OPERATIONAL_BSS,
    TLV_TYPE_BSS_CONFIG_REPORT,
    TLV_TYPE_END_OF_TLV,
}

def print_error(message):
    print(f"\033[91mFAIL: {message}\033[0m")  # Red text\
    #return f'<b style="color:red">FAIL: {message}</b>'
    return f'<span style="color:red; font-weight:bold;">FAIL: {message}</span>'

# ---------------------------------------------------------
# Multicast validation
# ---------------------------------------------------------

def is_multicast_message(eth):
    """
    Check whether frame destination is IEEE1905 multicast.

    Input:
        eth (scapy Ether object)

    Returns:
        True or False
    """

    dst_mac = eth.dst.lower()
    return dst_mac == IEEE1905_CONTROL_ADDRESS

def check_al_mac_address(eth, al_mac):
    src_mac = eth.src.lower()
    if src_mac == al_mac.lower():
        return True
    else:
        return False


# ---------------------------------------------------------
# Mandatory TLV validation
# ---------------------------------------------------------

def validate_tlvs(expected_tlvs, found_tlvs):
    """
    Check if all mandatory TLVs are present.

    Input:
        expected_tlvs (set): Set of mandatory TLV types.
        found_tlvs (list): List of found TLV types.

    Returns:
        missing_tlvs (set): Set of missing TLV types.
    """
    found_set = set(found_tlvs)

    missing_tlvs = expected_tlvs - found_set
    extra_tlvs = found_set - expected_tlvs
    if missing_tlvs:
        missing_hex = [f"0x{tlv:02X}" for tlv in missing_tlvs]
        print_error(f" Missing mandatory TLVs: {missing_hex}")

    if extra_tlvs:
        extra_hex = [f"0x{tlv:02X}" for tlv in extra_tlvs]
        print_error(f" Found Extra TLVs: {extra_hex}")

    return missing_tlvs, extra_tlvs


# ---------------------------------------------------------
# TLV length validation
# ---------------------------------------------------------

def validate_tlv_length(tlv_type, tlv_length):
    """
    Validate TLV length based on spec.

    Returns:
        True or False
    """

    if tlv_type == TLV_TYPE_AL_MAC_ADDRESS and tlv_length != 6:
        return False

    if tlv_type == TLV_TYPE_MAC_ADDRESS and tlv_length != 6:
        return False

    if tlv_type == TLV_TYPE_LINK_METRIC_QUERY and tlv_length < 41:
        return False

    if tlv_type == TLV_TYPE_TX_LINK_METRIC and tlv_length < 41:
        return False

    if tlv_type == TLV_TYPE_RX_LINK_METRIC and tlv_length < 35:
        return False

    if tlv_type == TLV_TYPE_SEARCHED_ROLE and tlv_length != 1:
        return False

    if tlv_type == TLV_TYPE_AUTOCONFIG_FREQ_BAND and tlv_length != 1:
        return False

    if tlv_type == TLV_TYPE_SUPPORTED_ROLE and tlv_length != 1:
        return False

    if tlv_type == TLV_TYPE_SUPPORTED_FREQ_BAND and tlv_length != 1:
        return False

    if tlv_type == TLV_TYPE_MULTI_AP_PROFILE and tlv_length != 1:
        return False

    if tlv_type == TLV_TYPE_DEVICE_INFORMATION and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_AP_OPERATIONAL_BSS and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_BSS_CONFIG_REPORT and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_WSC and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_AP_RADIO_BASIC_CAPABILITIES and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_PROFILE_2_AP_CAPABILITY and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_AP_RADIO_ADVANCED_CAPABILITIES and tlv_length < 1:
        return False
    
    if tlv_type == TLV_TYPE_AP_RADIO_IDENTIFIER and tlv_length != 6:
        return False

    if tlv_type == TLV_TYPE_END_OF_TLV and tlv_length != 0:
        return False

    return True


# ---------------------------------------------------------
# TLV parser
# ---------------------------------------------------------

def parse_tlvs(payload):
    """
    Parse TLVs from IEEE1905 payload.

    Input:
        payload (bytes)

    Returns:
        found_tlvs (list)
        tlv_lengths (list)
        tlv_values (list)
        end_of_message_found (bool)
        error (None or string)
    """

    tlv_start = 8
    current_position = tlv_start

    found_tlvs = []  # Changed from set to list to preserve order
    tlv_lengths = []
    tlv_values = []  # New list to store TLV values
    found_end_of_message = False

    while current_position < len(payload):

        # Check TLV header size
        if current_position + 3 > len(payload):
            return None, None, None, False, "Incomplete TLV header"

        tlv_type = payload[current_position]
        tlv_length = (payload[current_position + 1] << 8) | payload[current_position + 2]

        # Extract TLV value
        tlv_value_start = current_position + 3
        tlv_value_end = tlv_value_start + tlv_length
        if tlv_value_end > len(payload):
            return None, None, None, False, "Incomplete TLV value"

        tlv_value = payload[tlv_value_start:tlv_value_end]

        found_tlvs.append(tlv_type)  # Append to list to preserve order
        tlv_lengths.append(tlv_length)
        tlv_values.append(tlv_value)  # Append TLV value

        # Check End of Message
        if tlv_type == TLV_TYPE_END_OF_MESSAGE:
            found_end_of_message = True
            break

        current_position += 3 + tlv_length

    return found_tlvs, tlv_lengths, tlv_values, found_end_of_message, None
