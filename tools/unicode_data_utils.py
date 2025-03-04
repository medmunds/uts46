"""Common utilities for parsing Unicode Consortium data files"""

import os
import re
import sys
import urllib.request
from collections.abc import Iterator
from pathlib import Path

# Unicode data file URLs
IDNA_MAPPING_TABLE_URL = (
    "https://www.unicode.org/Public/idna/{version}/IdnaMappingTable.txt"
)
IDNA_CONFORMANCE_TEST_URL = (
    "https://www.unicode.org/Public/idna/{version}/IdnaTestV2.txt"
)
DERIVED_JOINING_TYPE_URL = (
    "https://www.unicode.org/Public/{version}/ucd/extracted/DerivedJoiningType.txt"
)

# Data directory for caching downloaded files
DATA_DIR = Path(__file__).parent.parent / "data"

# Keep track of downloaded file source in comment at end of file
SOURCE_URL_PREFIX = "# Source-URL:"


def get_source_url(file_path: Path, *, look_back: int = 1024) -> str | None:
    """
    Return the source URL from a downloaded Unicode data file, if it exists.
    (Only checks the last `look_back` bytes in the file.)
    """
    # ("b" mode is required to perform negative seeks.)
    with file_path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(max(-look_back, -file_size), os.SEEK_END)
        raw_lines = f.readlines()
        for raw_line in reversed(raw_lines):
            line = raw_line.decode().strip()
            if line.startswith(SOURCE_URL_PREFIX):
                return line[len(SOURCE_URL_PREFIX) :].strip()
    return None


def get_unicode_file(
    url: str, *, force_download: bool = False, version: str | None = None
) -> tuple[Path, str]:
    """
    Get a Unicode data file, downloading it if necessary.
    Downloaded files are cached in DATA_DIR.

    `url` is the full URL to the file. It may include a "{version}" placeholder
    that will be replaced with `version`
    e.g., "https://www.unicode.org/Public/{version}/ucd/UnicodeData.txt".

    If `force_download` is False (the default), returns a cached copy
    from DATA_DIR if it exists and was retrieved from the same URL.

    Returns the Path to the downloaded file and the URL from which it was downloaded.
    """
    if "{version}" in url:
        if version is None:
            raise ValueError(
                "version must be specified when using {version} placeholder in url"
            )
        url = url.format(version=version)

    file_path = DATA_DIR / Path(url).name
    if force_download or not file_path.exists() or get_source_url(file_path) != url:
        print(f"Downloading {url}", file=sys.stderr)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, file_path)
        # Append the source url
        with file_path.open("a", encoding="utf-8") as f:
            f.write(f"\n{SOURCE_URL_PREFIX} {url}\n")
    else:
        print(f"Using cached {file_path}", file=sys.stderr)
    return file_path, url


def unescape_string(s: str) -> str:
    """Unescape \u0000 and \x00 escape sequences in a string."""
    return re.sub(
        r"\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})",
        lambda m: chr(int(m.group(1) or m.group(2), 16)),
        s,
    )


def parse_codepoint_field(field: str) -> tuple[int, int]:
    """
    Parse a codepoint or codepoint range field into a (start, end) tuple.

    field may be a string representing a single codepoint (e.g., "0041")
    or a codepoint range separated by ".." (e.g., "0041..005A").
    """
    if ".." in field:
        start, end = field.split("..")
        return int(start, 16), int(end, 16)
    else:
        cp = int(field, 16)
        return cp, cp


def parse_codepoint_sequence_field(field: str) -> str:
    """
    Parse a sequence of whitespace separated codepoints into a string.

    E.g., "0041 0042 0043" -> "ABC"
    """
    cps = [int(cp, 16) for cp in field.split()]
    return "".join(chr(cp) for cp in cps)


def parse_line_with_comment(line: str) -> tuple[str, str | None]:
    """Parse a line that may contain a "#" comment. Returns (content, comment)."""
    line = line.strip()
    comment = None
    content = line
    if "#" in line:
        content, comment = line.split("#", 1)
        comment = comment.strip()
        content = content.strip()
    return content, comment


def parse_semicolon_fields(line: str) -> list[str]:
    """
    Parse semicolon-delimited fields from a line.
    Strips leading/trailing whitespace.
    """
    return [field.strip() for field in line.split(";")]


def parse_data_file(
    file_path: Path, skip_blank: bool = True
) -> Iterator[tuple[int, str, str | None]]:
    """
    Parse a Unicode data file, yielding (line_number, content, comment) tuples.

    If `skip_blank` is True, skips empty lines and those that contain only a comment.
    Otherwise, yields (line_number, "", comment) for those lines.
    """
    with file_path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            content, comment = parse_line_with_comment(line)
            if skip_blank and not content:
                continue
            yield line_num, content, comment
