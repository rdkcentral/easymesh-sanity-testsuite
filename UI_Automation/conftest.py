/**
 * If not stated otherwise in this file or this component LICENSE file the
 * following copyright and licenses apply:
 *
 * Copyright 2026 RDK Management
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

from urllib import request
import pytest
from playwright.sync_api import sync_playwright
import paramiko
from pathlib import Path
import pytest_html
import time
from scp import SCPClient
import datetime
import os

BASE_DIR = Path(__file__).resolve().parent
screenshots_path = None
reports_path = None
failure_logs_path = None

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
    global screenshots_path, reports_path, failure_logs_path
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
    failure_logs_path = run_dir / "Failed_Logs"
    network_topology_screenshot_path = BASE_DIR / "Network_topology_screenshots"
    #Create all directories
    for path in [screenshots_path, reports_path, failure_logs_path]:
        path.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Using Test Run Directory: {run_dir}\n")
    return {
        "run_dir": run_dir,
        "screenshots": screenshots_path,
        "reports": reports_path,
        "logs": failure_logs_path,
        "network_topology_screenshots": network_topology_screenshot_path
    }

@pytest.fixture(scope="session")
def paths(test_run_dirs):
    return test_run_dirs

@pytest.fixture(scope="session", autouse=True)
def global_config(request):
    #Controller details
    request.session.ctrl_ip = ""
    request.session.ctrl_user = ""
    request.session.ctrl_pass = ""
    request.session.key_file = None
    #Extender details
    request.session.ext1_ip = ""
    request.session.ext1_user = ""
    request.session.ext1_pass = ""
    request.session.passphrase = ""
    #Wi-Fi client details
    request.session.client_ip = ""
    request.session.client_user = ""
    request.session.client_pass = ""
    request.session.bridge_intf ="brlan0"
    #LAN client details
    request.session.lan_client_mac = ""
    request.session.lan_client_user = ""
    request.session.lan_client_pass = ""
    #Database details
    request.session.easy_mesh_db = "OneWifiMesh"
    request.session.db_user = ""
    request.session.db_pass = ""
    request.session.network_ssid_list_db_table = "NetworkSSIDList"
    request.session.wifi_reset_interface = "eth0_virt_peer"
    request.session.reset_json_file = "/usr/ccsp/EasyMesh/Reset.json"

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
    def __init__(self, request):
        self.req = request.session
        self.controller = None
        self.agent = None

    # ---------- Controller + Agent ----------
    def connect(self):
        self.controller = paramiko.SSHClient()
        self.controller.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_args = dict(
            hostname=self.req.ctrl_ip,
            username=self.req.ctrl_user,
            timeout=20,
            banner_timeout=60,
            auth_timeout=30
        )

        if self.req.key_file:
            connect_args["key_filename"] = self.req.key_file
        else:
            connect_args["password"] = self.req.ctrl_pass

        self.controller.connect(**connect_args)

        # ---------- Tunnel to Agent ----------
        transport = self.controller.get_transport()

        agent_channel = transport.open_channel(
            "direct-tcpip",
            (self.req.ext1_ip, 22),
            ("127.0.0.1", 0),
        )

        self.agent = paramiko.SSHClient()
        self.agent.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.agent.connect(
            hostname=self.req.ext1_ip,
            username=self.req.ext1_user,
            password=self.req.ext1_pass,
            sock=agent_channel,
            timeout=20,
            banner_timeout=60,
        )

    # ---------- Generic execute ----------
    def _execute(self, client, command, sudo_password=None):
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        # Send sudo password if required
        if sudo_password:
            stdin.write(sudo_password + "\n")
            stdin.flush()
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        # Remove password if echoed (safety cleanup)
        if sudo_password:
            out = out.replace(sudo_password, "")
        out = out.strip()
        err = err.strip()
        if "Error" in err or "failed" in err.lower():
            pytest.fail(f"Fail: Error executing command: {err}")
        return out

    # ---------- Controller/Agent run ----------
    def run(self, target, command, sudo_password=None):
        client = {
            "controller": self.controller,
            "agent": self.agent
        }[target]

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

    def copy_agent_logs_to_controller(self, agent_paths, controller_dir="/tmp"):
        if not self.controller or not self.agent:
            raise RuntimeError("SSH connections not established")        
        for remote_path in agent_paths:
            filename = os.path.basename(remote_path)
            dest_path = f"{controller_dir}/{filename}"
            try:
                # Check if file exists on agent
                stdin, stdout, stderr = self.agent.exec_command(f"test -f {remote_path} && echo EXISTS || echo MISSING")
                result = stdout.read().decode().strip()
                if result != "EXISTS":
                    print(f"[AGENT INFO] Missing: {remote_path}")
                    continue
                # Copy agent -> controller (runs on controller)
                scp_cmd = (f"scp -o StrictHostKeyChecking=no "f"{self.req.ext1_user}@{self.req.ext1_ip}:{remote_path} {dest_path}")
                stdin, stdout, stderr = self.controller.exec_command(scp_cmd)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code == 0:
                    print(f"[AGENT -> CTRL] {remote_path} -> {dest_path}")
                else:
                    err = stderr.read().decode()
                    print(f"[AGENT ERROR] SCP failed: {err}")
            except Exception as e:
                print(f"[AGENT ERROR] Failed copying {remote_path}: {e}")

    # ---------- Cleanup ----------    
    def close(self):
        for c in [self.agent, self.controller]:
            if c:
                c.close()

@pytest.fixture(scope="session")
def ssh(request):
    manager = SSHManager(request)
    manager.connect()
    yield manager
    manager.close()

@pytest.fixture(autouse=True)
def collect_device_logs_on_failure(request, ssh):
    """
    Runs after each test.
    If test fails:
        - Creates a folder with test name + timestamp
        - Copies predefined device logs into that folder
    """
    yield  # Run the test first
    report = getattr(request.node, "rep_call", None)
    if report and report.failed:
        test_name = request.node.name
        # Unique folder to avoid overwrite
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir = os.path.join(f"{failure_logs_path}", f"{test_name}_{timestamp}")
        agent_test_dir = os.path.join(test_dir, "Agent_Logs")
        os.makedirs(agent_test_dir, exist_ok=True)
        controller_logs = ["/tmp/ieee1905_agent_log.txt", "/tmp/ieee1905_ctrl_log.txt", "/tmp/em_agent.log", "/tmp/em_cli.log", "/tmp/em_ctrl.log", "/rdklogs/logs/WiFilog.txt.0", "/rdklogs/logs/WiFilog.txt.1", "/rdklogs/logs/wifiCtrl.txt", "/rdklogs/logs/wifiDMCLI.txt", "/rdklogs/logs/wifiEM.txt", "/rdklogs/logs/wifiHal.txt", "/rdklogs/logs/wifiHalStats.txt", "/rdklogs/logs/wifiMgr.txt"]
        agent_logs = ["/tmp/ieee1905_agent_log.txt", "/tmp/em_agent.log", "/rdklogs/logs/WiFilog.txt.0", "/rdklogs/logs/WiFilog.txt.1", "/rdklogs/logs/wifiCtrl.txt", "/rdklogs/logs/wifiDMCLI.txt", "/rdklogs/logs/wifiEM.txt", "/rdklogs/logs/wifiHal.txt", "/rdklogs/logs/wifiHalStats.txt", "/rdklogs/logs/wifiMgr.txt", "/rdklogs/logs/emAgent.txt"]
        try:
            #Step 1: Copy agent logs to controller (/tmp)
            ssh.copy_agent_logs_to_controller(agent_logs, "/tmp")
            #Step 2: Download controller logs
            for remote_path in controller_logs:
                filename = os.path.basename(remote_path)
                local_path = os.path.join(test_dir, filename)
                try:
                    ssh.download_logfiles_from_controller(remote_path, local_path)
                except Exception as e:
                    print(f"[CTRL ERROR] {remote_path}: {e}")
            #Step 3: Download staged agent logs from controller
            for remote_path in agent_logs:
                staged_path = f"/tmp/{os.path.basename(remote_path)}"
                local_path = os.path.join(agent_test_dir, os.path.basename(remote_path))
                try:
                    ssh.download_logfiles_from_controller(staged_path, local_path)
                except Exception as e:
                    print(f"[AGENT ERROR] {staged_path}: {e}")
        except Exception as e:
            print(f"[LOG ERROR] Failure in log collection: {e}")

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

def pytest_html_results_table_html(report, data):
    if report.when == "call":

        new_data = []

        #Add failure traceback manually
        if report.failed:
            if hasattr(report, "longrepr"):
                new_data.append(f"<div>{report.longrepr}</div>")

        #Add formatted logs
        if hasattr(report, "capstdout"):
            log = report.capstdout
            lines = log.splitlines()
            formatted_lines = []

            for line in lines:
                if "PASS:" in line:
                    formatted_lines.append(
                        f'<span style="color:green; font-weight:bold;">{line}</span>'
                    )
                elif "FAIL:" in line:
                    formatted_lines.append(
                        f'<span style="color:red; font-weight:bold;">{line}</span>'
                    )
                else:
                    formatted_lines.append(line)

            html = "<br>".join(formatted_lines)
            new_data.append(f"<div>{html}</div>")
        # Replace everything
        data.clear()
        data.extend(new_data)
