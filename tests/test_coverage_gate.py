"""Check the boundary which a rounded aggregate percentage can hide."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_spec = spec_from_file_location(
    "coverage_gate", Path(__file__).parents[1] / "scripts/check_coverage.py"
)
_gate = module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def report():
    return {
        "files": {
            f"/installed/pyelternportal/{name}.py": {
                "summary": {"covered_lines": covered, "num_statements": 100},
                "excluded_lines": [],
            }
            for name, covered in [
                ("client", 96),
                ("counts", 100),
                ("registrations", 100),
            ]
        }
    }


def test_strict_threshold_and_full_coverage_requirements():
    data = report()
    assert not _gate.check(data)
    data["files"]["/installed/pyelternportal/client.py"]["summary"]["covered_lines"] = (
        95
    )
    assert _gate.check(data)
    data = report()
    data["files"]["/installed/pyelternportal/counts.py"]["summary"]["covered_lines"] = (
        99
    )
    assert _gate.check(data)


def test_missing_duplicate_and_excluded_modules_fail():
    data = report()
    del data["files"]["/installed/pyelternportal/registrations.py"]
    assert _gate.check(data)
    data = report()
    data["files"]["/source/pyelternportal/client.py"] = deepcopy(
        data["files"]["/installed/pyelternportal/client.py"]
    )
    assert _gate.check(data)
    data = report()
    data["files"]["/installed/pyelternportal/client.py"]["excluded_lines"] = [3]
    assert _gate.check(data)
