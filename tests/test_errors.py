import unittest

from uts46._errors import ErrorList, Uts46Error, ucp


class ErrorListTests(unittest.TestCase):
    def test_default_accumulates_errors(self):
        """fail_fast=False accumulates errors instead of raising"""
        errors = ErrorList()
        error1 = errors.add("Error 1")
        error2 = errors.add("Error 2")
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors, [error1, error2])

    def test_fail_fast_raises_immediately(self):
        errors = ErrorList(fail_fast=True)
        with self.assertRaises(Uts46Error):
            errors.add("Error 1")
        self.assertEqual(len(errors), 1)

    def test_position(self):
        errors = ErrorList()
        error = errors.add("Invalid character", pos=3)
        self.assertEqual(str(error), "Invalid character at position 3")
        self.assertEqual(error.start, 3)
        self.assertEqual(error.end, 4)

    def test_start_end(self):
        errors = ErrorList()
        error = errors.add("Invalid range", start=5, end=8)
        self.assertEqual(error.start, 5)
        self.assertEqual(error.end, 8)
        self.assertEqual(str(error), "Invalid range at positions 5 to 8")

    def test_obj(self):
        errors = ErrorList()
        error = errors.add("Invalid sequence", obj="example")
        self.assertEqual(error.object, "example")
        self.assertEqual(str(error), "Invalid sequence in 'example'")

    def test_status(self):
        errors = ErrorList()
        error = errors.add("Error occurred", status="X2")
        self.assertEqual(error.status, "X2")
        self.assertEqual(str(error), "Error occurred [X2]")

    def test_all_arguments(self):
        errors = ErrorList()
        error = errors.add("Complex error", obj=b"domain", start=3, end=5, status="O2")
        self.assertEqual(
            str(error), "Complex error in b'domain' at positions 3 to 5 [O2]"
        )

    def test_is_unicode_error(self):
        """For use with codecs, Uts46Error must be a subclass of UnicodeError."""
        self.assertIsInstance(Uts46Error("error"), UnicodeError)


class UcpTests(unittest.TestCase):
    def test_ucp(self):
        cases: list[tuple[str | int, str]] = [
            # Characters
            ("A", "U+0041"),
            ("☕", "U+2615"),
            ("\N{MATHEMATICAL SCRIPT CAPITAL A}", "U+1D49C"),
            ("\n", "U+000A"),
            # Code points
            (65, "U+0041"),
            (9749, "U+2615"),
            (119964, "U+1D49C"),
            # Edge cases
            ("\x00", "U+0000"),
            (0, "U+0000"),
            (0x10FFFF, "U+10FFFF"),
            ("\u0000", "U+0000"),
            ("\U0010ffff", "U+10FFFF"),
        ]
        for c, expected in cases:
            with self.subTest(input_value=c):
                actual = ucp(c)
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
