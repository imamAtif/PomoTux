"""Fail unless the version is identical in all release files.

Run: python packaging/check_version.py (also runs in CI).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> int:
    code = (ROOT / "pomotux" / "__init__.py").read_text()
    spec = (ROOT / "pomotux.spec").read_text()
    changelog = (ROOT / "debian" / "changelog").read_text().splitlines()[0]

    versions = {
        "pomotux/__init__.py": re.search(r'__version__ = "([^"]+)"', code).group(1),
        "pomotux.spec": re.search(r"^Version:\s*(\S+)", spec, re.M).group(1),
        "debian/changelog": re.search(r"\(([^)]+)\)", changelog).group(1).split("-")[0],
    }
    for where, ver in versions.items():
        print(f"{where}: {ver}")
    if len(set(versions.values())) != 1:
        print("MISMATCH: bump all three to the same version", file=sys.stderr)
        return 1
    print("VERSIONS_IN_SYNC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
