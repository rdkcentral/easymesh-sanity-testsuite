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

import pytest
import utils
from utils import print_step, print_error, print_success
import conftest

#@pytest.mark.skip(reason="Feature to be tested with LAN client device")
def test_lan_client_connectivity(request, ssh):
    print_step("Entering Test1: test_lan_client_connectivity")
    print_step("Step 1: Verify LAN client obtained IP address from fronthaul network")
    # Retrieve client details from controller
    fetch_index_cmd = f"""dmcli eRT getv Device.Hosts.Host. | grep -i '{request.session.lan_client_mac}' -B 1 | grep -v '^--$' | head -n 1 | awk -F'.' '{{print $(NF-1)}}'"""
    index = ssh.run("controller", fetch_index_cmd).strip()
    print(f"Client index command is {fetch_index_cmd} and output retrieved from controller: {index}")
    ip_cmd = f"dmcli eRT getv Device.Hosts.Host.{index}.IPAddress | sed -n 's/.*value: *//p'"
    intf_cmd = f"dmcli eRT getv Device.Hosts.Host.{index}.Layer1Interface | sed -n 's/.*value: *//p'"
    active_cmd = f"dmcli eRT getv Device.Hosts.Host.{index}.Active | sed -n 's/.*value: *//p'"
    client_ip = ssh.run("controller", ip_cmd)
    interface = ssh.run("controller", intf_cmd)
    active_status = ssh.run("controller", active_cmd)
    client_ip = client_ip.strip()
    interface = interface.strip()
    active_status = active_status.strip()
    print(f"Client IP: {client_ip}")
    print(f"Interface: {interface}")
    print(f"Active Status: {active_status}")
    if not client_ip or interface != "Ethernet" or active_status.lower() != "true":
        pytest.fail(f"LAN Client not connected properly. Client IP: {client_ip}, Interface: {interface}, Active: {active_status}")
    # Verify client IP on client device
    cmd = "ifconfig | awk '/inet / {print $2}'"
    client_ip_out = ssh.run_client(client_ip, request.session.lan_client_user, request.session.lan_client_pass, cmd)
    if not client_ip_out.strip():
        pytest.fail(f"LAN Client did not obtain IP address. Output: {client_ip_out}")
    print_success(f"LAN Client obtained IP {client_ip_out.strip()} successfully")
    print_step("Step 2: Verify LAN client internet connectivity")
    ping_out = ssh.run_client(client_ip, request.session.lan_client_user, request.session.lan_client_pass, "ping -c 5 www.google.com")
    print(f"Ping output:\n{ping_out}")
    if "0% packet loss" not in ping_out:
        print_error(request, f"LAN Client has no internet connectivity. Ping output: {ping_out}")
    else:
        print_success("LAN Client has internet connectivity")
    print_step("Exiting Test1: test_lan_client_connectivity")
