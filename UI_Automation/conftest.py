# If not stated otherwise in this file or this component LICENSE file the
# following copyright and licenses apply:
#
# Copyright 2026 RDK Management
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from urllib import request
from html import escape
import re
import pytest
from playwright.sync_api import sync_playwright
import paramiko
from pathlib import Path
import pytest_html
import time
from scp import SCPClient
import datetime
import os
import yaml
import utils
import io
import contextlib

BASE_DIR = Path(__file__).resolve().parent
screenshots_path = None
reports_path = None
GLOBAL_SETUP_LOGS = []


def record_global_setup_log(message, print_to_stdout=True):
    if print_to_stdout:
        print(message)
    GLOBAL_SETUP_LOGS.append(message)

global intf
intf = "eth0_virt_peer"
global filter
filter = "ether proto 0x893a"
global supported_bands_of_controller
supported_bands_of_controller = 3
global number_of_agents
number_of_agents = 1
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
global CMDU_AP_ERROR
CMDU_AP_ERROR = 0x0055
global expected_renew_count
expected_renew_count = 3

global expected_count_autoconfig_renew
expected_count_autoconfig_renew = number_of_agents * supported_bands_of_controller
global expected_count_wsc
#for one autoconfig renew there will be one m1 wsc and one m2 wsc
expected_count_wsc = expected_count_autoconfig_renew*2
global expected_count_topology_query
expected_count_topology_query = 1
global expected_count_topology_response
expected_count_topology_response = 1
global M2_TYPE
M2_TYPE = 0x05

@pytest.fixture(scope="session", autouse=True)
def test_run_dirs():
    global screenshots_path, reports_path
    #Read from environment (set by main.py)
    run_dir_env = os.environ.get("TEST_RUN_DIR")
    if run_dir_env:
        run_dir = Path(run_dir_env)
    else:
        # Fallback (if someone runs pytest directly)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = BASE_DIR / f"TestRun_{timestamp}"
    screenshots_path = run_dir / "Screenshots"
    reports_path = run_dir / "Reports"
    network_topology_screenshot_path = BASE_DIR / "Network_topology_screenshots"
    #Create all directories
    for path in [screenshots_path, reports_path]:
        path.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Using Test Run Directory: {run_dir}\n")
    return {
        "run_dir": run_dir,
        "screenshots": screenshots_path,
        "reports": reports_path,        
        "network_topology_screenshots": network_topology_screenshot_path
    }

@pytest.fixture(scope="session")
def paths(test_run_dirs):
    return test_run_dirs

def validate_config(cfg):
    if not cfg:
        raise ValueError("Config file is empty or invalid")
    # ---- Controller ----
    ctrl = cfg.get("controller")
    if not ctrl:
        raise ValueError("Missing 'controller' section")
    for field in ["ip", "user"]:
        if not ctrl.get(field):
            raise ValueError(f"Controller missing required field: {field}")
    # ---- Extenders ----
    extenders = cfg.get("extenders", {})
    if not isinstance(extenders, dict):
        raise ValueError("'extenders' must be a dictionary (YAML mapping)")
    for name, ext in extenders.items():
        if not ext.get("ip"):
            raise ValueError(f"Extender '{name}' missing IP")
        if not ext.get("user"):
            raise ValueError(f"Extender '{name}' missing user")
    # ---- Clients ----
    for group in ["wifi_clients", "lan_clients"]:
        clients = cfg.get(group, {})
        if clients and not isinstance(clients, dict):
            raise ValueError(f"'{group}' must be a dictionary")
        
@pytest.fixture(scope="session")
def config():
    filename = BASE_DIR / "config.yaml"
    try:
        with open(filename, "r") as f:
            data = yaml.safe_load(f)
        validate_config(data)
        return data
    except FileNotFoundError:
        pytest.fail(f"Config file not found: {filename}")
    except ValueError as e:
        pytest.fail(f"Config validation error: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error loading config: {e}")

RADIO_CONFIG = [
    {"link_id": 0, "radio": "2_4ghz", "ui_tab": "2_4g", "channel": "10"},
    {"link_id": 1, "radio": "5ghz", "ui_tab": "5g", "channel": "40"},
    {"link_id": 2, "radio": "6ghz", "ui_tab": "6g", "channel": "33"}
]

DB_DEFAULT_DATA = [
    {"haul_id": "Fronthaul", "default_ssid": "private_ssid", "default_pass": "test-fronthaul"},
    {"haul_id": "IoT","default_ssid": "iot_ssid", "default_pass": "test-backhaul"},
    {"haul_id": "Configurator", "default_ssid": "lnf_radius", "default_pass": "test-backhaul"},
    {"haul_id": "Backhaul", "default_ssid": "mesh_backhaul", "default_pass": "test-backhaul"},
    {"haul_id": "Hotspot", "default_ssid": "hotspot", "default_pass": "test-hotspot"}
]

WIFI_RESET_CONFIG = [
    {"haul_id": "Fronthaul", "custom_ssid": "new-fronthaul-ssid", "custom_pass": "new-fronthaul-pass"},
    {"haul_id": "IoT", "custom_ssid": "new-iot-ssid", "custom_pass": "new-iot-pass"},
    {"haul_id": "Configurator", "custom_ssid": "new-configurator-ssid", "custom_pass": "new-configurator-pass"},
    {"haul_id": "Backhaul", "custom_ssid": "new-backhaul-ssid", "custom_pass": "new-backhaul-pass"},
    {"haul_id": "Hotspot", "custom_ssid": "new-hotspot-ssid", "custom_pass": "new-hotspot-pass"}
]

@pytest.fixture(scope="session")
def playwright_instance():
    playwright = sync_playwright().start()
    yield playwright
    playwright.stop()

@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(        
        headless=False
    )
    #channel="msedge" for Edge browser, channel="chrome" for Chrome browser
    yield browser
    browser.close()

@pytest.fixture(scope="function")
def context(browser):
    context = browser.new_context(viewport=None, ignore_https_errors=True)
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(context):
    page = context.new_page()
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)
    yield page
    page.close()

class SSHManager:
    def __init__(self, config):
        self.config = config
        self.controller = None
        self.extenders = {}  # <-- multiple agents

    # ---------- Connect ----------
    def connect(self):
        # ---- Controller ----
        ctrl = self.config["controller"]
        self.controller = paramiko.SSHClient()
        self.controller.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.controller.connect(
            hostname=ctrl["ip"],
            username=ctrl["user"],
            password=ctrl["pass"],
            timeout=20,
            banner_timeout=60,
            auth_timeout=30,
        )

        # ---- Extenders (via tunnel) ----
        transport = self.controller.get_transport()
        for name, ext in self.config.get("extenders", {}).items():
            channel = transport.open_channel(
                "direct-tcpip",
                (ext["ip"], 22),
                ("127.0.0.1", 0),
            )
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=ext["ip"],
                username=ext["user"],
                password=ext["pass"],
                sock=channel,
                timeout=20,
                banner_timeout=60,
            )
            self.extenders[name] = client  # store by name

    # ---------- Execute ----------
    def _execute(self, client, command, sudo_password=None):
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)

        if sudo_password:
            stdin.write(sudo_password + "\n")
            stdin.flush()

        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")

        if sudo_password:
            out = out.replace(sudo_password, "")

        if "Error" in err or "failed" in err.lower():
            pytest.fail(f"Fail: Error executing command: {err}")

        return out.strip()

    # ---------- Run ----------
    def run(self, target, command, sudo_password=None):
        if target == "controller":
            client = self.controller
        else:
            client = self.extenders.get(target)

        if not client:
            pytest.fail(f"Unknown device: {target}")

        return self._execute(client, command, sudo_password)

    # ---------- Dynamic Client Connection ----------
    def connect_client(self, client_ip, client_user, client_password):
        transport = self.controller.get_transport()

        client_channel = transport.open_channel(
            "direct-tcpip",
            (client_ip, 22),
            ("127.0.0.1", 0),
        )

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=client_ip,
            username=client_user,
            password=client_password,
            sock=client_channel,
            timeout=20,
            banner_timeout=60,
        )

        return client  #return instead of storing

    # ---------- Run on any client ----------
    def run_client(self, client_ip, client_user, client_password, command, sudo_password=None):
        client = self.connect_client(client_ip, client_user, client_password)
        try:
            return self._execute(client, command, sudo_password)
        finally:
            client.close()  #avoid leaks

    def download_logfiles_from_controller(self, remote_paths, local_path):
        if not self.controller:
            raise RuntimeError("Controller SSH connection not established")
        # Normalize to list
        if isinstance(remote_paths, str):
            remote_paths = [remote_paths]
        for remote_path in remote_paths:
            filename = os.path.basename(remote_path)
            dest_path = local_path if len(remote_paths) == 1 else os.path.join(local_path, filename)
            try:
                #Step 1: Check if file exists on remote
                stdin, stdout, stderr = self.controller.exec_command(f"test -f {remote_path} && echo EXISTS || echo MISSING")
                result = stdout.read().decode().strip()

                if result != "EXISTS":
                    print(f"[LOG INFO] File does not exist on remote: {remote_path}")
                    continue  # Skip to next file
                #Step 2: Retry SCP download
                for attempt in range(3):
                    try:
                        transport = self.controller.get_transport()
                        if not transport or not transport.is_active():
                            raise RuntimeError("SSH transport is not active")
                        with SCPClient(transport) as scp:
                            scp.get(remote_path, dest_path)
                        print(f"[LOG INFO] Downloaded: {remote_path} -> {dest_path}")
                        break
                    except Exception as e:
                        if attempt == 2:
                            print(f"[LOG ERROR] SCP failed for {remote_path}: {e}")
                        time.sleep(2)
            except Exception as e:
                print(f"[LOG ERROR] Failed processing {remote_path}: {e}")

    # ---------- Cleanup ----------
    def close(self):
        if self.controller:
            self.controller.close()
        for client in self.extenders.values():
            client.close()

@pytest.fixture(scope="session")
def ssh(global_setup):
    # Reuse the session-level SSH manager from global setup to avoid duplicate setup execution and logs.
    yield global_setup

@pytest.fixture(scope="session", autouse=True)
def global_setup(config):
    """
    Runs once before the entire test suite.
    If anything fails, entire execution stops.
    """
    ssh = SSHManager(config)
    try:
        record_global_setup_log("\n[GLOBAL SETUP] Connecting to devices...", print_to_stdout=False)
        ssh.connect()
        record_global_setup_log("[GLOBAL SETUP] Verifying configured VAPs and mesh formation...", print_to_stdout=False)
        
        # Capture output from utility functions
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            utils.validate_all_configured_vaps_are_up(config, ssh)
            utils.verify_mld0_interface_presence(config, ssh, DB_DEFAULT_DATA)
            utils.verify_mld0_links_to_privatevaps(config, ssh, DB_DEFAULT_DATA)
            utils.verify_mesh_backhaul_interfaces(config, ssh, DB_DEFAULT_DATA)
            utils.verify_mesh_backhaul_extenders_connected(config, ssh, DB_DEFAULT_DATA)
        
        # Add captured output to global logs
        output = captured_output.getvalue()
        if output:
            record_global_setup_log(output, print_to_stdout=False)
        
        record_global_setup_log("[GLOBAL SETUP] Setup successful", print_to_stdout=False)
    except Exception as e:
        record_global_setup_log(f"[GLOBAL SETUP FAILED] {str(e)}", print_to_stdout=False)
        pytest.exit(
            f"\n[GLOBAL SETUP FAILED]\n{str(e)}",
            returncode=1
        )
    yield ssh
    record_global_setup_log("\n[GLOBAL TEARDOWN] Closing SSH connections...", print_to_stdout=False)
    ssh.close()


def pytest_html_results_summary(prefix, summary, postfix):
    if not GLOBAL_SETUP_LOGS:
        return

    formatted_logs = "<br>".join(escape(line) for line in GLOBAL_SETUP_LOGS)
    summary.extend([
        "<h2>Global Setup</h2>",
        (
            "<div style='white-space: pre-wrap; font-family: monospace;'>"
            f"{formatted_logs}"
            "</div>"
        ),
    ])

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        errors = getattr(item, "error_logs", [])
        if errors:
            report.outcome = "failed"
            report.longrepr = "Error logs found:\n" + "\n".join(errors)
        #Attach report to item (so fixture can read it)
        setattr(item, "rep_call", report)

        extra = getattr(report, "extra", [])
        if report.failed:
            message = f'<span style="color:red; font-weight:bold;">FAIL</span>'
        elif report.passed:
            message = '<span style="color:green; font-weight:bold;">PASS</span>'
        elif report.skipped:
            message = '<span style="color:orange; font-weight:bold;">SKIPPED</span>'
        else:
            message = '<span>UNKNOWN</span>'

        extra.append(pytest_html.extras.html(message))
        report.extra = extra

_ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _strip_ansi(text):
    return _ANSI_ESCAPE.sub('', text)

def pytest_html_results_table_html(report, data):
    if report.when not in ("call", "setup", "teardown"):
        return

    new_data = []

    # Add failure traceback for call phase
    if report.failed and report.when == "call":
        if hasattr(report, "longrepr"):
            new_data.append(f"<div>{escape(str(report.longrepr))}</div>")

    # Add formatted logs from captured stdout
    stdout = getattr(report, "capstdout", "") or ""
    if stdout.strip():
        lines = _strip_ansi(stdout).splitlines()
        formatted_lines = []
        for line in lines:
            escaped_line = escape(line)
            if "PASS:" in line:
                formatted_lines.append(
                    f'<span style="color:green; font-weight:bold;">{escaped_line}</span>'
                )
            elif "FAIL:" in line:
                formatted_lines.append(
                    f'<span style="color:red; font-weight:bold;">{escaped_line}</span>'
                )
            else:
                formatted_lines.append(escaped_line)
        html = "<br>".join(formatted_lines)
        new_data.append(f"<div>{html}</div>")

    if new_data:
        data.clear()
        data.extend(new_data)