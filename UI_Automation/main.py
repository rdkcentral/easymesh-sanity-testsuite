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
import datetime
from pathlib import Path
import os

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = BASE_DIR / f"TestRun_{timestamp}"
    #Set environment variable
    os.environ["TEST_RUN_DIR"] = str(run_dir)
    # Reports path (needed BEFORE pytest starts)
    reports_path = run_dir / "Reports"
    reports_path.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Test Run Dir: {run_dir}\n")    
    pytest.main([
        "-v",
        f"{BASE_DIR}/test_basic_sanity_tc.py",
        f"{BASE_DIR}/test_network_topology.py",
        f"{BASE_DIR}/test_wifi_client_connectivity.py",
        f"{BASE_DIR}/test_lan_client_connectivity.py",
        f"{BASE_DIR}/test_em_functionality.py",
        f"--html={reports_path}/sanity_report.html",
        "--self-contained-html"
    ])