# Packet Analyzer - Usage Instructions

## Prerequisites

Before running the packet analyzer, update the following parameters in `conftest.py`:

1. **capture_file_path**
   - Set the path to the packet capture file (`.pcap`) to be analyzed.

2. **controller_mac**
   - Update the Controller AL MAC address.

3. **agent_mac**
   - Update the Agent AL MAC address.

4. **ssid_name**
   - Set the `ssid_name` parameter to the SSID that you want to validate.

5. **Profile Confirmation**
   - The captured packet file must contain:
     - **AP-Autoconfiguration Response Message**
   - This message is currently used for profile confirmation.
   - The profile validation logic will be reviewed and enhanced in a future update.

## Running the Test

Execute the following command to run the test and generate an HTML report:

```bash
pytest -v -s test_logic.py::test_ap_configuration_renew --html=Reports\test_logic.html --self-contained-html