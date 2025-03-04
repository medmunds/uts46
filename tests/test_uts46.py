"""
uts46 core public API tests.

These tests focus on the Python APIs (parameters, error handling, etc.)
The conformance tests verify correctness of the underlying algorithms.

Unicode's IDNA demo page is helpful for verifying results:
https://util.unicode.org/UnicodeJsps/idna.jsp
"""

import unittest
from typing import Any

import uts46


class EncodeDecodeTests(unittest.TestCase):
    """Wrapper functions"""

    def test_encode(self):
        cases: list[tuple[Any, bytes]] = [
            # Examples from the readme
            ("солідарні.ua", b"xn--80ahukbpc4oe.ua"),
            ("Είναι.Är.صغير.世界", b"xn--kxaekss.xn--r-zfa.xn--wgbhp8d.xn--rhqv96g"),
            ("🧪.test", b"xn--0v9h.test"),
            ("δοκιμή.test", b"xn--jxalpdlp.test"),
            ("faß.de", b"xn--fa-hia.de"),
            ("☕.example", b"xn--53h.example"),
            # Other
            ("ascii.only", b"ascii.only"),
            ("Single-Label", b"single-label"),
            (b"fa\xc3\x9f.de", b"xn--fa-hia.de"),
            (bytearray("faß.de", "utf-8"), b"xn--fa-hia.de"),
        ]
        for domain, expected in cases:
            with self.subTest(domain=domain):
                actual = uts46.encode(domain)
                self.assertEqual(actual, expected)

    def test_decode(self):
        cases: list[tuple[Any, str]] = [
            # Examples from the readme
            (b"xn--80ahukbpc4oe.ua", "солідарні.ua"),
            (b"xn--kxaekss.xn--r-zfa.xn--wgbhp8d.xn--rhqv96g", "είναι.är.صغير.世界"),
            (b"xn--0v9h.test", "🧪.test"),
            (b"xn--jxalpdlp.test", "δοκιμή.test"),
            (b"xn--fa-hia.de", "faß.de"),
            (b"xn--53h.example", "☕.example"),
            # Other
            (b"ascii.only", "ascii.only"),
            (b"Single-Label", "single-label"),
            ("xn--fa-hia.de", "faß.de"),
            (bytearray("xn--fa-hia.de", "ascii"), "faß.de"),
        ]
        for domain, expected in cases:
            with self.subTest(domain=domain):
                actual = uts46.decode(domain)
                self.assertEqual(actual, expected)

    def test_encode_errors(self):
        # These domains should raise an error unless kwargs are used
        cases = [
            # domain, kwargs, expected
            ("hyphens-.bad", {"check_hyphens": False}, b"hyphens-.bad"),
            ("bidi٤٦.bad", {"check_bidi": False}, b"xn--bidi-tfgm.bad"),
            ("zwj\u200dbad", {"check_joiners": False}, b"xn--zwjbad-rf0c"),
            ("std3_bad.bad", {"use_std3_ascii_rules": False}, b"std3_bad.bad"),
            ("dns..length", {"verify_dns_length": False}, b"dns..length"),
            # Can't find invalid punycode that isn't also some other error.
            # ("xn--0.pt", {"ignore_invalid_punycode": True}, b"xn--0.pt"),
        ]
        for domain, kwargs, expected in cases:
            with self.subTest(domain=domain), self.assertRaises(uts46.Uts46Error):
                uts46.encode(domain)
            with self.subTest(domain=domain, **kwargs):
                actual = uts46.encode(domain, **kwargs)
                self.assertEqual(actual, expected)

    def test_decode_errors(self):
        cases = [
            # domain, kwargs, expected
            (b"hyphens-.bad", {"check_hyphens": False}, "hyphens-.bad"),
            (b"xn--bidi-tfgm.bad", {"check_bidi": False}, "bidi٤٦.bad"),
            (b"xn--zwjbad-rf0c", {"check_joiners": False}, "zwj\u200dbad"),
            (b"std3_bad.bad", {"use_std3_ascii_rules": False}, "std3_bad.bad"),
            # decode doesn't support verify_dns_length.
            # Can't find invalid punycode that isn't also some other error.
            # ("xn--0.pt", {"ignore_invalid_punycode": True}, b"xn--0.pt"),
        ]
        for domain, kwargs, expected in cases:
            with self.subTest(domain=domain), self.assertRaises(uts46.Uts46Error):
                uts46.decode(domain)
            with self.subTest(domain=domain, **kwargs):
                actual = uts46.decode(domain, **kwargs)
                self.assertEqual(actual, expected)

    def test_encode_transitional(self):
        self.assertEqual(
            uts46.encode("FAẞ.test", transitional_processing=True),
            b"fass.test",
        )

    def test_decode_transitional(self):
        # Transitional processing (IDNA 2003) strips ZWJ.
        # Non-transitional forbids it outside appropriate joining contexts.
        domain = "idna\N{ZERO WIDTH JOINER}2003".encode()
        self.assertEqual(
            uts46.decode(domain, transitional_processing=True),
            "idna2003",
        )


class Uts46OperationTests(unittest.TestCase):
    """Operations defined in UTS46 Section 4"""

    def test_main_processing(self):
        self.assertEqual(
            uts46.main_processing("Fakatātā.½.Example"),
            "fakatātā.1\N{FRACTION SLASH}2.example",
        )

    def test_main_processing_error(self):
        with self.assertRaises(uts46.Uts46Error):
            uts46.main_processing(">½.Example")

    def test_validate_label(self):
        # Does not raise
        uts46.validate_label("fakatātā", is_bidi_domain=False)

    def test_validate_label_error(self):
        with self.assertRaises(uts46.Uts46Error):
            uts46.validate_label(">½", check_bidi=False)

    def test_validate_label_is_bidi_domain(self):
        # validate_label needs to know if domain is bidi to implement check_bidi
        with self.assertRaisesRegex(
            TypeError, "Must provide is_bidi_domain when check_bidi is True"
        ):
            uts46.validate_label("foo")

    def test_to_ascii(self):
        self.assertEqual(
            uts46.to_ascii("ᖃᐅᔨᓴᕐᓂᖅ.test"), ("xn--1ce29aze6hmh6kta.test", [])
        )

    def test_to_ascii_error(self):
        with self.assertRaises(uts46.Uts46Error):
            uts46.to_ascii(">.test")

    def test_to_ascii_raise_errors_false(self):
        result, errors = uts46.to_ascii(">.Test", raise_errors=False)
        self.assertIsNone(result)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], uts46.Uts46Error)

    def test_to_unicode(self):
        self.assertEqual(
            uts46.to_unicode("xn--1ce29aze6hmh6kta.test"), ("ᖃᐅᔨᓴᕐᓂᖅ.test", [])
        )

    def test_to_unicode_error(self):
        with self.assertRaises(uts46.Uts46Error):
            uts46.to_unicode(">.test")

    def test_to_unicode_raise_errors_false(self):
        result, errors = uts46.to_unicode(">.Test", raise_errors=False)
        self.assertEqual(result, ">.test")  # not None (unlike to_ascii)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], uts46.Uts46Error)

    def test_preprocessing_for_idna2008(self):
        self.assertEqual(
            uts46.preprocessing_for_idna2008("Fakatātā.½.Example"),
            "fakatātā.1\N{FRACTION SLASH}2.example",
        )

    def test_preprocessing_for_idna2008_error(self):
        with self.assertRaises(uts46.Uts46Error):
            uts46.preprocessing_for_idna2008(">.Test")


class VersionTests(unittest.TestCase):
    def test_package_version(self):
        self.assertRegex(uts46.__version__, r"^\d+\.\d+")
        self.assertIsInstance(uts46.__version_tuple__, tuple)

        # The version tuple should contain the version's parts.
        version, *local_version_id = uts46.__version__.split("+")
        version_parts = [
            int(part) if part.isdigit() else part for part in version.split(".")
        ] + local_version_id
        self.assertEqual(uts46.__version_tuple__, tuple(version_parts))

    def test_versions_dict(self):
        version_re = r"^\d+\.\d+.\d+$"
        self.assertIsInstance(uts46.versions, dict)
        self.assertEqual(uts46.versions["uts46"], uts46.__version__)
        self.assertRegex(uts46.versions["uts46-spec"], version_re)
        self.assertRegex(uts46.versions["uts46-data"], version_re)
        self.assertRegex(uts46.versions["uts46-generator-unidata"], version_re)
        self.assertRegex(uts46.versions["joining-types-data"], version_re)


if __name__ == "__main__":
    unittest.main()
