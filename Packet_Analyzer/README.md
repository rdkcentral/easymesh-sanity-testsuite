# Packet Analyzer

This folder contains utilities and test logic to capture EasyMesh/IEEE 1905.1 traffic and validate expected CMDUs and TLVs after SSID updates.

The module runs a packet capture during an SSID update workflow, transfers the generated pcap locally, and validates IEEE 1905.1 control traffic from the captured frames.

Please refer to the detailed test case documentation provided in [PacketAnalyzer_Test_Documentation.md](PacketAnalyzer_Test_Documentation.md) file

## Table of Contents

1. [Files](#files)
	- [Hardware/Network Requirements](#hardwarenetwork-requirements)
2. [Test Setup Architecture](#test-setup-architecture)
	- [Packet Analyzer Limitations](#packet-analyzer-limitations)
3. [Runtime Dependencies](#runtime-dependencies)
4. [Current Test Flow](#current-test-flow)
5. [Execution](#execution)
6. [Report Behavior](#report-behavior)
7. [Notes](#notes)


## Files

- `capture_utils.py`: Helper functions to start and stop remote tcpdump capture, then transfer the generated pcap file from device to local machine.
- `ieee1905_utils.py`: Shared IEEE 1905.1 constants and validation helpers (message/TLV related checks, mandatory TLV sets, TLV length validation, and formatted pass/fail logging).
- `message_verify.py`: Core packet analysis and verification routines that parse captured 1905 frames and validate message presence, TLV presence, relay flag status, AL MAC consistency, and updated SSID content in topology response.
- `test_ssid_update_capture_analysis.py`: End-to-end pytest workflow that uses the independent `ssh_manager` fixture, captures traffic during SSID update, validates controller/agent SSID consistency, and runs detailed packet-level checks using verification utilities.
- `conftest.py`: Packet Analyzer-local pytest hooks for HTML report formatting. It preserves captured stdout in the report and color codes `PASS:` and `FAIL:` log lines.
- `main.py`: Entry-point runner that creates a timestamped run directory, exports `TEST_RUN_DIR`, and executes `test_ssid_update_capture_analysis.py` with a self-contained HTML report.

### Hardware/Network Requirements

- Controller Device: 1 device accessible via network (configured in config.yaml)
- Agent/Extender Devices: 1 device accessible via network (configured in config.yaml)

## Test Setup Architecture

The current supported Packet Analyzer test setup is a single-controller and single-extender topology.

```text
					 +-----------------------------------+
					 | Local Test Machine               |
					 |-----------------------------------|
					 | - Packet_Analyzer/main.py        |
					 | - pytest + pytest-html           |
					 | - Playwright UI automation       |
					 | - Local pcap/report storage      |
					 +----------------+------------------+
									  |
					SSH / UI access   |
									  |
					 +----------------v------------------+
					 | Controller Device                |
					 |-----------------------------------|
					 | - SSID update trigger            |
					 | - tcpdump capture on             |
					 |   eth0_virt_peer                |
					 | - /tmp/ssid_update.pcap          |
					 +----------------+------------------+
									  |
				   IEEE 1905.1 / Mesh |
				   control traffic    |
									  |
					 +----------------v------------------+
					 | Extender Device                 |
					 |-----------------------------------|
					 | - Participates in mesh exchange  |
					 | - Sends/responds to CMDUs/TLVs   |
					 +-----------------------------------+
```

Packet capture is started on the controller, while IEEE 1905.1 message validation is performed on traffic exchanged between the controller and the single extender.

### Packet Analyzer Limitations

- Current code version only supports 1 extender. Scalability with multiple extenders is to be supported in future versions.

## Runtime Dependencies

- The Packet Analyzer flow reuses shared fixtures and helpers from `UI_Automation`, including:
	- `config` for device and database settings
	- `page` and related Playwright fixtures for SSID update via UI flow
	- `ssh_manager` for independent SSH access without relying on `global_setup`
- The test expects the UI Automation `config.yaml` to be valid and reachable for controller and extender access.

## Current Test Flow

The current `test_ssid_update_capture_analysis.py` workflow performs the following actions:

1. Connects to controller and agent using the shared `ssh_manager` fixture.
2. Reads controller and agent MAC addresses used by packet-verification filters.
3. Starts packet capture on interface `eth0_virt_peer` with filter `ether proto 0x893a`.
4. Updates the SSID through the existing UI automation path.
5. Stops packet capture and verifies the capture file exists on the controller.
6. Downloads the capture to the local run directory and deletes the remote file.
7. Validates expected CMDUs and TLVs from the generated pcap.
8. Verifies relay indicator status, AL MAC consistency, and updated SSID presence in topology response.

## Execution

Run the packet analyzer test suite from this folder:

```bash
python main.py
```

`main.py` sets the `TEST_RUN_DIR` environment variable before invoking pytest so both artifacts and report output are written into the same timestamped execution directory.

## Report Behavior

- The HTML report is generated using `pytest-html` with `--self-contained-html`.
- Packet Analyzer includes a local pytest HTML hook that formats captured stdout in the report.
- Console log lines containing `PASS:` are rendered in green in the HTML report.
- Console log lines containing `FAIL:` are rendered in red in the HTML report.

Artifacts are created under a timestamped folder:

- `TestRun_<timestamp>/Reports/ssid_update_capture_analysis.html`
- `TestRun_<timestamp>/Captured_Packets/ssid_update.pcap`

## Notes

- Packet Analyzer now uses the independent `ssh_manager` fixture instead of the `ssh` fixture path that depends on `global_setup`.
- Packet Analyzer has its own local `conftest.py` for HTML report formatting, so report styling does not depend on `UI_Automation/conftest.py` being auto-discovered by pytest.
