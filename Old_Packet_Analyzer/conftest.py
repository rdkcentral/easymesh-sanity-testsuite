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

import re
from html import escape

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text):
    return _ANSI_ESCAPE.sub("", text)


def pytest_html_results_table_html(report, data):
    if report.when not in ("call", "setup", "teardown"):
        return

    new_data = []

    # Keep traceback visibility for failures.
    if report.failed and report.when == "call" and hasattr(report, "longrepr"):
        new_data.append(f"<div>{escape(str(report.longrepr))}</div>")

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

        new_data.append(f"<div>{'<br>'.join(formatted_lines)}</div>")

    if new_data:
        data.clear()
        data.extend(new_data)
