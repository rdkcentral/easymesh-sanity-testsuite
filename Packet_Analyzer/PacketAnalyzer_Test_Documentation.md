# Centralized Packet Analyzer Test Case Specification

## Scope

This document centralizes all test cases implemented in the following Packet Analyzer test file:
- [test_ssid_update_capture_analysis.py](#test_ssid_update_capture_analysispy)

It documents each case with the stepwise flow captured directly in the test procedure table.

## Test Suite Pre-requisites

1. Minimum setup: 1 Controller and 1 Extender are configured and reachable.
2. Shared UI Automation config and fixtures are valid (`config`, `page`, `ssh_manager`, `paths`).
3. Capture interface and filter values are configured and valid:
    - interface: `eth0_virt_peer`
    - filter: `ether proto 0x893a`
4. Controller UI is reachable so SSID update can be triggered from RDKB-CLI.
5. Controller `/tmp` has sufficient space for temporary capture file storage.

## Test Environment

| Component | Meaning |
| --- | --- |
| Controller | EasyMesh controller where packet capture is started/stopped and where temporary pcap file is stored. |
| Extender | EasyMesh agent/extender participating in IEEE 1905.1 message exchange. |
| Local Test Machine | Executes pytest, Playwright workflow, pcap transfer, and packet analysis functions. |

---

<a id="test_ssid_update_capture_analysispy"></a>
## 1) test_ssid_update_capture_analysis.py

<a id="tc-pa-01"></a>
### TC-PA-01: test_capture_and_analyze_packets_with_ssid_update

Preconditions:
- Controller and extender are reachable over SSH.
- RDKB-CLI page is reachable.
- Packet capture interface and filter are available on controller.

Objective:
- Capture IEEE 1905.1 traffic during SSID update, then verify expected CMDUs, TLVs, relay indicator behavior, AL MAC consistency, and updated SSID presence in topology response.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | Local Test Machine | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Fetch controller MAC using `ifconfig eth0_virt_peer` (via helper), assign to `message_verify.controller_mac`. | Fetch extender MAC using `ifconfig eth1_virt_peer` (via helper), assign to `message_verify.agent_mac`. |  | Required MAC context is initialized for packet validation filters. | Step logs with MAC values. |
| 2 | Start remote capture on interface `eth0_virt_peer` with filter `ether proto 0x893a` and output `/tmp/ssid_update.pcap` (tcpdump flow via `capture_utils.capture_packets`). |  | Initialize local destination folder `TestRun_<timestamp>/Captured_Packets`. | Packet capture session starts successfully and capture process ID is returned. | Capture start logs/ID. |
| 3 | Run SSID update verification workflow on controller (UI-triggered update plus device-side verification via shared helper). | Verify updated SSID propagation on agent as part of same helper flow. | Trigger SSID update from RDKB-CLI through shared Playwright path. | SSID update is successfully applied and propagated while capture is running. | UI + SSH verification logs. |
| 4 | Stop packet capture process using returned capture ID (`capture_utils.stop_packet_capture`). |  |  | Capture stops cleanly. | Capture stop logs. |
| 5 | Verify capture file exists: `ls -l /tmp/ssid_update.pcap`; then remove file after transfer: `rm -f /tmp/ssid_update.pcap`. |  | Transfer remote pcap to local path `.../Captured_Packets/ssid_update.pcap` using SCP helper. | Capture file is present on device, transferred locally, and cleaned from device. | `ls -l` output, transfer status, delete log. |
| 6 |  |  | Validate CMDU presence/counts in local pcap using `message_verify.verify_cmdu_presence(...)` for: AP Autoconfiguration Renew, AP Autoconfiguration WSC, Topology Query, Topology Response. | Expected CMDU types are present with configured counts. | CMDU verification pass/fail logs. |
| 7 |  |  | Validate required TLVs with `message_verify.verify_tlv_presence_with_type(...)` for Renew, WSC M1, WSC M2, Topology Query, and Topology Response messages. | All mandatory TLVs are present in corresponding message types. | TLV verification pass/fail logs. |
| 8 |  |  | Validate protocol semantics in local pcap: relay indicator status (`verify_relay_indicator_flag_status`), transmitter MAC vs 1905 AL MAC TLV (`verify_1905_al_mac_address`), and updated SSID in topology response (`verify_ssidname_in_topology_response`). | Relay indicator and AL MAC checks pass, and updated SSID is present in AP Operational BSS TLV. | Final packet-analysis pass/fail logs. |

---

## Execution Notes

- Evidence should be collected from:
  - Pytest console logs and HTML report under `TestRun_<timestamp>/Reports`.
  - Captured packets under `TestRun_<timestamp>/Captured_Packets`.
- Attach `ssid_update_capture_analysis.html` and `ssid_update.pcap` for each execution.
