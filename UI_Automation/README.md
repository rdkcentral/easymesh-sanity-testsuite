# UI Automation

This folder contains an automated test suite for EasyMesh/RDKB validation using Pytest, Playwright, and SSH-based device checks.

## Table of Contents

1. [File Overview](#file-overview)
2. [Test Setup Architecture](#test-setup-architecture)
3. [System Requirements](#system-requirements)
4. [Hardware/Network Requirements](#hardwarenetwork-requirements)
5. [Test Suite Execution Pre-requisites](#test-suite-execution-pre-requisites)
6. [Configuration](#configuration)
7. [Steps To Execute The Sanity Test Suite](#steps-to-execute-the-sanity-test-suite)
8. [Test Case Documentation](#test-case-documentation) 
9. [Notes](#notes)

## File Overview

| Name | Short Description |
| --- | --- |
| conftest.py | Defines shared Pytest fixtures, test-run directory creation, Playwright browser setup, YAML config loading and validation, SSH tunneling helpers, environment data, global setup verification (device connectivity, VAP validation, mesh backhaul checks), and failure log collection/report hooks. |
| main.py | Entry-point runner that creates a timestamped test-run folder, sets environment variables, and launches selected Pytest modules with an HTML report output. |
| utils.py | Provides reusable helpers for logging, UI navigation, screenshots, DB/SSH operations, Wi-Fi scans, SSID verification, topology data extraction/validation, and service status checks. |
| playwright_utils.py | Contains RDKB-CLI UI workflow helpers including SSID/password update verification, page navigation, field updates, screenshot capture, and value assertions against backend state. |
| test_basic_sanity_tc.py | Covers baseline sanity checks for services, logs, interfaces, SSID broadcast, connectivity, and RDKB-CLI navigation across controller and agent devices. |
| test_em_functionality.py | Validates EasyMesh feature workflows from UI and backend, including SSID/password updates, channel changes, and Wi-Fi reset behavior against database values. |
| test_lan_client_connectivity.py | Verifies LAN client discovery, IP assignment, interface type, and internet reachability via controller-side host data and client-side checks. |
| test_network_topology.py | Validates UI topology details against TR-181 backend data and compares captured topology screenshots against known Star and Daisychain reference images. |
| test_wifi_client_connectivity.py | Tests wireless client onboarding to fronthaul SSIDs (default and updated), including scan visibility, BSSID selection, connection success, IP assignment, and internet access. |
| EM_Test_User_Manual.md | User manual and setup guide for environment preparation, test coverage, installation, configuration, execution options, expected outputs, troubleshooting, and test setup architecture. |
| Network_topology_screenshots/ | Stores reference topology images (Star and Daisychain layouts) used for visual similarity checks during topology validation tests. |
| config.yaml | Runtime configuration file containing device credentials, network details, database information, and system-specific parameters for the test environment. |

## Test Setup Architecture

For detailed diagrams of the physical test setup and scalability approach, see [Test Setup Architecture](EM_Test_User_Manual.md#test-setup-architecture) in the **EM_Test_User_Manual.md** document.

## System Requirements

See [System Requirements](EM_Test_User_Manual.md#system-requirements) in [EM_Test_User_Manual.md](EM_Test_User_Manual.md).


## Hardware/Network Requirements

See [Hardware/Network Requirements](EM_Test_User_Manual.md#hardwarenetwork-requirements) in [EM_Test_User_Manual.md](EM_Test_User_Manual.md).


## Test Suite Execution Pre-requisites

See [Test Suite Execution Pre-requisites](EM_Test_User_Manual.md#test-suite-execution-pre-requisites) in [EM_Test_User_Manual.md](EM_Test_User_Manual.md).


## Configuration

See [Configuration](EM_Test_User_Manual.md#configuration) in [EM_Test_User_Manual.md](EM_Test_User_Manual.md).


## Steps To Execute The Sanity Test Suite

See [Steps To Execute The Sanity Test Suite](EM_Test_User_Manual.md#steps-to-execute-the-sanity-test-suite) in [EM_Test_User_Manual.md](EM_Test_User_Manual.md).

## Test Case Documentation

See [Sanity_Tests_Documentation.md](Sanity_Tests_Documentation.md) file

### Notes

- `conftest.py` currently connects to the controller and extenders with password-based Paramiko SSH sessions.
- Extender and client SSH sessions are opened through the controller using Paramiko direct TCP/IP channels.
- If `TEST_RUN_DIR` is set by `main.py`, reports and screenshots are created there; otherwise Pytest creates a fallback `TestRun_<timestamp>` directory automatically.
