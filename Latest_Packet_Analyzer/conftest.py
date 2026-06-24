import pytest


global capture_file_path
capture_file_path = r"your_capture_file_path_here.pcap" # Update this path to point to your actual capture file
#example: capture_file_path = r"/home/user/captures/test_capture.pcap"

global MSG_TYPE_TOPOLOGY_DISCOVERY
MSG_TYPE_TOPOLOGY_DISCOVERY = 0x0000
global MSG_TYPE_TOPOLOGY_NOTIFICATION
MSG_TYPE_TOPOLOGY_NOTIFICATION = 0x0001
global MSG_TYPE_AP_AUTOCONFIG_SEARCH
MSG_TYPE_AP_AUTOCONFIG_SEARCH = 0x0007
global MSG_TYPE_AP_AUTOCONFIGURATION_RESPONSE
MSG_TYPE_AP_AUTOCONFIGURATION_RESPONSE = 0x0008
global MSG_TYPE_1905_ACK
MSG_TYPE_1905_ACK = 0x8000
global MSG_TYPE_AP_CAPABILITY_QUERY
MSG_TYPE_AP_CAPABILITY_QUERY = 0x8001
global MSG_TYPE_AP_CAPABILITY_REPORT
MSG_TYPE_AP_CAPABILITY_REPORT = 0x8002
global MSG_TYPE_CHANNEL_PREFERENCE_QUERY
MSG_TYPE_CHANNEL_PREFERENCE_QUERY = 0x8004
global MSG_TYPE_CHANNEL_PREFERENCE_REPORT
MSG_TYPE_CHANNEL_PREFERENCE_REPORT = 0x8005
global MSG_TYPE_AP_AUTOCONFIGURATION_RENEW
MSG_TYPE_AP_AUTOCONFIGURATION_RENEW = 0x000A
global MSG_TYPE_AP_AUTOCONFIG_RENEW
MSG_TYPE_AP_AUTOCONFIG_RENEW = 0x000A
global CMDU_AP_AUTOCONFIGURATION_RENEW
CMDU_AP_AUTOCONFIGURATION_RENEW = 0x000A
global CMDU_AP_AUTOCONFIG_WSC
CMDU_AP_AUTOCONFIG_WSC = 0x0009
global MSG_TYPE_AP_TOPOLOGY_QUERY
MSG_TYPE_AP_TOPOLOGY_QUERY = 0x0002
global MSG_TYPE_AP_TOPOLOGY_RESPONSE
MSG_TYPE_AP_TOPOLOGY_RESPONSE = 0x0003
global MSG_TYPE_AP_AUTOCONFIG_WSC
MSG_TYPE_AP_AUTOCONFIG_WSC = 0x0009
global MSG_TYPE_POLICY_CONFIG_REQUEST
MSG_TYPE_POLICY_CONFIG_REQUEST = 0x8003
global MSG_TYPE_CHANNEL_SELECTION_REQUEST
MSG_TYPE_CHANNEL_SELECTION_REQUEST = 0x8006
global MSG_TYPE_CHANNEL_SELECTION_RESPONSE
MSG_TYPE_CHANNEL_SELECTION_RESPONSE = 0x8007
global MSG_TYPE_OPERATING_CHANNEL_REPORT
MSG_TYPE_OPERATING_CHANNEL_REPORT = 0x8008
global CMDU_AP_ERROR
CMDU_AP_ERROR = 0x0055


global controller_mac
controller_mac = "AL MAC address of the controller here" # Update this to the AL MAC address of the controller in your test setup
#example: controller_mac = "00:11:22:33:44:55"

global agent_mac
agent_mac = "AL MAC address of the agent here" # Update this to the AL MAC address of the agent in your test setup
#example: agent_mac = "00:11:22:33:44:66"

global agent_front_radio_count
agent_front_radio_count = 3 # Update this to the actual number of front radios in the agent as per your test setup, this is used for validating the count of WSC M1 messages in the test

global M2_TYPE
M2_TYPE = 0x05

global ssid_name
ssid_name = "TDKB_Test123" #update this to the actual SSID name used in your test setup

global VALIDATION_LEVEL
VALIDATION_LEVEL = 4


def pytest_addoption(parser):
    parser.addoption(
        "--level",
        action="store",
        default=4,
        type=int,
        help="Validation level (1 to 4)"
    )

def pytest_configure(config):
    global VALIDATION_LEVEL
    VALIDATION_LEVEL = config.getoption("--level")

@pytest.fixture(scope="session")
def validation_level(request):
    return VALIDATION_LEVEL
