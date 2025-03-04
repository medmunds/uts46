import unittest
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from tools import unicode_data_utils as udu
from uts46._data import joining_types, uts46_mapping, uts46_transitional_mapping
from uts46._datamodels import Status


class Uts46MappingTableTests(unittest.TestCase):
    """
    Verify the implementation of the UTS46 mapping tables and generated data
    by exhaustively comparing to the original source data.
    """

    data_file: Path

    @dataclass
    class IdnaMapping:
        line_num: int
        start: int
        end: int
        status: str
        mapping: str | None = None
        comment: str | None = None

        @property
        def codepoints(self) -> range:
            return range(self.start, self.end + 1)

    @classmethod
    def setUpClass(cls):
        cls.data_file, _ = udu.get_unicode_file(
            udu.IDNA_MAPPING_TABLE_URL, version=uts46_mapping.data_version
        )

    @classmethod
    def parse_mapping_table(cls) -> Iterator[IdnaMapping]:
        """Iterate over the mapping table definitions."""
        for line_num, content, comment in udu.parse_data_file(cls.data_file):
            fields = udu.parse_semicolon_fields(content)
            start, end = udu.parse_codepoint_field(fields[0])
            status = fields[1]
            mapping = None
            if status in {"mapped", "deviation"}:
                assert len(fields) >= 3, f"Missing mapping: {content}"
                mapping = udu.parse_codepoint_sequence_field(fields[2])
            yield cls.IdnaMapping(
                line_num=line_num,
                start=start,
                end=end,
                status=status,
                mapping=mapping,
                comment=comment,
            )

    # Using subTest on every individual codepoint overwhelms the test result
    # collector. Instead, cover all codepoints for each mapping table line
    # in a single subTest.

    def test_uts46_mapping_status(self):
        """Exhaustively verify the non-transitional uts46_mapping status."""
        for original in self.parse_mapping_table():
            with self.subTest(line=original.line_num, comment=original.comment):
                expected = {
                    "valid": Status.VALID,
                    "ignored": Status.IGNORED,
                    "mapped": Status.MAPPED,
                    # In non-transitional processing, deviation codepoints
                    # are treated as valid.
                    "deviation": Status.VALID,
                    "disallowed": Status.DISALLOWED,
                }[original.status]
                for cp in original.codepoints:
                    actual = uts46_mapping.status(chr(cp))
                    self.assertEqual(
                        actual,
                        expected,
                        f"Incorrect status for U+{cp:04X}:"
                        f" expected {expected!r}, got {actual!r}",
                    )

    def test_uts46_mapping_getitem(self):
        """Exhaustively verify the non-transitional uts46_mapping mappings."""
        for original in self.parse_mapping_table():
            with self.subTest(line=original.line_num, comment=original.comment):
                for cp in original.codepoints:
                    char = chr(cp)
                    expected = {
                        "valid": char,
                        "ignored": "",
                        "mapped": original.mapping,
                        "deviation": char,
                        "disallowed": char,
                    }[original.status]
                    actual = uts46_mapping[char]
                    self.assertEqual(
                        actual,
                        expected,
                        f"Incorrect mapping for U+{cp:04X}:"
                        f" expected {expected!r}, got {actual!r}",
                    )

    def test_uts46_mapping_transitional_status(self):
        """Exhaustively verify the uts46_transitional_mapping status."""
        for original in self.parse_mapping_table():
            with self.subTest(line=original.line_num, comment=original.comment):
                for cp in original.codepoints:
                    expected = {
                        "valid": Status.VALID,
                        "ignored": Status.IGNORED,
                        "mapped": Status.MAPPED,
                        "deviation": Status.DEVIATION,
                        "disallowed": Status.DISALLOWED,
                    }[original.status]
                    # Transitional has special case for "ẞ" per UTS46 section 5.
                    if cp == 0x1E9E:
                        expected = Status.DEVIATION
                    actual = uts46_transitional_mapping.status(chr(cp))
                    self.assertEqual(
                        actual,
                        expected,
                        f"Incorrect transitional status for U+{cp:04X}:"
                        f" expected {expected!r}, got {actual!r}",
                    )

    def test_uts46_mapping_transitional_getitem(self):
        """Exhaustively verify the uts46_transitional_mapping mappings."""
        for original in self.parse_mapping_table():
            with self.subTest(line=original.line_num, comment=original.comment):
                for cp in original.codepoints:
                    char = chr(cp)
                    expected = {
                        "valid": char,
                        "ignored": "",
                        "mapped": original.mapping,
                        "deviation": original.mapping,
                        "disallowed": char,
                    }[original.status]
                    # Transitional has special case for "ẞ" per UTS46 section 5.
                    if cp == 0x1E9E:
                        expected = "ss"
                    actual = uts46_transitional_mapping[char]
                    self.assertEqual(
                        actual,
                        expected,
                        f"Incorrect transitional mapping for U+{cp:04X}:"
                        f" expected {expected!r}, got {actual!r}",
                    )


class JoiningTypesTests(unittest.TestCase):
    """
    Verify the implementation of the joining types map and generated data
    by exhaustively comparing to the original source data.
    """

    @dataclass
    class JoiningTypeEntry:
        line_num: int
        start: int
        end: int
        joining_type: str
        comment: str | None = None

        @property
        def codepoints(self) -> range:
            return range(self.start, self.end + 1)

    data_file: Path

    @classmethod
    def setUpClass(cls):
        cls.data_file, _ = udu.get_unicode_file(
            udu.DERIVED_JOINING_TYPE_URL, version=joining_types.data_version
        )

    @classmethod
    def parse_joining_types(cls) -> Iterator[JoiningTypeEntry]:
        """Iterate over the joining types table definitions."""
        for line_num, content, comment in udu.parse_data_file(cls.data_file):
            fields = udu.parse_semicolon_fields(content)
            start, end = udu.parse_codepoint_field(fields[0])
            joining_type = fields[1]
            yield cls.JoiningTypeEntry(
                line_num=line_num,
                start=start,
                end=end,
                joining_type=joining_type,
                comment=comment,
            )

    def test_joining_types(self):
        """Exhaustively verify the joining types."""
        defined_ranges = []
        for original in self.parse_joining_types():
            defined_ranges.append((original.start, original.end))
            with self.subTest(line=original.line_num, comment=original.comment):
                for cp in original.codepoints:
                    expected = original.joining_type
                    actual = joining_types[cp]
                    self.assertEqual(
                        actual,
                        expected,
                        f"Incorrect joining type for U+{cp:04X}:"
                        f" expected {expected!r}, got {actual!r}",
                    )

        # In between defined ranges, joining type should be "".
        defined_ranges.sort()
        undefined_ranges = zip(
            [0] + [end + 1 for _, end in defined_ranges],
            [start - 1 for start, _ in defined_ranges] + [0x10FFFF],
            strict=True,
        )
        for start, end in undefined_ranges:
            if end < start:
                continue
            with self.subTest(undefined=f"U+{start:04X}..U+{end:04X}"):
                for cp in range(start, end + 1):
                    self.assertEqual(
                        joining_types[cp],
                        "",
                        f"Incorrect joining type for U+{cp:04X}"
                        f" expected '', got {joining_types[cp]!r}",
                    )


if __name__ == "__main__":
    unittest.main()
