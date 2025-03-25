"""
Data structures for representing certain Unicode tables.
The actual tables are created in the (generated) _data.py file.
"""

from collections.abc import Iterator
from enum import IntEnum
from itertools import chain
from typing import TypeVar

from ._rangemap import RangeMap

CodePoint = int
CodePointRange = tuple[CodePoint, CodePoint]
CodePointList = list[CodePoint | CodePointRange]


V = TypeVar("V")


def _expand_codepoint_list(
    keys: CodePointList, value: V
) -> Iterator[tuple[CodePointRange, V]]:
    """
    Converts _data.py compact representations to RangeMap initializers.
    Given a list of keys that can be a mixture of individual CodePoints
    and (start, end) CodePointRange tuples, plus a value, generate
    a sequence of ((start, end), value) tuples.
    """
    for key in keys:
        if isinstance(key, tuple):
            yield key, value
        else:
            yield (key, key), value


class Status(IntEnum):
    """UTS46 IDNA Mapping Table status (column 2) for a codepoint."""

    VALID = 0
    IGNORED = 1
    MAPPED = 2
    DEVIATION = 3
    DISALLOWED = 4

    def __str__(self) -> str:
        return self.name.lower()


class Uts46MappingTable:
    """
    UTS46 Non-transitional IDNA Mapping Table

    This implementation is intended to minimize the size of the initialization
    data and memory usage, while maintaining fast lookup.

    Initialization data is:
    - Lists of `valid` and `ignored` codepoint ranges.
      - Each list can mix (int, int) tuple ranges and single codepoints.
      - Deviation codepoints must be included in the `valid` ranges (see below).
    - A dict of `mapped` codepoints, whose values are the mapped strings.
    - A list of `offset` codepoint ranges, which defines "mapped" codepoints
      at a fixed offset from the original codepoint. (This is an optimization
      that reduces the size of the `mapped` dict.)
    - All other codepoints are treated as disallowed.

    For non-transitional processing, deviation codepoints are handled the same
    as valid ones. So as an optimization, they are just stored as valid here.
    (See UTS46 section 4 processing step 1 and section 4.1 validation step 7.)
    """

    # Version of UTS46 IDNA Mapping Table used to generate this data.
    data_version: str

    # Python unicodedata.unidata_version during data generation.
    unidata_version: str

    # The Status or offset for each codepoint
    _cp_status: RangeMap[CodePoint, Status | int]
    _mapped: dict[CodePoint, str]
    _default_status = Status.DISALLOWED

    def __init__(
        self,
        *,
        valid: CodePointList,
        ignored: CodePointList,
        offset: list[tuple[CodePointRange, int]],
        mapped: dict[CodePoint, str],
        data_version: str | None = None,
        unidata_version: str | None = None,
    ):
        self._cp_status = RangeMap(
            chain(
                _expand_codepoint_list(valid, Status.VALID),
                _expand_codepoint_list(ignored, Status.IGNORED),
                offset,
            )
        )
        self._mapped = mapped
        self.data_version = data_version or ""
        self.unidata_version = unidata_version or ""

    def status(self, char: str) -> Status:
        """
        Return the IDNA Mapping Table status for char's codepoint.
        Deviation characters return Status.VALID.
        """
        cp = ord(char)
        if cp in self._mapped:
            return Status.MAPPED
        _status = self._cp_status.get(cp, self._default_status)
        if not isinstance(_status, Status):
            _status = Status.MAPPED  # offset means mapped
        return _status

    def is_valid(self, char: str) -> bool:
        """
        Return True if char is valid per UTS46 section 4.1 validity criteria
        step 7 item 2 (non-transitional processing).
        """
        return self.status(char) == Status.VALID

    def __getitem__(self, char: str) -> str:
        """
        Implement UTS46 section 4 Processing step 1 mapping for _non-transitional_
        processing. Return the string which should replace char in the domain name.
        """
        cp = ord(char)
        result = self._mapped.get(cp)
        if result is None:
            status = self._cp_status.get(ord(char), self._default_status)
            if status in {Status.VALID, Status.DISALLOWED}:
                result = char
            elif status == Status.IGNORED:
                result = ""
            elif not isinstance(status, Status):
                result = chr(cp + status)  # offset
            else:
                # Status.MAPPED was covered by _mapped or offset above.
                # Status.DEVIATION should use VALID in non-transitional table.
                raise ValueError(f"Unknown status for {cp:#06x}: {status!r}")
        return result


class Uts46TransitionalMappingTable:
    """
    UTS46 Transitional IDNA Mapping Table

    Extends the non-transitional mapping table with overrides for deviation
    characters. In transitional processing, deviations are handled as mappings.
    (See UTS46 section 4 processing step 1 and section 4.1 validation step 7.)

    The `deviations` dict must include:
    - Mappings for all codepoints with status 'deviation' in the IDNA mapping table.
    - The "exceptional change" from section 5 mapping U+1E9E capital sharp s (ẞ)
      to "ss" for transitional processing.
    """

    def __init__(self, base: Uts46MappingTable, deviations: dict[CodePoint, str]):
        self.base = base
        self.deviations: dict[str, str] = {
            chr(cp): value for cp, value in deviations.items()
        }

    def status(self, char: str) -> Status:
        """
        Return the IDNA Mapping Table status for char's codepoint.
        """
        if char in self.deviations:
            return Status.DEVIATION
        return self.base.status(char)

    def is_valid(self, char: str) -> bool:
        """
        Return True if char is valid per UTS46 section 4.1 validity criteria
        step 7 item 1 (transitional processing).
        """
        return self.status(char) == Status.VALID

    def __getitem__(self, char: str) -> str:
        """
        Implement UTS46 section 4 Processing step 1 mapping for _transitional_
        processing. Return the string which should replace char in the domain name.
        """
        try:
            return self.deviations[char]
        except KeyError:
            return self.base[char]


class JoiningTypes:
    """
    UTR44 Joining Types data from the Unicode Character Database.
    (This data is not included in Python's unicodedata module.)

    Initialization data is single-char keyword args representing
    the joining type (in lowercase -- 'c', 'd', 'r', etc.), where the value
    of each arg is a list of mixed (start, end) ranges and single codepoints.
    """

    # Version of Unicode database used to generate this data.
    data_version: str

    _joining_type: RangeMap[CodePoint, str]

    def __init__(
        self, *, data_version: str | None = None, **kwargs: CodePointList
    ) -> None:
        # Each kwarg is a CodePointList of its lowercase joining type code.
        assert all(len(code.upper()) == 1 for code in kwargs.keys())
        self._joining_type = RangeMap(
            chain.from_iterable(
                _expand_codepoint_list(cplist, code.upper())
                for code, cplist in kwargs.items()
            )
        )
        self.data_version = data_version or ""

    def __getitem__(self, char: CodePoint | str) -> str:
        """
        Return the joining type assigned to the character or codepoint,
        or an empty string if no joining type is defined.
        """
        cp = ord(char) if isinstance(char, str) else char
        return self._joining_type.get(cp, "")

    def get(self, char: CodePoint | str, default: str = "") -> str:
        """
        Return the joining type assigned to the character or codepoint,
        or default if no joining type is defined.
        """
        cp = ord(char) if isinstance(char, str) else char
        return self._joining_type.get(cp, default)
