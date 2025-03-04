"""
UTS46 codecs for str.encode() and bytes.decode().

Importing this module registers the uts46 and uts46-transitional codecs.
"""

import codecs
from collections.abc import Iterable
from typing import Any

from . import uts46

__all__ = ["Uts46Codec", "Uts46TransitionalCodec", "register", "unregister"]


class Uts46Codec(codecs.Codec):
    @property
    def name(self) -> str:
        return "uts46"

    @property
    def aliases(self) -> Iterable[str]:
        # Python converts encoding names to lowercase and replaces hyphens
        # and spaces with underscores before searching for a codec.
        return ["uts_46", "idna_uts46", "idna_uts_46"]

    @property
    def transitional_processing(self) -> bool:
        return False

    codec_info: codecs.CodecInfo

    def __init__(self) -> None:
        super().__init__()
        # UTS46 operates only on whole domain names--it can't process labels
        # piecemeal. So don't bother with incremental or streaming codecs.
        self.codec_info = codecs.CodecInfo(
            name=self.name, encode=self.encode, decode=self.decode
        )

    def _check_errors(self, errors: str) -> bool:
        """
        Return whether `errors` codec error handling scheme calls
        for error checking, or raise error on unsupported schemes.
        """
        if errors == "strict":
            return True
        elif errors == "ignore":
            return False
        else:
            raise ValueError(f"{self.name} codec does not support errors={errors!r}")

    def encode(self, s: str, errors: str = "strict", /) -> tuple[bytes, int]:
        if not isinstance(s, str):
            raise TypeError(f"{self.name} codec cannot encode {type(s)!r}")

        if s == "":
            return b"", 0

        check_errors = self._check_errors(errors)
        result, error_list = uts46.to_ascii(
            s,
            transitional_processing=self.transitional_processing,
            check_hyphens=check_errors,
            check_bidi=check_errors,
            check_joiners=check_errors,
            use_std3_ascii_rules=check_errors,
            verify_dns_length=check_errors,
            ignore_invalid_punycode=not check_errors,
        )
        assert result is not None
        assert not error_list
        return result.encode("ascii", errors), len(s)

    # Should be `b: ReadableBuffer`, but that requires Python 3.12
    # (and we don't want to bother with typing_extensions just for that).
    def decode(self, b: Any, errors: str = "strict", /) -> tuple[str, int]:
        if isinstance(b, memoryview):
            b = bytes(b)
        elif not isinstance(b, bytes):
            raise TypeError(f"{self.name} codec cannot decode {type(b)!r}")

        if b == b"":
            return "", 0

        s = b.decode("ascii", errors=errors)
        check_errors = self._check_errors(errors)
        result, error_list = uts46.to_unicode(
            s,
            transitional_processing=self.transitional_processing,
            check_hyphens=check_errors,
            check_bidi=check_errors,
            check_joiners=check_errors,
            use_std3_ascii_rules=check_errors,
            ignore_invalid_punycode=not check_errors,
        )
        assert not error_list
        return result, len(b)


class Uts46TransitionalCodec(Uts46Codec):
    @property
    def name(self) -> str:
        return f"{super().name}_transitional"

    @property
    def aliases(self) -> Iterable[str]:
        return [f"{alias}_transitional" for alias in super().aliases]

    @property
    def transitional_processing(self) -> bool:
        return True


_codec_info_by_encoding: dict[str, codecs.CodecInfo] = {
    name: codec.codec_info
    for codec in (Uts46Codec(), Uts46TransitionalCodec())
    for name in (codec.name, *codec.aliases)
}


def _codec_search(encoding: str) -> codecs.CodecInfo | None:
    return _codec_info_by_encoding.get(encoding)


def register() -> None:
    """
    Register the uts46 codecs, making them available
    to str.encode() and bytes.decode().

    (This function is called automatically as a side effect
    of importing `uts46.codecs`.)
    """
    # Only register if not already registered (else it's impossible to unregister).
    try:
        codecs.lookup("uts46")
    except LookupError:
        codecs.register(_codec_search)


def unregister() -> None:
    """Unregister the uts46 codecs."""
    codecs.unregister(_codec_search)


# Register the codecs when this module is imported
register()
