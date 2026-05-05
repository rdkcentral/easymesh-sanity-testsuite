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

import pytest
import utils
from utils import print_step, print_error, print_success

#@pytest.mark.skip(reason="Feature to be tested with LAN client device")
def test_lan_client_connectivity(config, request, ssh):
    print_step("Entering Test1: test_lan_client_connectivity")    
    lan_client_list = list(config.get("lan_clients", {}).keys())
    for idx, lan_client in enumerate(lan_client_list, start=1):
        print_step(f"\nStep 1: Verify LAN client {idx} obtained IP address from fronthaul network")
        lan_client_mac = config["lan_clients"][lan_client].get("mac", "")
        lan_client_user = config["lan_clients"][lan_client].get("user", "")
        lan_client_pass = config["lan_clients"][lan_client].get("pass", "")
        if lan_client_mac == "":
            pytest.fail(f"LAN client {idx} with MAC {lan_client_mac} is not present in the configuration")

        # Retrieve client details from controller
        fetch_index_cmd = f"""dmcli eRT getv Device.Hosts.Host. | grep -i '{lan_client_mac}' -B 1 | grep -v '^--$' | head -n 1 | awk -F'.' '{{print $(NF-1)}}'"""
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
            pytest.fail(f"LAN Client {idx} not connected properly. Client IP: {client_ip}, Interface: {interface}, Active: {active_status}")
        #Fetch the interface with the MAC address from LAN client device using ifconfig command to further validate the connectivity status of the client
        cmd = f"/usr/sbin/ifconfig | awk '/^[a-zA-Z0-9]/ {{iface=$1}} /{lan_client_mac}/ {{print iface}}'"
        iface_out = ssh.run_client(client_ip, lan_client_user, lan_client_pass, cmd)
        iface_out = iface_out.strip(":")
        if iface_out:
            print_success(f"LAN Client {idx} with MAC {lan_client_mac} is connected via interface {iface_out}")
        else:
            pytest.fail(f"LAN Client {idx} with MAC {lan_client_mac} is not connected via Ethernet interface. ifconfig output: {iface_out}")
        # Verify client IP on client device
        cmd = f"/usr/sbin/ifconfig {iface_out} | awk '/inet / {{print $2}}'"
        client_ip_out = ssh.run_client(client_ip, lan_client_user, lan_client_pass, cmd)
        if not client_ip_out.strip():
            pytest.fail(f"LAN Client {idx} did not obtain IP address. Output: {client_ip_out}")
        else:
            print_success(f"LAN Client {idx} obtained IP {client_ip_out.strip()} successfully")
        print_step("Step 2: Verify LAN client internet connectivity")
        ping_out = ssh.run_client(client_ip, lan_client_user, lan_client_pass, "ping -c 5 www.google.com")
        print(f"Ping output:\n{ping_out}")
        if "0% packet loss" not in ping_out:
            print_error(request, f"LAN Client {idx} with MAC {lan_client_mac} has no internet connectivity. Ping output: {ping_out}")
        else:
            print_success(f"LAN Client {idx} with MAC {lan_client_mac} has internet connectivity")
    print_step("Exiting Test1: test_lan_client_connectivity")