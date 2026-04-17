import pytest
import datetime
from pathlib import Path
import sys
import os

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(BASE_DIR.parent))
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
        f"{BASE_DIR}/test_ssid_update_capture_analysis.py",
        f"--html={reports_path}/ssid_update_capture_analysis.html",
        "--self-contained-html"
    ])