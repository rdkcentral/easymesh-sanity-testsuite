# Centralized UI Automation Test Case Specification

## Scope

This document centralizes all test cases implemented in the following files:
- [test_basic_sanity_tc.py](#test_basic_sanity_tcpy)
- [test_em_functionality.py](#test_em_functionalitypy)
- [test_network_topology.py](#test_network_topologypy)
- [test_wifi_client_connectivity.py](#test_wifi_client_connectivitypy)
- [test_lan_client_connectivity.py](#test_lan_client_connectivitypy)

It documents each case with the stepwise flow captured directly in the test procedure table.

## Test Suite Pre-requisites

1. Minimum setup: 1 Controller, 2 Extenders, 1 LAN client, 1 Wi-Fi client (more allowed in config.yaml).
2. Setup should be in default state before full suite execution.
3. Configure setup details in config.yaml as per manual.
4. At least 1 extender must be configured and enabled in config.yaml.
5. Topology test requires minimum 2 onboarded extenders.
6. Mesh backhaul formation must be complete before execution.
7. Below tests are validated as part of suite pre-requisites and should mandatorily pass for the test cases to be executed:
    - Validate all configured VAPs are UP.
    - Verify mld0 interface presence.
    - Verify mld0 links to private VAPs.
    - Verify mesh backhaul interfaces.
    - Verify mesh backhaul extenders are connected.

## Test Environment

| Component | Meaning |
| --- | --- |
| Controller | EasyMesh control node (primary BPI-R4) that hosts OneWifiMesh DB, RDKB-CLI UI, and coordinates mesh operations. |
| Extender | EasyMesh agent node(s) that join the controller over backhaul and extend coverage. |
| LAN Client | Wired test endpoint connected over Ethernet, used for host discovery/IP/internet connectivity validation. |
| Wi-Fi Client | Wireless Linux test endpoint used for SSID scan, BSSID selection, association, IP assignment, and internet connectivity validation. |

---

<a id="test_basic_sanity_tcpy"></a>
## 1) test_basic_sanity_tc.py

<a id="tc-basic-01"></a>
### TC-BASIC-01: test_onewifi_service_status

Preconditions:
- Global setup completed.
- Controller and all enabled extenders are reachable over SSH.

Objective:
- Verify onewifi service is running on all mesh devices.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Build verification list from ssh.device_list; include controller. | Include each enabled extender from ssh.device_list iteration. |  |  | Service validation loop is started for every mesh node. | Pytest step logs (Step n per device). |
| 2 | Execute: systemctl is-active onewifi | Execute: systemctl is-active onewifi on each extender via SSH. |  |  | onewifi returns active on controller and all enabled extenders. | Command output and pass/fail log lines. |

### TC-BASIC-02: test_verify_core_files_presence

<a id="tc-basic-02"></a>

Preconditions:
- Global setup completed.
- SSH access to controller and extenders.

Objective:
- Ensure no crash core files are present (or flag if present).

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Execute: ls /tmp/*dmp* 2>/dev/null on controller. | Execute: ls /tmp/*dmp* 2>/dev/null on each extender. |  |  | Command returns empty output (no dump files) on all checked devices. | Core scan command output and pass/fail logs. |

### TC-BASIC-03: test_ieee1905_em_ctrl_service_status

<a id="tc-basic-03"></a>

Preconditions:
- Controller SSH reachable.

Objective:
- Verify ieee1905_em_ctrl service is active on controller.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Execute: systemctl is-active ieee1905_em_ctrl |  |  |  | Controller service state is retrieved successfully. | Service command output. |
| 2 | Validate command output contains active. |  |  |  | ieee1905_em_ctrl is active on controller. | Pass/fail log entry. |

### TC-BASIC-04: test_em_ctrl_service_status

<a id="tc-basic-04"></a>

Preconditions:
- Controller SSH reachable.

Objective:
- Verify em_ctrl service is active on controller.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Execute: systemctl is-active em_ctrl |  |  |  | Controller service state is retrieved successfully. | Service command output. |
| 2 | Validate command output contains active. |  |  |  | em_ctrl is active on controller. | Pass/fail log entry. |

### TC-BASIC-05: test_ieee1905_em_agent_service_status

<a id="tc-basic-05"></a>

Preconditions:
- Controller and extenders reachable.

Objective:
- Verify ieee1905_em_agent service is active on controller and extenders.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Build verification list from ssh.device_list; include controller. | Include each enabled extender from ssh.device_list iteration. |  |  | All target devices are queued for service check. | Iteration logs. |
| 2 | Execute: systemctl is-active ieee1905_em_agent | Execute: systemctl is-active ieee1905_em_agent on each extender via SSH. |  |  | ieee1905_em_agent is active on all checked devices. | Command output and pass/fail logs. |

### TC-BASIC-06: test_em_agent_service_status

<a id="tc-basic-06"></a>

Preconditions:
- Controller and extenders reachable.

Objective:
- Verify em_agent service is active on controller and extenders.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Build verification list from ssh.device_list; include controller. | Include each enabled extender from ssh.device_list iteration. |  |  | All target devices are queued for service check. | Iteration logs. |
| 2 | Execute: systemctl is-active em_agent | Execute: systemctl is-active em_agent on each extender via SSH. |  |  | em_agent is active on all checked devices. | Command output and pass/fail logs. |

### TC-BASIC-07: test_db_values_match_default_json

<a id="tc-basic-07"></a>

Preconditions:
- Controller DB accessible.
- Reset.json path configured and readable.

Objective:
- Validate OneWifiMesh SSID table values match Reset.json defaults by haul type.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Read reset file using: cat <reset_json_file_path>; parse wfa-dataelements:Reset.<ssid_table>. |  |  |  | Reset.json content is available for validation. | JSON dump in logs. |
| 2 | Run SQL metadata/data queries via mysql -N --batch: SHOW COLUMNS FROM <ssid_table>; SELECT * FROM <ssid_table>; |  |  |  | SSID table columns and rows are fetched from OneWifiMesh DB. | SQL query output. |
| 3 | For each JSON entry, map haul type to DB row by matching haul marker inside ID field (for example, ID LIKE %Fronthaul%OneWifiMesh%). |  |  |  | Correct JSON-to-DB row mapping is established for each haul type. | Mapping and row dump logs. |
| 4 | Compare every JSON field with DB value (including boolean normalization 1/0/true/false and list membership checks). |  |  |  | All validated haul-type rows match Reset.json defaults. | Per-field pass/fail logs. |

### TC-BASIC-08: test_log_files_presence (parametrized)

<a id="tc-basic-08"></a>

Preconditions:
- Controller and extenders reachable.
- /tmp accessible on devices.

Objective:
- Validate expected EM and IEEE1905 log file counts on controller/extenders.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | For pattern em*.log, run: find /tmp -maxdepth 1 -type f -name 'em*.log' \| wc -l | Run same command on each extender. |  |  | File count is collected on each device. | find/wc output per device. |
| 2 | Compare count with expected controller value = 3. | Compare count with expected extender value = 1. |  |  | Actual count matches expected count for em*.log. | Pass/fail log lines. |
| 3 | For pattern ieee1905*.txt, run: find /tmp -maxdepth 1 -type f -name 'ieee1905*.txt' \| wc -l | Run same command on each extender. |  |  | File count is collected on each device. | find/wc output per device. |
| 4 | Compare count with expected controller value = 2. | Compare count with expected extender value = 1. |  |  | Actual count matches expected count for ieee1905*.txt. | Pass/fail log lines. |

### TC-BASIC-09: test_broadcast_default_SSID

<a id="tc-basic-09"></a>

Preconditions:
- At least one enabled Wi-Fi client.
- OneWifiMesh DB reachable.

Objective:
- Verify default fronthaul/backhaul SSIDs in DB are broadcast and visible from Wi-Fi client(s).

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Load expected defaults from config: network_ssid_map.Fronthaul.default_ssid and network_ssid_map.Backhaul.default_ssid. |  |  |  | Expected baseline SSID values are available for checks. | Config-derived log lines. |
| 2 | Query DB on controller using mysql -N --batch with: SELECT SSID FROM <ssid_table> WHERE ID LIKE '%Fronthaul%OneWifiMesh%'; and SELECT SSID FROM <ssid_table> WHERE ID LIKE '%Backhaul%OneWifiMesh%'; |  |  |  | DB fronthaul/backhaul SSID values match configured defaults. | SQL output and compare logs. |
| 3 |  |  |  | For each enabled Wi-Fi client: nmcli -t -f BSSID,SSID device wifi list \| grep <default_fronthaul_ssid> (with pre-scan disconnect if connected). | Default fronthaul SSID is visible from client scans. | nmcli scan output per client. |
| 4 |  |  |  | For each enabled Wi-Fi client: nmcli -t -f BSSID,SSID device wifi list \| grep <default_backhaul_ssid> (with same scan workflow). | Default backhaul SSID is visible from client scans. | nmcli scan output per client. |

### TC-BASIC-10: test_verify_agent_connectivity_to_default_gateway

<a id="tc-basic-10"></a>

Preconditions:
- At least one enabled extender.

Objective:
- Verify each extender can ping default gateway.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  | Execute on each enabled extender: ping 10.0.0.1 -c 5 |  |  | Ping statistics are collected per extender. | Ping output per extender. |
| 2 |  | Validate command output contains 0% packet loss. |  |  | Every enabled extender has default-gateway connectivity. | Pass/fail logs. |

### TC-BASIC-11: test_ssh_controller_agent_connectivity

<a id="tc-basic-11"></a>

Preconditions:
- SSH credentials valid.

Objective:
- Confirm SSH command execution works on controller and extenders.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Execute: cat /version.txt over SSH on controller. | Execute: cat /version.txt over SSH on each extender. |  |  | SSH command execution works on all devices and firmware/version text is returned. | Command output logs. |

### TC-BASIC-12: test_verify_rdkbcli_browser_launch

<a id="tc-basic-12"></a>

Preconditions:
- Controller UI endpoint reachable.
- Playwright browser fixture available.

Objective:
- Validate RDKB-CLI web UI can be launched.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Playwright action: page.goto('http://<controller_ip>:8888/', wait_until='domcontentloaded'). |  |  |  | RDKB-CLI URL opens successfully. | Playwright step log. |
| 2 | Playwright assertion: expect(page).to_have_title('EasyMesh R6 Pro Controller'). |  |  |  | Landing page title validation passes and UI is accessible. | Assertion log and optional screenshot. |

### TC-BASIC-13: test_verify_rdkbcli_tab_navigation

<a id="tc-basic-13"></a>

Preconditions:
- RDKB-CLI UI reachable.
- Playwright navigation helpers available.

Objective:
- Verify major sidebar tab navigation in RDKB-CLI.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Open RDKB-CLI: page.goto('http://<controller_ip>:8888/'); then click sidebar link Wireless Settings and assert h1 is visible. |  |  |  | Wireless Settings page loads without navigation errors. | Playwright navigation/assertion logs. |
| 2 | Sequentially click and verify sidebar pages: Network Topology, Coverage Map, Mesh Devices, Connected Clients (expect h1 for each). |  |  |  | Each page in this set opens and header verification passes. | Page-wise logs and screenshots on failure. |
| 3 | Sequentially click and verify: Wireless Settings, Policy Settings, Performance, RF Analysis, Security Center, System Settings (expect h1 for each). |  |  |  | Each page in this set opens and header verification passes. | Page-wise logs and screenshots on failure. |

---

<a id="test_em_functionalitypy"></a>
## 2) test_em_functionality.py

### TC-EM-01: test_rdkbcli_update_verify_ssid

Preconditions:
- RDKB-CLI UI reachable.
- Controller and extenders reachable over SSH.

Objective:
- Update fronthaul SSID in UI, verify propagation to devices, then revert to default.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Use Playwright flow: goto RDKB-CLI -> Wireless Settings -> click editProfile('Fronthaul') -> fill #profile-ssid -> click submit and #save-profile-settings. |  |  |  | SSID update request is submitted from UI. | UI action logs and screenshot of updated value. |
| 2 | Verify device propagation using SSH command: iw dev mld0 info \| awk '/ssid/ {print $2}' (with retry/wait loop). | Verify same command on each extender until all values match new SSID. |  |  | Updated SSID is present on controller and all enabled extenders. | SSH command outputs and pass/fail logs. |
| 3 | Repeat Step 1 with default fronthaul SSID value from config network_ssid_map.Fronthaul.default_ssid. |  |  |  | Revert request is submitted from UI. | UI revert logs and screenshot. |
| 4 | Re-run verification command: iw dev mld0 info \| awk '/ssid/ {print $2}' for default value check. | Re-run same command on each extender for default value check. |  |  | Default SSID is restored across mesh. | SSH outputs and final validation logs. |

### TC-EM-02: test_rdkbcli_update_verify_password

Preconditions:
- RDKB-CLI UI reachable.
- Controller/extender SSH access.

Objective:
- Update fronthaul passphrase in UI, verify propagation, then revert to default.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Use Playwright flow: goto RDKB-CLI -> Wireless Settings -> click editProfile('Fronthaul') -> fill #profile-passphrase -> submit and save. |  |  |  | Passphrase update request is submitted from UI. | UI action logs and screenshot of updated value. |
| 2 | Verify backend value on controller DB using mysql -N --batch query: SELECT PassPhrase FROM <ssid_table> WHERE ID='Fronthaul@OneWifiMesh' LIMIT 1; | Extenders rely on mesh sync; no direct passphrase CLI check is implemented in this test. |  |  | DB passphrase value matches expected updated value after sync wait. | SQL output and validation logs. |
| 3 | Repeat Step 1 with default fronthaul passphrase value from config network_ssid_map.Fronthaul.default_pass. |  |  |  | Revert request is submitted from UI. | UI revert logs and screenshot. |
| 4 | Re-run controller DB query: SELECT PassPhrase FROM <ssid_table> WHERE ID='Fronthaul@OneWifiMesh' LIMIT 1; and compare to default. | Extender-side validation remains indirect via controller DB consistency. |  |  | Default passphrase is restored. | SQL output and pass/fail logs. |

### TC-EM-03: test_rdkbcli_channel_change_preference (Skipped in current suite)

Preconditions:
- Test currently marked skip due to known instability (RDKBWIFI-424).
- If enabled: UI and SSH access required.

Objective:
- Modify radio channel preference in UI and verify controller/extender channel update.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | In Wireless Settings radio tab: select tab button.radio-tab-btn[data-band='<radio>']; choose ALL device #device-<band>; find current channel with preference 14 and set it to 0. |  |  |  | Existing most-preferred channel is downgraded in UI. | UI logs and screenshot. |
| 2 | Select new channel row #list-<band> .list-row[data-channel='<new_channel>']; check checkbox .ch-check; set preference to 14; click #save-radio-settings. |  |  |  | New channel preference configuration is applied in UI. | UI logs and screenshot. |
| 3 | Execute SSH command on controller: iw dev mld0 info; parse link ID <link_id> channel via regex. | Execute same SSH command on each extender and parse link ID channel value. |  |  | Controller and extenders show the updated channel for the target link ID. | Controller/extender command outputs. |

### TC-EM-04: test_rdkbcli_wifi_reset_with_default_values

Preconditions:
- RDKB CLI is accessible for the configured controller.
- System Settings page is available and loaded.
- Controller interface from `config["system"]["wifi_reset_interface"]` exists and has a valid MAC.
- Test sets non-default SSID/passphrase values before performing reset to validate the reset functionality restores defaults.

Objective:
- Validate that Wi-Fi reset with default SSID/passphrase values is accepted via UI, applied after reboot, and reflected in DB/interface-level verification without creating crash dumps. Verify that pre-reset non-default values are properly reset to defaults.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Update fronthaul SSID to non-default value (TDKB_New_SSID_03) using `update_verify_required_field_from_rdkbcli` helper. |  |  |  | Non-default SSID update request is submitted from UI. | UI action logs and screenshot. |
| 2 | Verify SSID update propagation on controller and all extenders using `verify_ssid_update_in_controller_and_agent`. | Verify SSID update on each enabled extender. |  |  | Updated SSID (TDKB_New_SSID_03) is present on controller and all enabled extenders. | SSH command outputs and pass/fail logs. |
| 3 | Update fronthaul passphrase to non-default value (TestTDKB@1234) using `update_verify_required_field_from_rdkbcli` helper. |  |  |  | Non-default passphrase update request is submitted from UI. | UI action logs and screenshot. |
| 4 | Verify passphrase update propagation on controller and all extenders using `verify_password_update_in_controller_and_agent`. | Verify passphrase update on each enabled extender. |  |  | Updated passphrase is synchronized across controller and all enabled extenders. | DB/SSH validation logs and pass/fail logs. |
| 5 | Wait for 20 seconds to ensure non-default changes are fully applied before proceeding with reset. |  |  |  | Sufficient delay is provided for system stability before reset operation. | Delay log. |
| 6 | Open RDKB CLI URL using Playwright helper `navigate_to_rdkbcli_page`. |  |  |  | RDKB CLI opens successfully. | Playwright step log. |
| 7 | Navigate to **System Settings** using navigation helper `navigate_to_required_rdkbcli_page`. |  |  |  | System Settings page is loaded successfully. | Playwright navigation log. |
| 8 | Read configured reset interface name (`wifi_reset_interface`) and retrieve its MAC from controller (`get_interface_mac_address`). |  |  |  | Interface MAC (AL MAC candidate) is fetched successfully. | SSH command output and pass log. |
| 9 | Select the retrieved AL MAC in Wi-Fi reset dropdown (`select_wifi_reset_al_mac`). |  |  |  | Correct target interface is selected in UI. | UI selection log/screenshot (on failure). |
| 10 | Trigger and confirm Wi-Fi reset from UI (`perform_wifi_reset`). |  |  |  | Reset workflow is accepted by UI confirmation flow. | UI dialog handling logs. |
| 11 | Reboot devices and wait for recovery (`reboot_device_after_wifi_reset`). | Agents reboot and reconnect as part of mesh recovery. |  |  | Mesh comes back online after reset. | Reboot/reconnect logs. |
| 12 | Verify OneWifiMesh DB values against **default** expected set (`verify_wifi_db_values(..., expected_type="default")`). |  |  |  | DB values have been reset and now reflect default SSID/passphrase values (not the pre-reset non-default values). | SQL/query validation logs. |
| 13 | Verify interface-level SSID values using `iw dev` against **default** expected set (`verify_iw_dev_interface_value(..., expected_type="default")`). | Validate corresponding extender-side interface values through helper flow. |  |  | Runtime interface state on controller and extenders matches expected default values. | SSH output + comparison logs. |
| 14 | Check for core/crash dump generation after reset (`verify_core_dump_generated`). | Same crash-dump validation for enabled extenders. |  |  | No unexpected dump/core files are generated due to reset flow. | Core scan logs and pass/fail summary. |

### TC-EM-05: test_rdkbcli_wifi_reset_with_custom_values

Preconditions:
- RDKB CLI is accessible for the configured controller.
- System Settings page is available and loaded.
- Controller interface from `config["system"]["wifi_reset_interface"]` exists and has a valid MAC.
- Custom Wi-Fi values are available in configuration for reset operation.

Objective:
- Validate that Wi-Fi reset with custom SSID/passphrase values is accepted via UI, applied after reboot, and reflected in DB/interface-level verification without creating crash dumps.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Open RDKB CLI URL and navigate to **System Settings** using Playwright navigation helpers. |  |  |  | System Settings view opens successfully. | Playwright step log. |
| 2 | Read configured reset interface name (`wifi_reset_interface`) and retrieve its MAC from controller (`get_interface_mac_address`). |  |  |  | Interface MAC (AL MAC candidate) is fetched successfully. | SSH command output and pass log. |
| 3 | Select the retrieved AL MAC in Wi-Fi reset dropdown (`select_wifi_reset_al_mac`). |  |  |  | Correct target interface is selected in UI. | UI selection log/screenshot (on failure). |
| 4 | Fill custom SSID/passphrase values in reset form (`configure_custom_wifi_values`). |  |  |  | Custom input fields are populated for reset request. | UI action log. |
| 5 | Capture pre-reset screenshot: `rdkbcli_wifi_reset_custom_values.png`. |  |  |  | Evidence of custom values before reset is saved. | Screenshot artifact. |
| 6 | Trigger and confirm Wi-Fi reset from UI (`perform_wifi_reset`). |  |  |  | Reset workflow is accepted by UI confirmation flow. | UI dialog handling logs. |
| 7 | Reboot devices and wait for recovery (`reboot_device_after_wifi_reset`). | Agents reboot and reconnect as part of mesh recovery. |  |  | Mesh comes back online after reset. | Reboot/reconnect logs. |
| 8 | Verify OneWifiMesh DB values against **custom** expected set (`verify_wifi_db_values(..., expected_type="custom")`). |  |  |  | DB reflects configured custom SSID/passphrase values. | SQL/query validation logs. |
| 9 | Verify interface-level SSID values using `iw dev` against **custom** expected set (`verify_iw_dev_interface_value(..., expected_type="custom")`). | Validate corresponding extender-side interface values through helper flow. |  |  | Runtime interface state matches expected custom values. | SSH output + comparison logs. |
| 10 | Check for core/crash dump generation after reset (`verify_core_dump_generated`). | Same crash-dump validation for enabled extenders. |  |  | No unexpected dump/core files are generated due to reset flow. | Core scan logs and pass/fail summary. |

---

<a id="test_network_topologypy"></a>
## 3) test_network_topology.py

### TC-TOPO-01: test_validate_ui_topology

Preconditions:
- Minimum 2 enabled extenders (otherwise test is skipped).
- Network Topology page reachable.
- Reference topology images available.

Objective:
- Validate UI topology node/SSID/BSSID consistency with backend TR-181 data and classify topology image similarity.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Playwright: open RDKB-CLI and Topology page; collect TR-181 data via dmcli commands on controller: DeviceNumberOfEntries, Device.<i>.ID, RadioNumberOfEntries, BSSNumberOfEntries, SSID, BSSID, and APMLD.1.MLDMACAddress. |  |  |  | Backend topology mapping (device -> SSID/BSSID/MLD) is available. | dmcli collection logs. |
| 2 | Compare TR-181 device count against configured extender count (+ controller) and log mismatch/pass. |  |  |  | Device-count relationship is validated. | Count comparison logs. |
| 3 | For each UI node/SSID tooltip in topology graph, compare tooltip MAC/BSSID/MLD values against TR-181 map. |  |  |  | UI topology metadata matches backend device data. | Tooltip validation logs. |
| 4 | Capture screenshot using Playwright page.screenshot(.../network_topology.png). |  |  |  | Current topology screenshot is captured successfully. | network_topology.png artifact. |
| 5 | Compare screenshot with reference star_network_topology.png and daisychain_network_topology.png using SSIM (skimage + cv2). |  |  |  | Topology is classified as Star or Daisychain based on SSIM threshold. | SSIM score output and classification log. |

### TC-TOPO-02: test_determine_topology_type_from_brctl_command

Preconditions:
- Minimum 2 enabled extenders.
- bridge_intf configured in system section.

Objective:
- Determine star vs daisychain topology from bridge STA interfaces and station-dump traversal.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Execute on controller: brctl show <bridge_intf>; parse interfaces that match wifi*.sta. |  |  |  | STA interface list is available for topology decision. | brctl output logs. |
| 2 | For each STA interface execute on controller: iw dev <sta_iface> station dump |  |  |  | Station dump data is available for connected peers. | Station dump outputs. |
| 3 | If STA interface count >= 2, classify as Star topology (direct multi-extender links). |  |  |  | Star topology is detected and logged. | Classification logs. |
| 4 | If STA interface count == 1, fetch first-hop MAC from controller station dump; then fetch each extender mesh backhaul MAC using ifconfig wifi1.3; traverse hop-by-hop with iw dev <sta_iface> station dump on each visited extender. | Provide per-extender MAC map participation in traversal path. |  |  | Daisychain path is validated without loops and with expected node count. | Traversal and MAC-map logs. |
| 5 | Emit final topology verdict after traversal/count checks. |  |  |  | Final topology classification (Star or Daisychain/Invalid) is determined. | Final result log. |

---

<a id="test_wifi_client_connectivitypy"></a>
## 4) test_wifi_client_connectivity.py

### TC-WIFI-01: test_fronthaul_wifi_client_connectivity

Preconditions:
- At least one enabled Wi-Fi client (module fixture enforces skip otherwise).
- Fronthaul SSID/passphrase available in DB.

Objective:
- Verify Wi-Fi client can scan fronthaul SSID, connect to visible BSSID, obtain IP, and access internet.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Run SQL query on controller DB: SELECT SSID, PassPhrase FROM <ssid_table> WHERE ID='Fronthaul@OneWifiMesh' LIMIT 1; |  |  |  | Valid fronthaul SSID/passphrase are available for connectivity workflow. | SQL query logs. |
| 2 | Collect controller fronthaul BSSIDs using SSH command: iw dev mld0 info (parse link addr). | Collect extender fronthaul BSSIDs using same command on each enabled extender. |  |  | Candidate AP BSSID set is available for selection. | BSSID collection logs. |
| 3 |  |  |  | On each Wi-Fi client: identify wifi interface via nmcli -t -f DEVICE,TYPE dev status \| grep wifi \| cut -d: -f1; scan with nmcli -t -f BSSID,SSID device wifi list \| grep <fronthaul_ssid>; parse visible BSSIDs. | Visible target BSSID candidates are discovered. | nmcli scan output per client. |
| 4 |  |  |  | Connect using: sudo -S nmcli device wifi connect '<ssid>' password '<passphrase>' bssid <target_bssid> ifname <wifi_iface> | Wi-Fi association is successful to a target controller/extender BSSID. | nmcli connection output. |
| 5 |  |  |  | Verify IP and internet on client: nmcli -t -f IP4.ADDRESS device show <wifi_iface> \| awk -F'[:/]' '{print $2}' and ping -I <wifi_iface> -c 5 www.google.com | Client has valid IP and internet reachability (0% packet loss). | IP and ping logs. |

### TC-WIFI-02: test_fronthaul_wifi_client_connectivity_with_updated_ssid

Preconditions:
- RDKB-CLI reachable.
- At least one enabled Wi-Fi client.

Objective:
- Update fronthaul SSID, validate propagation, test client connectivity on updated SSID, then revert.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Use Playwright update flow in Wireless Settings to set new fronthaul SSID (editProfile + fill #profile-ssid + save). |  |  |  | New SSID request is submitted from UI. | UI update logs and screenshot. |
| 2 | Verify propagation using SSH command iw dev mld0 info \| awk '/ssid/ {print $2}' on controller. | Verify same command on each extender with retry/wait until values match new SSID. |  |  | Updated SSID is propagated across mesh nodes. | SSH verification logs. |
| 3 |  |  |  | Execute fronthaul connectivity workflow on new SSID: nmcli scan (BSSID,SSID), connect with sudo nmcli device wifi connect ..., then IP/internet checks (nmcli IP4.ADDRESS + ping -I ...). | Client connects and passes IP/internet checks on updated SSID. | Scan/connectivity logs. |
| 4 | Revert SSID with same UI flow to config default; re-check via iw dev mld0 info \| awk '/ssid/ {print $2}' | Verify default SSID restored on each extender using same command. |  |  | Setup state is restored to default SSID. | Revert logs and verification output. |

---

<a id="test_lan_client_connectivitypy"></a>
## 5) test_lan_client_connectivity.py

### TC-LAN-01: test_lan_client_connectivity

Preconditions:
- At least one enabled LAN client (module fixture enforces skip otherwise).
- LAN client MAC/user/pass configured.

Objective:
- Verify each enabled LAN client is detected as active Ethernet host, has valid IP, and internet connectivity.

Test Type:
- Positive

#### Test Procedure and Expected Results
| Step Number | Controller | Extender | LAN Client | Wi-Fi Client | Expected Results | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Resolve host index on controller via dmcli pipeline: dmcli eRT getv Device.Hosts.Host. \| grep -i '<lan_client_mac>' -B 1 \| grep -v '^--$' \| head -n 1 \| awk -F'.' '{print $(NF-1)}' |  |  |  | Host index for configured LAN client MAC is resolved. | dmcli output. |
| 2 | Query host status on controller: dmcli eRT getv Device.Hosts.Host.<index>.IPAddress; dmcli eRT getv Device.Hosts.Host.<index>.Layer1Interface; dmcli eRT getv Device.Hosts.Host.<index>.Active |  |  |  | Client is Active=true, Layer1Interface=Ethernet, with valid IP. | dmcli outputs and validation logs. |
| 3 |  |  | Identify Ethernet interface bound to configured MAC using: /usr/sbin/ifconfig \| awk '/^[a-zA-Z0-9]/ {iface=$1} /<lan_client_mac>/ {print iface}' |  | LAN client interface mapping to MAC is correct. | LAN ifconfig output. |
| 4 |  |  | Verify interface IP using: /usr/sbin/ifconfig <iface> \| awk '/inet / {print $2}' |  | LAN interface has assigned IP address. | LAN ifconfig output. |
| 5 |  |  | Verify internet connectivity using: ping -c 5 www.google.com |  | Internet connectivity is verified by 0% packet loss. | Ping output logs. |

---

## Execution Notes

- Evidence should be collected from:
  - Pytest console logs and HTML report under TestRun_<timestamp>/Reports.
  - Stored screenshots in TestRun_<timestamp>/Screenshots.
- For skipped tests, attach skip reason and bug/reference ID in execution evidence.
- For parametrized cases, attach one evidence set per parameter instance.
