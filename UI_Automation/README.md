# UI Automation

This folder contains an automated test suite for EasyMesh/RDKB validation using Pytest, Playwright, and SSH-based device checks.

## File Overview

| Name | Short Description |
| --- | --- |
| conftest.py | Defines shared Pytest fixtures, test-run directory creation, Playwright browser setup, SSH tunneling helpers, environment data, and failure log collection/report hooks. |
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

## Configuration: Fields to Fill in `conftest.py`

Before running the test suite, update the `global_config` fixture in `conftest.py` with your environment-specific values.

### `global_config` Fixture

| Variable | Description |
| --- | --- |
| `ctrl_ip` | IP address of the EasyMesh controller device |
| `ctrl_user` | SSH username for the controller |
| `ctrl_pass` | SSH password for the controller (leave empty if using key file) |
| `key_file` | Path to SSH private key file for the controller (or `None` for password auth) |
| `ext1_ip` | IP address of the extender/agent device |
| `ext1_user` | SSH username for the extender |
| `ext1_pass` | SSH password for the extender |
| `passphrase` | Passphrase for the SSH key file (if applicable) |
| `client_ip` | IP address of the Wi-Fi client device |
| `client_user` | SSH username for the Wi-Fi client |
| `client_pass` | SSH password for the Wi-Fi client |
| `lan_client_mac` | MAC address of the LAN client device |
| `lan_client_user` | SSH username for the LAN client |
| `lan_client_pass` | SSH password for the LAN client |
| `db_user` | Database username |
| `db_pass` | Database password |