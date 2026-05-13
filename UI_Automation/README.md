# UI Automation

This folder contains an automated test suite for EasyMesh/RDKB validation using Pytest, Playwright, and SSH-based device checks.

## File Overview

| Name | Short Description |
| --- | --- |
| conftest.py | Defines shared Pytest fixtures, test-run directory creation, Playwright browser setup, YAML config loading and validation, SSH tunneling helpers, environment data, and failure log collection/report hooks. |
| main.py | Entry-point runner that creates a timestamped test-run folder, sets environment variables, and launches selected Pytest modules with an HTML report output. |
| test_basic_sanity_tc.py | Covers baseline sanity checks for services, logs, interfaces, SSID broadcast, connectivity, and RDKB-CLI navigation across controller and agent devices. |
| test_em_functionality.py | Validates EasyMesh feature workflows from UI and backend, including SSID/password updates, channel changes, and Wi-Fi reset behavior against database values. |
| test_lan_client_connectivity.py | Verifies LAN client discovery, IP assignment, interface type, and internet reachability via controller-side host data and client-side checks. |
| test_network_topology.py | Validates UI topology details against TR-181 backend data and compares captured topology screenshots against known Star and Daisychain reference images. |
| test_wifi_client_connectivity.py | Tests wireless client onboarding to fronthaul SSIDs (default and updated), including scan visibility, BSSID selection, connection success, IP assignment, and internet access. |
| utils.py | Provides reusable helpers for logging, UI navigation, screenshots, DB/SSH operations, Wi-Fi scans, SSID verification, and topology data extraction/validation. |
| EM_Test_User_Manual.docx | User manual and setup guide for environment preparation, test coverage, execution options, expected outputs, and troubleshooting. |
| Network_topology_screenshots/ | Stores reference topology images used for visual similarity checks during topology validation tests. |

## Running The Suite

- Run all primary UI automation modules using the project runner:

```bash
python main.py
```

- `main.py` runs:
	- `test_basic_sanity_tc.py`
	- `test_wifi_client_connectivity.py`
	- `test_lan_client_connectivity.py`
	- `test_network_topology.py`
	- `test_em_functionality.py`

- Output artifacts are created under:
	- `TestRun_<timestamp>/Reports/sanity_report.html`
	- `TestRun_<timestamp>/Screenshots/`
	- `TestRun_<timestamp>/Failed_Logs/`

## Configuration

Before running the test suite, update `config.yaml` in the project root with your environment-specific values. The `config()` fixture in `conftest.py` loads this file with `yaml.safe_load()` and validates the required sections before any SSH-dependent test runs.

### Validation Rules From `conftest.py`

- The `controller` section must exist and must include non-empty `ip` and `user` values.
- The `extenders` section must be a valid YAML mapping. Each extender entry must include non-empty `ip` and `user` values, and an `enabled` parameter set to either true or false. At least one extender must be enabled.
- The `wifi_clients` and `lan_clients` sections, when present, must be YAML mappings.

### `config.yaml` Structure

#### `controller`

| Key | Description |
| --- | --- |
| `ip` | IP address of the EasyMesh controller device |
| `user` | SSH username for the controller |
| `pass` | SSH password for the controller |
| `key_file` | Optional SSH private key path placeholder in the YAML template |

#### `extenders`

Each entry under `extenders` represents one agent device, for example `ext1`, `ext2`, and so on.

| Key | Description |
| --- | --- |
| `enabled` | Extender enabled status (True or False) |
| `ip` | IP address of the extender or agent |
| `user` | SSH username for the extender |
| `pass` | SSH password for the extender |
| `passphrase` | Optional passphrase placeholder in the YAML template |

#### `wifi_clients`

Each entry under `wifi_clients` represents one Wi-Fi client.

| Key | Description |
| --- | --- |
| `ip` | IP address of the Wi-Fi client device |
| `user` | SSH username for the Wi-Fi client |
| `pass` | SSH password for the Wi-Fi client |

#### `lan_clients`

Each entry under `lan_clients` represents one wired LAN client.

| Key | Description |
| --- | --- |
| `mac` | MAC address of the LAN client device |
| `user` | SSH username for the LAN client |
| `pass` | SSH password for the LAN client |

#### `database`

| Key | Description |
| --- | --- |
| `name` | Database name used by the test suite |
| `user` | Database username |
| `pass` | Database password |
| `ssid_table` | Database table containing SSID data |

#### `system`

| Key | Description |
| --- | --- |
| `bridge_intf` | Bridge interface used in device-side checks |
| `wifi_reset_interface` | Interface used for Wi-Fi reset traffic capture or validation |
| `reset_json_file` | Path to the EasyMesh reset JSON file on the target system |

### Notes

- `conftest.py` currently connects to the controller and extenders with password-based Paramiko SSH sessions.
- Extender and client SSH sessions are opened through the controller using Paramiko direct TCP/IP channels.
- If `TEST_RUN_DIR` is set by `main.py`, reports and screenshots are created there; otherwise Pytest creates a fallback `TestRun_<timestamp>` directory automatically.

## Test Setup Architecture

For detailed diagrams of the physical test setup and scalability approach, see [Test Setup Architecture](EM_Test_User_Manual.md#test-setup-architecture) in the **EM_Test_User_Manual.md** document.