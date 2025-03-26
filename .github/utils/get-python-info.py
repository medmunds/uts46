#!/usr/bin/env python
"""
Create GitHub workflow output variables describing the running Python version.
"""

import os
import sys
from collections.abc import Mapping
from typing import Any, TextIO, TypedDict

OutputVariables = TypedDict(
    "OutputVariables",
    {
        "python-prerelease": bool,  # anything before final
        "python-release-level": str,
        "python-version-string": str,
    },
)


def collect_info() -> OutputVariables:
    releaselevel = sys.version_info.releaselevel
    return {
        "python-prerelease": releaselevel != "final",
        "python-release-level": releaselevel,
        "python-version-string": sys.version,
    }


def write_output(f: TextIO, info: Mapping[str, Any]) -> None:
    for name, value in info.items():
        # GitHub expects JSON-esque literals for bool and None
        if value is None:
            value = "null"
        elif isinstance(value, bool):
            value = "true" if value else "false"
        f.write(f"{name}={value}\n")


def main() -> None:
    info = collect_info()
    github_output_path = os.environ.get("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a") as f:
            write_output(f, info)
    else:
        write_output(sys.stdout, info)


if __name__ == "__main__":
    main()
