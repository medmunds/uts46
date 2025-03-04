import unittest

from uts46.whatwg import domain_to_ascii, domain_to_unicode


class WhatWGTests(unittest.TestCase):
    def test_domain_to_ascii(self):
        self.assertEqual(domain_to_ascii("☕.example"), "xn--53h.example")

    def test_domain_to_ascii_not_strict(self):
        self.assertEqual(
            domain_to_ascii("🧪_🤖.test", be_strict=False), "xn--_-o54ses.test"
        )

    def test_domain_to_ascii_transitional(self):
        self.assertEqual(domain_to_ascii("FAẞ.test", transitional=True), "fass.test")

    def test_domain_to_unicode(self):
        self.assertEqual(domain_to_unicode("xn--53h.example"), "☕.example")

    def test_domain_to_unicode_not_strict(self):
        self.assertEqual(
            domain_to_unicode("xn--_-o54ses.test", be_strict=False), "🧪_🤖.test"
        )

    def test_domain_to_unicode_transitional(self):
        self.assertEqual(
            domain_to_unicode("idna\N{ZERO WIDTH JOINER}2003", transitional=True),
            "idna2003",
        )
