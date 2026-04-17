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

import time
from UI_Automation.utils import print_success, print_error

def capture_packets(ssh, interface, filter, snap_length, capture_file_location):
    cmd = f"nohup tcpdump -i {interface} {filter} -s {snap_length} -w {capture_file_location} > /dev/null 2>&1 & echo $!"
    pid = ssh.run("controller", cmd).strip()
    print_success(f"Packet capture started with PID: {pid}")
    time.sleep(5)
    if not pid:
        print_error("Failed to start packet capture. No PID returned.")
    return pid

def stop_packet_capture(ssh, pid):
    out = ssh.run("controller", f"kill -2 {pid}")
    time.sleep(5)  # Wait for tcpdump to flush and close the pcap file
    print_success(f"Packet capture stopped for PID {pid}.")

def transfer_capfile_from_device(ssh, remote_file_location, local_file_location):
    ret = ssh.download_from_controller(remote_file_location, local_file_location)
    print_success(f"Captured file transferred from device: {remote_file_location} to local machine: {local_file_location}")
    return ret
