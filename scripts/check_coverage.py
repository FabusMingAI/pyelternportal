"""Keep the extracted modules covered independently of the HA adapter."""

import json
import sys
from pathlib import Path


def check(report: dict) -> list[str]:
    """Reject missing modules, excluded runtime code and weak coverage."""
    errors = []
    for module, minimum in [("client", 95), ("counts", 100), ("registrations", 100)]:
        matches = [
            data
            for name, data in report["files"].items()
            if name.replace("\\", "/").endswith(f"pyelternportal/{module}.py")
        ]
        if len(matches) != 1:
            errors.append(f"{module}: expected exactly one measured module")
            continue
        data = matches[0]
        covered = data["summary"]["covered_lines"]
        total = data["summary"]["num_statements"]
        if data.get("excluded_lines"):
            errors.append(f"{module}: excluded lines are not permitted")
        passed = covered == total if minimum == 100 else covered * 100 > total * minimum
        if total <= 0 or not passed:
            errors.append(
                f"{module}: {covered}/{total} lines; requires "
                + ("100%" if minimum == 100 else "strictly above 95%")
            )
    return errors


if __name__ == "__main__":
    failures = check(json.loads(Path(sys.argv[1]).read_text()))
    for failure in failures:
        print(failure)
    if failures:
        raise SystemExit(1)
    print("PASS: client >95%; counts and registrations 100%; no excluded runtime lines")
