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
        f"{BASE_DIR}/test_wifi_client_connectivity.py",
        f"{BASE_DIR}/test_lan_client_connectivity.py",
        f"{BASE_DIR}/test_network_topology.py",
        f"{BASE_DIR}/test_em_functionality.py",
        f"--html={reports_path}/sanity_report.html",
        "--self-contained-html"
    ])