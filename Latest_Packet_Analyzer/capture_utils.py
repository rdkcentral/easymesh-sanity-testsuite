import pytest
import time
import ieee1905_utils
from ieee1905_utils import print_success, print_error

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
    print_success(f"Packet capture stopped for PID {pid}.")

def transfer_capfile_from_device(ssh, remote_file_location, local_file_location):
    ret = ssh.download_from_controller(remote_file_location, local_file_location)
    print_success(f"Captured file transferred from device: {remote_file_location} to local machine: {local_file_location}")
    return ret