# Packet Analyzer

This folder contains utilities and test logic to capture EasyMesh/IEEE 1905.1 traffic and validate expected CMDUs and TLVs after SSID updates.

## Files

- `capture_utils.py`: Helper functions to start and stop remote tcpdump capture, then transfer the generated pcap file from device to local machine.
- `ieee1905_utils.py`: Shared IEEE 1905.1 constants and validation helpers (message/TLV related checks, mandatory TLV sets, TLV length validation, and formatted pass/fail logging).
- `message_verify.py`: Core packet analysis and verification routines that parse captured 1905 frames and validate message presence, TLV presence, relay flag status, and SSID content in topology response.
- `test_ssid_update_capture_analysis.py`: End-to-end test workflow that captures traffic during SSID update, validates controller/agent SSID consistency, and runs detailed packet-level checks using verification utilities.
- `main.py`: Entry-point runner that creates a timestamped run directory, exports `TEST_RUN_DIR`, and executes `test_ssid_update_capture_analysis.py` with a self-contained HTML report.

## Execution

Run the packet analyzer test suite from this folder:

```bash
python main.py
```

Artifacts are created under a timestamped folder:

- `TestRun_<timestamp>/Reports/ssid_update_capture_analysis.html`
- `TestRun_<timestamp>/Captured_Packets/ssid_update.pcap`
