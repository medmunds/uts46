"""
Implementations of the "domain to ASCII" and "domain to Unicode" algorithms
from the IDNA section of the WHATWG URL Standard: https://url.spec.whatwg.org/#idna.
"""

from . import Uts46Error, to_ascii, to_unicode

__all__ = ["domain_to_ascii", "domain_to_unicode"]

# From https://url.spec.whatwg.org/#forbidden-domain-code-point:
# "A forbidden domain code point is a forbidden host code point, a C0 control,
# U+0025 (%), or U+007F DELETE."
#
# "A forbidden host code point is U+0000 NULL, U+0009 TAB, U+000A LF, U+000D CR,
# U+0020 SPACE, U+0023 (#), U+002F (/), U+003A (:), U+003C (<), U+003E (>), U+003F (?),
# U+0040 (@), U+005B ([), U+005C (\), U+005D (]), U+005E (^), or U+007C (|)."
#
# "A C0 control is a code point in the range U+0000 NULL
# to U+001F INFORMATION SEPARATOR ONE, inclusive."
_FORBIDDEN_HOST_CODE_POINTS = set("\x00\t\n\r #/:<>?@[\\]^|")
_CO_CONTROL = {chr(cp) for cp in range(0x00, 0x1F + 1)}
_FORBIDDEN_DOMAIN_CODE_POINTS = _FORBIDDEN_HOST_CODE_POINTS | _CO_CONTROL | set("%\x7f")


def domain_to_ascii(
    domain: str, *, be_strict: bool = True, transitional: bool = False
) -> str:
    """
    Implements the "domain to ASCII" IDNA algorithm from the WHATWG
    URL Standard section 3.3. Returns the ASCII-encoded domain name,
    or raises :exc:`Uts46Error` for any failures.

    :param domain:
        The domain name to encode. Note that both input and output of this
        function are strings, not bytes.

    :param be_strict:
        Sets several UTS46 processing options as described in the URL Standard.

    :param transitional:
        Set True to use deprecated UTS46 transitional processing. Note that this
        option was removed from the URL Standard in early 2017. (All browsers
        now implement non-transitional UTS46 processing.) It is retained here
        for compatibility.
    """
    # [Comments below are quoted from the WHATWG URL Standard unless in brackets.]

    # 1. Let result be the result of running Unicode ToASCII with domain_name
    #    set to domain, CheckHyphens set to beStrict, CheckBidi set to true,
    #    CheckJoiners set to true, UseSTD3ASCIIRules set to beStrict,
    #    Transitional_Processing set to false, VerifyDnsLength set to beStrict,
    #    and IgnoreInvalidPunycode set to false.
    result, errors = to_ascii(
        domain,
        raise_errors=True,
        check_hyphens=be_strict,
        check_bidi=True,
        check_joiners=True,
        use_std3_ascii_rules=be_strict,
        transitional_processing=transitional,
        verify_dns_length=be_strict,
        ignore_invalid_punycode=False,
    )
    assert isinstance(result, str)

    # 2. If result is a failure value... return failure.
    assert not errors  # [Errors are raised by to_ascii() above.]

    # 3. If beStrict is false:
    if not be_strict:
        # 1. If result is the empty string... return failure.
        if not result:
            raise Uts46Error("Empty domain")
        # 2. If result contains a forbidden domain code point... return failure.
        if not _FORBIDDEN_DOMAIN_CODE_POINTS.isdisjoint(result):
            raise Uts46Error(
                "Domain contains a forbidden domain code point",
                obj=result,
            )

    # 4. Assert: result is not the empty string and does not contain
    #    a forbidden domain code point. Note: Unicode IDNA Compatibility
    #    Processing guarantees this holds when beStrict is true.
    assert result != ""
    assert _FORBIDDEN_DOMAIN_CODE_POINTS.isdisjoint(result)

    # 5. Return result.
    return result


def domain_to_unicode(
    domain: str, *, be_strict: bool = True, transitional: bool = False
) -> str:
    """
    Implements the "domain to Unicode" IDNA algorithm from the WHATWG
    URL Standard section 3.3. Returns the decoded Unicode domain name,
    or raises :exc:`Uts46Error` for any failures.

    :param domain:
        The "Punycode" domain name to decode. Note that both input and output
        of this function are strings, not bytes.

    :param be_strict:
        Sets several UTS46 processing options as described in the URL Standard.

    :param transitional:
        Set True to use deprecated UTS46 transitional processing. Note that this
        option was removed from the URL Standard in early 2017. (All browsers
        now implement non-transitional UTS46 processing.) It is retained here
        for compatibility.
    """
    # [Comments below are quoted from the WHATWG URL Standard unless in brackets.]

    # 1. Let result be the result of running Unicode ToUnicode with domain_name
    #    set to domain, CheckHyphens set to beStrict, CheckBidi set to true,
    #    CheckJoiners set to true, UseSTD3ASCIIRules set to beStrict,
    #    Transitional_Processing set to false, and IgnoreInvalidPunycode
    #    set to false.
    result, errors = to_unicode(
        domain,
        raise_errors=True,
        check_hyphens=be_strict,
        check_bidi=True,
        check_joiners=True,
        use_std3_ascii_rules=be_strict,
        transitional_processing=transitional,
        ignore_invalid_punycode=False,
    )

    # 2. Signify domain-to-Unicode validation errors for any returned errors,
    #    and then, return result.
    assert not errors  # [Errors are raised by to_unicode() above.]
    return result
