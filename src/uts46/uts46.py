"""
UTS46 (Unicode IDNA Compatibility Processing) Implementation.

This module implements the core algorithms from UTS46
https://unicode.org/reports/tr46/
"""

from . import Uts46Error, _errors, _idna2008, _uts46_internal

__all__ = [
    "UTS46_SPEC_VERSION",
    "decode",
    "encode",
    "main_processing",
    "preprocessing_for_idna2008",
    "to_ascii",
    "to_unicode",
    "validate_label",
]

# The version of UTS46 that this module implements.
UTS46_SPEC_VERSION = "16.0.0"


def main_processing(
    domain_name: str,
    *,
    use_std3_ascii_rules: bool = True,
    check_hyphens: bool = True,
    check_bidi: bool = True,
    check_joiners: bool = True,
    transitional_processing: bool = False,
    ignore_invalid_punycode: bool = False,
) -> str:
    """
    Implements UTS46 Section 4 Main Processing Steps. Returns the processed
    domain name, or raises :exc:`Uts46Error` for any failures.

    :param domain_name:
      The domain name to process. Note that both input and output
      of this function are Unicode strings, not bytes.

    The keyword arguments control various UTS46 validation options.
    UTS46 does not specify default values for these options;
    the defaults here provide strict validation.

    :param use_std3_ascii_rules:
      set False to skip STD3 ASCII rules checks
    :param check_hyphens:
      set False to skip checks for illegal hyphen placements in IDNA A-labels
    :param check_bidi:
      set False to skip RFC 5892 bidirectional label validation
    :param check_joiners:
      set False to skip validating RFC 5893 contextual joining rules
    :param transitional_processing:
      set False to use deprecated transitional processing rules
    :param ignore_invalid_punycode:
      set `True` to ignore errors in Punycode conversion
    """
    errors = _errors.ErrorList(fail_fast=True)
    labels = _uts46_internal.main_processing(
        domain_name,
        use_std3_ascii_rules=use_std3_ascii_rules,
        check_hyphens=check_hyphens,
        check_bidi=check_bidi,
        check_joiners=check_joiners,
        transitional_processing=transitional_processing,
        ignore_invalid_punycode=ignore_invalid_punycode,
        errors=errors,
    )
    return _uts46_internal.FULL_STOP.join(labels)


def validate_label(
    label: str,
    *,
    check_hyphens: bool = True,
    check_joiners: bool = True,
    transitional_processing: bool = False,
    use_std3_ascii_rules: bool = True,
    check_bidi: bool = True,
    is_bidi_domain: bool | None = None,
) -> None:
    """
    Implements UTS46 Section 4.1 Validity Criteria for an individual label.
    Raises :exc:`Uts46Error` for any failed criteria.

    Keyword arguments are as described in :func:`main_processing`.

    When check_bidi is True, you must also provide bool is_bidi_domain,
    indicating whether the label is part of a Bidi domain name (that is,
    if _any_ label in the processed domain name is RTL).
    """
    if check_bidi and is_bidi_domain is None:
        raise TypeError("Must provide is_bidi_domain when check_bidi is True")

    errors = _errors.ErrorList(fail_fast=True)
    # Steps 1-8
    _uts46_internal.validate_label(
        label,
        check_hyphens=check_hyphens,
        check_joiners=check_joiners,
        transitional_processing=transitional_processing,
        use_std3_ascii_rules=use_std3_ascii_rules,
        errors=errors,
    )
    # Step 9
    if check_bidi and is_bidi_domain:
        _idna2008.check_bidi_rules(label, errors=errors)


def to_ascii(
    domain_name: str,
    *,
    raise_errors: bool = True,
    check_hyphens: bool = True,
    check_bidi: bool = True,
    check_joiners: bool = True,
    use_std3_ascii_rules: bool = True,
    transitional_processing: bool = False,
    verify_dns_length: bool = True,
    ignore_invalid_punycode: bool = False,
) -> tuple[str | None, list[Uts46Error]]:
    """
    Implements the UTS46 Section 4.2 ToASCII operation.
    Returns the ASCII-encoded domain name (or None if there were errors)
    and a list of any errors recorded during processing.

    Note that both input and output are Unicode strings, not bytes.

    If raise_errors is True (the default), immediately raises a :exc:`Uts46Error`
    if any error is recorded. In this case, to_ascii() always either returns
    a valid string and an empty error list, or raises an error.

    If raise_errors is False, accumulates all errors recorded during processing
    without raising. Returns either a valid string and an empty list, or None
    and a non-empty error list.

    By default, verifies DNS length restrictions described in UTS46 section 4.2
    step 3. Set verify_dns_length False to skip this check.

    The other keyword arguments are as described in :func:`main_processing`.
    """
    # [Comments below are quoted from UTS46 Section 4.2, unless in brackets.]
    errors = _errors.ErrorList(fail_fast=raise_errors)

    # 1. Apply Section 4 processing
    # 2. Break the result into labels at U+002E FULL STOP.
    labels = _uts46_internal.main_processing(
        domain_name,
        transitional_processing=transitional_processing,
        check_hyphens=check_hyphens,
        check_bidi=check_bidi,
        check_joiners=check_joiners,
        use_std3_ascii_rules=use_std3_ascii_rules,
        ignore_invalid_punycode=ignore_invalid_punycode,
        errors=errors,
    )

    # 3. Convert each label with non-ASCII characters into Punycode [RFC3492],
    #    and prefix by “xn--”. This may record an error.
    result_labels = []
    for label in labels:
        if not label.isascii():
            try:
                punycode = label.encode("punycode").decode("ascii")
            except UnicodeError as error:
                errors.add(
                    f"Failed to convert to Punycode: {error.args[0]}",
                    status="A3",
                    obj=label,
                )
            else:
                label = f"{_idna2008.ACE_PREFIX}{punycode}"
        result_labels.append(label)

    result = _uts46_internal.FULL_STOP.join(result_labels)

    # 4. If the VerifyDnsLength flag is true, then verify DNS length restrictions.
    if verify_dns_length:
        # The length of the domain name, excluding the root label and its dot,
        # is from 1 to 253.
        if not 1 <= len(result) <= 253:
            errors.add(
                f"Invalid domain name length {len(result)}",
                status="A4_1",
                obj=result,
            )
        # The length of each label is from 1 to 63.
        for index, label in enumerate(result_labels):
            if not 1 <= len(label) <= 63:
                errors.add(
                    f"Invalid length {len(label)} for label {index}",
                    status="A4_2",
                    obj=label,
                )

    # 5. If an error was recorded in steps 1-4, then the operation has failed
    #    and a failure value is returned.
    if errors:
        assert not raise_errors
        return None, errors

    # 6. Otherwise join the labels using U+002E FULL STOP as a separator,
    #    and return the result.
    return result, errors


def to_unicode(
    domain: str,
    *,
    raise_errors: bool = True,
    check_hyphens: bool = True,
    check_bidi: bool = True,
    check_joiners: bool = True,
    use_std3_ascii_rules: bool = True,
    transitional_processing: bool = False,
    ignore_invalid_punycode: bool = False,
) -> tuple[str, list[Uts46Error]]:
    """
    Implements the UTS46 Section 4.3 ToUnicode operation. Returns the decoded
    Unicode domain name and a list of errors recorded during processing.

    Note that both input and output are Unicode strings, not bytes.

    If raise_errors is True (the default), immediately raises a :exc:`Uts46Error`
    if any error is recorded. In this case, to_unicode() always either returns
    a valid string and an empty error list, or raises an error.

    If raise_errors is False, accumulates all errors recorded during processing
    (without raising) and returns them along with the resulting Unicode string.
    Unlike :func:`to_ascii` (and unlike IDNA 2008 ToUnicode), the UTS46 ToUnicode
    operation can return a processed string even when there are errors.

    The other keyword arguments are as described in :func:`main_processing`.
    """
    # [Comments below are quoted from UTS46 Section 4.3, unless in brackets.]
    errors = _errors.ErrorList(fail_fast=raise_errors)

    # 1. To the input domain_name, apply the Processing Steps in Section 4, Processing,
    #    using the input boolean flags Transitional_Processing, CheckHyphens, CheckBidi,
    #    CheckJoiners, and UseSTD3ASCIIRules. This may record an error.
    labels = _uts46_internal.main_processing(
        domain,
        transitional_processing=transitional_processing,
        check_hyphens=check_hyphens,
        check_bidi=check_bidi,
        check_joiners=check_joiners,
        use_std3_ascii_rules=use_std3_ascii_rules,
        ignore_invalid_punycode=ignore_invalid_punycode,
        errors=errors,
    )
    result = _uts46_internal.FULL_STOP.join(labels)

    # [Other than the root label, no label may be empty.
    # (Not specified, but implied by conformance tests.)]
    non_root_labels = labels[:-1] if len(labels) > 1 else labels
    for index, label in enumerate(non_root_labels):
        if not label:
            errors.add(f"Invalid empty label {index}", status="X4_2", obj=result)

    # 2. Like [RFC3490], this will always produce a converted Unicode string.
    #    Unlike ToASCII of [RFC3490], this always signals whether or not
    #    there was an error.
    return result, errors


def preprocessing_for_idna2008(
    domain_name: str, *, transitional_processing: bool = False
) -> str:
    """
    Implements UTS46 section 4.4 Preprocessing for IDNA2008.
    """
    # "Apply the Section 4.3, ToUnicode processing to the Unicode string."
    result, errors = to_unicode(
        domain_name, transitional_processing=transitional_processing
    )
    assert not errors
    return result


def encode(
    domain: str | bytes | bytearray,
    *,
    check_hyphens: bool = True,
    check_bidi: bool = True,
    check_joiners: bool = True,
    use_std3_ascii_rules: bool = True,
    transitional_processing: bool = False,
    verify_dns_length: bool = True,
    ignore_invalid_punycode: bool = False,
) -> bytes:
    """
    Convert a domain name to an RFC 5890 ASCII encoding using the UTS46 ToASCII
    operation with the given processing options. Returns the encoded domain
    as ASCII bytes or raises :exc:`Uts46Error`.

    :param domain:
      the domain name to encode, as a Unicode str or UTF-8 encoded bytes
    :param use_std3_ascii_rules:
      set False to skip STD3 ASCII rules checks
    :param check_hyphens:
      set False to skip checks for illegal hyphen placements in IDNA A-labels
    :param check_bidi:
      set False to skip RFC 5892 bidirectional label validation
    :param check_joiners:
      set False to skip validating RFC 5893 contextual joining rules
    :param transitional_processing:
      set False to use deprecated transitional processing rules
    :param verify_dns_length:
      set False to skip checks on DNS label and domain length
    :param ignore_invalid_punycode:
      set `True` to ignore errors in Punycode conversion
    """
    if not isinstance(domain, str):
        domain = domain.decode()
    result, errors = to_ascii(
        domain,
        raise_errors=True,
        check_hyphens=check_hyphens,
        check_bidi=check_bidi,
        check_joiners=check_joiners,
        use_std3_ascii_rules=use_std3_ascii_rules,
        transitional_processing=transitional_processing,
        verify_dns_length=verify_dns_length,
        ignore_invalid_punycode=ignore_invalid_punycode,
    )
    assert not errors
    assert result is not None
    return result.encode("ascii")


def decode(
    domain: str | bytes | bytearray,
    *,
    check_hyphens: bool = True,
    check_bidi: bool = True,
    check_joiners: bool = True,
    use_std3_ascii_rules: bool = True,
    transitional_processing: bool = False,
    ignore_invalid_punycode: bool = False,
) -> str:
    """
    Convert an ASCII-encoded internationalized domain name to a Unicode string
    using the UTS46 ToUnicode operation with the given processing options.
    Returns the decoded domain name or raises :exc:`Uts46Error`.

    :param domain:
      the domain name to decode, as a str or ASCII or UTF-8 encoded bytes
    :param use_std3_ascii_rules:
      set False to skip STD3 ASCII rules checks
    :param check_hyphens:
      set False to skip checks for illegal hyphen placements in IDNA A-labels
    :param check_bidi:
      set False to skip RFC 5892 bidirectional label validation
    :param check_joiners:
      set False to skip validating RFC 5893 contextual joining rules
    :param transitional_processing:
      set False to use deprecated transitional processing rules
    :param ignore_invalid_punycode:
      set `True` to ignore errors in Punycode conversion
    """
    if not isinstance(domain, str):
        domain = domain.decode()
    result, errors = to_unicode(
        domain,
        raise_errors=True,
        check_hyphens=check_hyphens,
        check_bidi=check_bidi,
        check_joiners=check_joiners,
        use_std3_ascii_rules=use_std3_ascii_rules,
        transitional_processing=transitional_processing,
        ignore_invalid_punycode=ignore_invalid_punycode,
    )
    assert not errors
    return result
