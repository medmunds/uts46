import unittest
from collections.abc import Iterator
from dataclasses import dataclass

import uts46
from tools import unicode_data_utils as udu


@dataclass
class TestData:
    """Parsed line of test data from IdnaTestV2.txt."""

    # Test info
    line_num: int
    comment: str

    # The source string
    source: str

    # The expected to_unicode string and status flags
    to_unicode: str
    to_unicode_status: set[str]

    # The expected to_ascii(transitional=False) string and status flags
    to_ascii_n: str
    to_ascii_n_status: set[str]

    # The expected to_ascii(transitional=True) string and status flags
    to_ascii_t: str
    to_ascii_t_status: set[str]


class UTS46ConformanceTests(unittest.TestCase):
    """UTS46 conformance tests from IdnaTestV2.txt."""

    @staticmethod
    def parse_test_data() -> Iterator[TestData]:
        """Generate a set of test cases from the UTS46 test data."""
        # For the format of the test data and an explanation of the status codes,
        # see the first ~105 lines of IdnaTestV2.txt.
        data_file, _ = udu.get_unicode_file(
            udu.IDNA_CONFORMANCE_TEST_URL, version=uts46.versions["uts46-data"]
        )

        def str_col(value: str, default: str | None = None) -> str:
            """
            Leading and trailing spaces and tabs in each column are ignored.
            A blank value means the same as the (some other result column) value.
            "" means the empty string.
            Characters may be escaped using ...
            """
            value = value.strip()
            if value == "":
                value = default if default is not None else ""
            elif value == '""':
                value = ""
            else:
                value = udu.unescape_string(value)
            return value

        def status_col(value: str, default: set[str] | None = None) -> set[str]:
            """
            Leading and trailing spaces and tabs in each column are ignored.
            A value in square brackets,such as "[B5, B6]"... the contents
            is a list of status codes
            A blank value means the same as (some other status column) value.
            An explicit [] means no errors.
            """
            value = value.strip()
            if value == "":
                return default if default is not None else set()
            elif value == "[]":
                return set()
            elif value.startswith("[") and value.endswith("]"):
                return {flag.strip() for flag in value[1:-1].split(",")}
            else:
                raise ValueError(f"Unexpected status column value: {value!r}")

        for line_num, content, comment in udu.parse_data_file(data_file):
            columns = udu.parse_semicolon_fields(content)
            try:
                # See the description of the columns in the test data file
                # to understand the logic here.
                source = str_col(columns[0])
                to_unicode = str_col(columns[1], source)
                to_unicode_status = status_col(columns[2])
                to_ascii_n = str_col(columns[3], to_unicode)
                to_ascii_n_status = status_col(columns[4], to_unicode_status)
                to_ascii_t = str_col(columns[5], to_ascii_n)
                to_ascii_t_status = status_col(columns[6], to_ascii_n_status)
            except UnicodeError as error:
                raise UnicodeError(
                    f"Error parsing line {line_num}: {content}"
                ) from error

            yield TestData(
                line_num=line_num,
                comment=comment or "",
                source=source,
                to_unicode=to_unicode,
                to_unicode_status=to_unicode_status,
                to_ascii_n=to_ascii_n,
                to_ascii_n_status=to_ascii_n_status,
                to_ascii_t=to_ascii_t,
                to_ascii_t_status=to_ascii_t_status,
            )

    @staticmethod
    def status_kwargs(status_flags: set[str]) -> tuple[dict[str, bool], set[str]]:
        """
        Return a dict of kwargs for uts46.to_unicode or uts46.to_ascii
        that would allow ignoring errors with the specified status flags,
        plus a set of leftover status flags that cannot be ignored.
        """
        # "Implementations that allow values of particular input flags to be false
        # would ignore the corresponding status codes listed in the table below
        # when testing for errors.
        #   VerifyDnsLength:   A4_1, A4_2
        #   CheckHyphens:      V2, V3
        #   CheckJoiners:      Cn
        #   CheckBidi:         Bn
        #   UseSTD3ASCIIRules: U1"
        kwargs = {}
        unhandled = set()
        for flag in status_flags:
            if flag in {"A4_1", "A4_2"}:
                kwargs["verify_dns_length"] = False
            elif flag in {"V2", "V3"}:
                kwargs["check_hyphens"] = False
            elif flag.startswith("C"):
                kwargs["check_joiners"] = False
            elif flag.startswith("B"):
                kwargs["check_bidi"] = False
            elif flag == "U1":
                kwargs["use_std3_ascii_rules"] = False
            else:
                unhandled.add(flag)
        return kwargs, unhandled

    def _test(
        self, func, source, expected, expected_flags, line_num, transitional=False
    ):
        func_name = func.__name__
        flags = ",".join(expected_flags)
        # For conformance testing, we want to review all detected errors.
        kwargs = {"raise_errors": False}
        if transitional:
            func_name += " transitional"
            kwargs["transitional_processing"] = True

        with self.subTest(func_name, line=line_num, source=source, flags=flags):
            result, errors = func(source, **kwargs)
            if expected_flags:
                self.assertNotEqual(errors, [])  # must signal errors
                if result is not None:
                    # to_unicode can have a result even with errors, and it should match
                    self.assertEqual(
                        result,
                        expected,
                        f"Expected {expected!r} got {result!r} with errors: {errors!r}",
                    )
            else:
                self.assertEqual(errors, [])
                self.assertEqual(result, expected)

        if expected_flags:
            # If possible, re-run test ignoring the error and check result.
            status_kwargs, unhandled = self.status_kwargs(expected_flags)
            if status_kwargs and not unhandled:
                with self.subTest(
                    func_name + " ignore",
                    line=line_num,
                    source=source,
                    flags=flags,
                    **status_kwargs,
                ):
                    result, errors = func(source, **kwargs, **status_kwargs)
                    self.assertEqual(errors, [])
                    self.assertEqual(result, expected)

    def test_conformance(self):
        for case in self.parse_test_data():
            self._test(
                uts46.to_unicode,
                case.source,
                case.to_unicode,
                case.to_unicode_status,
                case.line_num,
            )

            self._test(
                uts46.to_ascii,
                case.source,
                case.to_ascii_n,
                case.to_ascii_n_status,
                case.line_num,
                transitional=False,
            )

            self._test(
                uts46.to_ascii,
                case.source,
                case.to_ascii_t,
                case.to_ascii_t_status,
                case.line_num,
                transitional=True,
            )


if __name__ == "__main__":
    unittest.main()
