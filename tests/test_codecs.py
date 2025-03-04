import codecs
import unittest

from uts46 import Uts46Error
from uts46.codecs import register, unregister  # calls register() as side effect

# Isolate import side effect to this test file.
unittest.addModuleCleanup(unregister)

try:
    # Keep track of import side effect, before tests start.
    codec_on_import: codecs.CodecInfo | None = codecs.lookup("uts46")
except LookupError:
    codec_on_import = None


class CodecsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(unregister)
        register()

    def test_uts46_encode(self):
        self.assertEqual("faß.test".encode("uts46"), b"xn--fa-hia.test")

    def test_uts46_encode_empty(self):
        self.assertEqual("".encode("uts46"), b"")

    def test_uts46_encode_error(self):
        with self.assertRaises(Uts46Error):
            "bad\u200dzwj".encode("uts46")

    def test_uts46_encode_ignore_errors(self):
        self.assertEqual(
            "bad\u200dzwj".encode("uts46", errors="ignore"), b"xn--badzwj-rf0c"
        )

    def test_uts46_decode(self):
        self.assertEqual(b"xn--fa-hia.test".decode("uts46"), "faß.test")

    def test_uts46_decode_empty(self):
        self.assertEqual(b"".decode("uts46"), "")

    def test_uts46_decode_error(self):
        with self.assertRaises(Uts46Error):
            b"xn--oops".decode("uts46")

    def test_uts46_decode_ignore_errors(self):
        self.assertEqual(b"xn--oops".decode("uts46", errors="ignore"), "䨿")

    def test_aliases(self):
        # Python encoding names are case-insensitive,
        # and underscore/hyphen/space are interchangeable.
        for alias in [
            "uts_46",
            "UTS46",
            "UTS 46",
            "uts-46",
            "IDNA-UTS46",
            "idna-uts-46",
        ]:
            with self.subTest(alias=alias):
                self.assertIs(codecs.lookup(alias), codecs.lookup("uts46"))

    # Transitional

    def test_uts46_transitional_encode(self):
        self.assertEqual("faß.test".encode("uts46-transitional"), b"fass.test")
        self.assertEqual("ignored\u200dzwj".encode("uts46-transitional"), b"ignoredzwj")

    def test_uts46_transitional_encode_empty(self):
        self.assertEqual("".encode("uts46-transitional"), b"")

    def test_uts46_transitional_encode_error(self):
        with self.assertRaises(Uts46Error):
            "-example-".encode("uts46-transitional")

    def test_uts46_transitional_encode_ignore_errors(self):
        self.assertEqual(
            "-example-".encode("uts46-transitional", errors="ignore"),
            b"-example-",
        )

    def test_uts46_transitional_decode(self):
        self.assertEqual(b"xn--fa-hia.test".decode("uts46-transitional"), "faß.test")
        self.assertEqual(b"fass.test".decode("uts46-transitional"), "fass.test")

    def test_uts46_transitional_decode_empty(self):
        self.assertEqual(b"".decode("uts46-transitional"), "")

    def test_uts46_transitional_decode_error(self):
        with self.assertRaises(Uts46Error):
            b"xn--oops".decode("uts46-transitional")

    def test_uts46_transitional_decode_ignore_errors(self):
        self.assertEqual(
            b"xn--oops".decode("uts46-transitional", errors="ignore"), "䨿"
        )

    def test_transitional_aliases(self):
        for alias in [
            "uts_46_transitional",
            "UTS46 Transitional",
            "UTS 46 Transitional",
            "uts-46-transitional",
            "IDNA-UTS46-Transitional",
            "idna-uts-46-transitional",
        ]:
            with self.subTest(alias=alias):
                self.assertIs(codecs.lookup(alias), codecs.lookup("uts46-transitional"))

    def test_unsupported_error_handlers(self):
        with self.assertRaisesRegex(
            ValueError, r"uts46 codec does not support errors='replace'"
        ):
            "test".encode("uts46", errors="replace")
        with self.assertRaisesRegex(
            ValueError,
            r"uts46_transitional codec does not support errors='surrogateescape'",
        ):
            b"test".decode("uts46-transitional", errors="surrogateescape")


class CodecRegistrationTests(unittest.TestCase):
    def setUp(self):
        # Force cleanup of side effects from import.
        unregister()
        self.addCleanup(unregister)

    def test_registers_on_import(self):
        # Codec should have been registered when uts46.codecs was first imported.
        self.assertIsNotNone(codec_on_import)

    def test_register_and_unregister(self):
        register()
        self.assertIsNotNone(codecs.lookup("uts46"))

        unregister()
        with self.assertRaises(LookupError):
            codecs.lookup("uts46")

    def test_multiple_register_and_unregister(self):
        # Functions can be called repeatedly without errors.
        register()
        register()
        register()
        self.assertIsNotNone(codecs.lookup("uts46"))

        unregister()
        with self.assertRaises(LookupError):
            codecs.lookup("uts46")

        unregister()
        with self.assertRaises(LookupError):
            codecs.lookup("uts46")


if __name__ == "__main__":
    unittest.main()
