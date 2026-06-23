# Packet Analyzer - Usage Guide

## Packet Capture

1. Set up an EasyMesh network with one Controller and one Agent (Extender).
2. Start packet capture on the Controller:

   ```bash
   tcpdump -i eth0_virt_peer ether proto 0x893a -s 0 -w easymesh_capture.pcap
   ```

3. Trigger an SSID update using `rdkbcli`.
4. Verify that the updated SSID is reflected on both the Controller and the Agent.
5. Stop the packet capture.

## Prerequisites

Before running the packet analyzer, update the following parameters in `conftest.py`:

1. **capture_file_path**
   - Path to the packet capture (`.pcap`) file.

2. **controller_mac**
   - Controller AL MAC address.

3. **agent_mac**
   - Agent AL MAC address.

4. **ssid_name**
   - SSID to be validated.

## Profile Validation

The packet capture must contain an **AP-Autoconfiguration Response** message.

Currently, this message is used to determine the EasyMesh profile. The profile detection logic is temporary and will be enhanced in a future update.

## Validation Levels

The packet analyzer supports three validation levels:

- **Level 1**
  - Verifies the presence of the expected IEEE 1905.1/EasyMesh messages.

- **Level 2**
  - Performs all Level 1 validations and additionally:
    - Verifies the presence of mandatory TLVs.
    - Validates TLV lengths.
    - Detects unexpected or additional TLVs.

- **Level 3**
  - Performs all Level 1 and Level 2 validations and additionally:
    - Validates the payload/content of messages and TLVs.

## Running the Packet Analyzer

Execute the following command to run the packet analyzer and generate an HTML report:

```bash
pytest -v -s test_logic.py::test_ap_configuration_renew \
    --html=Reports/test_logic.html \
    --self-contained-html \
    --level=1
```