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
TLV_TYPE_AP_CAPABILITY = 0xA1
TLV_TYPE_ERROR_CODE = 0xA3
TLV_TYPE_CHANNEL_PREFERENCE = 0x8B
TLV_TYPE_RADIO_OPERATION_RESTRICTION = 0x8C
TLV_TYPE_TRANSMIT_POWER_LIMIT = 0x8D
TLV_TYPE_CHANNEL_SELECTION_RESPONSE = 0x8E
TLV_TYPE_OPERATING_CHANNEL = 0x8F
TLV_TYPE_CAC_COMPLETION_REPORT = 0xAF
TLV_TYPE_CAC_STATUS_REPORT = 0xB1
TLV_TYPE_CHANNEL_SCAN_CAPABILITIES = 0xA5
TLV_TYPE_DEVICE_INVENTORY = 0xD4
TLV_TYPE_METRIC_COLLECTION_INTERVAL = 0xC5
TLV_TYPE_CAC_CAPABILITIES = 0xB2
TLV_TYPE_1905_LAYER_SECURITY_CAPABILITY = 0xA9
TLV_TYPE_CLIENT_ASSOCIATION_EVENT = 0x92
TLV_TYPE_DEVICE_BRIDGING_CAPABILITY = 0x04
TLV_TYPE_NON_1905_NEIGHBOR_DEVICE_LIST = 0x06
TLV_TYPE_1905_NEIGHBOR_DEVICE_LIST = 0x07
TLV_TYPE_SUPPORTED_SERVICE = 0x80
TLV_TYPE_SEARCHED_SERVICE = 0x81
TLV_TYPE_ASSOCIATED_CLIENTS = 0x84
TLV_TYPE_AP_HT_CAPABILITIES = 0x86
TLV_TYPE_AP_VHT_CAPABILITIES = 0x87
TLV_TYPE_AP_HE_CAPABILITIES = 0x88
TLV_TYPE_AP_WIFI_6_CAPABILITIES = 0xAA
TLV_TYPE_DEFAULT_802_1Q_SETTINGS = 0xB5
TLV_TYPE_TRAFFIC_SEPARATION_POLICY = 0xB6
TLV_TYPE_PROFILE_2_ERROR_CODE = 0xBC
TLV_TYPE_DPP_CHIRP_VALUE = 0xD3
TLV_TYPE_CONTROLLER_CAPABILITY = 0xDD
TLV_TYPE_BACKHAUL_STA_RADIO_CAPABILITIES = 0xCB
TLV_TYPE_AKM_SUITE_CAPABILITIES = 0xCC
TLV_TYPE_STEERING_POLICY = 0x89
TLV_TYPE_METRIC_REPORTING_POLICY = 0x8A
TLV_TYPE_CHANNEL_SCAN_REPORTING_POLICY = 0xA4
TLV_TYPE_UNSUCCESSFUL_ASSOCIATION_POLICY = 0xC4
TLV_TYPE_BACKHAUL_BSS_CONFIGURATION = 0xD0
TLV_TYPE_QOS_MANAGEMENT_POLICY = 0xDB
TLV_TYPE_SPATIAL_REUSE_CONFIG_RESPONSE = 0xDA
TLV_TYPE_SPATIAL_REUSE_REQUEST = 0xD8
TLV_TYPE_SPATIAL_REUSE_REPORT = 0xD9
TLV_TYPE_WIFI_7_AGENT_CAPABILITIES = 0xDF
TLV_TYPE_AGENT_AP_MLD_CONFIGURATION = 0xE0
TLV_TYPE_BACKHAUL_STA_MLD_CONFIGURATION = 0xE1
TLV_TYPE_ASSOCIATED_STA_MLD_CONFIGURATION = 0xE2
TLV_TYPE_TID_TO_LINK_MAPPING_POLICY = 0xE6
TLV_TYPE_EHT_OPERATIONS = 0xE7
TLV_TYPE_RSN_PARAMETERS_CONFIGURATION = 0xEB
TLV_TYPE_BSS_ADVANCED_CONFIGURATION = 0xEC

_main_step_counter = 0
_sub_step_counter = 0

def print_main_step(message):
    global _main_step_counter, _sub_step_counter
    _main_step_counter += 1
    _sub_step_counter = 0
    label = f"Step {_main_step_counter}: {message}"
    print(f"\n\033[1m\033[97m{label}\033[0m")  # Bold white text
    return f'<span style="color:black; font-weight:bold;">{label}</span>'

def print_completed_step(message):
    global _main_step_counter
    label = f"Step {_main_step_counter}: Completed analysis of {message}"
    print(f"\033[1m\033[97m{label}\033[0m")  # Bold white text
    return f'<span style="color:black; font-weight:bold;">{label}</span>'

def print_sub_step(message):
    global _sub_step_counter
    sub_label = chr(ord('a') + _sub_step_counter)
    _sub_step_counter += 1
    label = f"Step {_main_step_counter}{sub_label}: {message}"
    print(f"\033[1m\033[97m{label}\033[0m")  # Bold white text
    return f'<span style="color:black; font-weight:bold;">{label}</span>'

def print_step(message):
    print(f"\033[1m\033[97m{message}\033[0m")  # Bold white text
    return f'<span style="color:black; font-weight:bold;">{message}</span>'

def print_error(message):
    print(f"\033[91mFAIL: {message}\033[0m")  # Red text\
    #return f'<b style="color:red">FAIL: {message}</b>'
    return f'<span style="color:red; font-weight:bold;">FAIL: {message}</span>'

def print_warning(message):
    print(f"\033[93mWARN: {message}\033[0m")  # Orange text
    return f'<span style="color:orange; font-weight:bold;">WARN: {message}</span>'

def print_success(message):
    print(f"\033[92mPASS: {message}\033[0m")  # Green text
    #return f'<b style="color:green">PASS: {message}</b>'
    return f'<span style="color:green; font-weight:bold;">PASS: {message}</span>'

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