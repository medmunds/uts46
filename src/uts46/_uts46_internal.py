"""
Internal functions. The public API is in uts46.py (without the underscore).
"""

import string
import unicodedata

from uts46._data import uts46_mapping, uts46_transitional_mapping
from uts46._errors import ErrorList, ucp
from uts46._idna2008 import (
    ACE_PREFIX,
    check_bidi_rules,
    check_zwj_rule,
    check_zwnj_rule,
    is_rtl_label,
)

FULL_STOP = "."
STD3_VALID_CHARS = set(string.ascii_lowercase + string.digits + "-")


def validate_label(
    label: str,
    *,
    check_hyphens: bool,
    check_joiners: bool,
    transitional_processing: bool,
    use_std3_ascii_rules: bool,
    errors: ErrorList,
) -> None:
    """
    Apply UTS46 Section 4.1, Validity Criteria steps 1-8.

    (Step 9 requires knowing if the domain name is a Bidi domain name,
    which requires having all processed labels available.)

    This is an internal function. The public API is uts46.validate_label().
    """
    # [Comments below are quoted from UTS46 Section 4.1, unless in brackets.]

    # Each of the following criteria must be satisfied for a non-empty label:
    if not label:
        return

    # 1. The label must be in Unicode Normalization Form NFC.
    if not unicodedata.is_normalized("NFC", label):
        errors.add("Label must be in Normalization Form C", status="V1", obj=label)

    # 2. If CheckHyphens, the label must not contain a U+002D HYPHEN-MINUS character
    #    in both the third and fourth positions.
    if check_hyphens and len(label) >= 4 and label[2:4] == "--":
        errors.add(
            "Label must not have hyphens in positions 3-4",
            status="V2",
            obj=label,
            start=2,
            end=4,
        )

    # 3. If CheckHyphens, the label must neither begin nor end with
    #    a U+002D HYPHEN-MINUS character.
    if check_hyphens:
        if label.startswith("-"):
            errors.add(
                "Label must not begin with a hyphen", status="V3", obj=label, start=0
            )
        if label.endswith("-"):
            errors.add(
                "Label must not end with a hyphen",
                status="V3",
                obj=label,
                pos=len(label) - 1,
            )

    # 4. If not CheckHyphens, the label must not begin with “xn--”.
    if not check_hyphens and label.startswith(ACE_PREFIX):
        errors.add(
            f"Label must not begin with {ACE_PREFIX!r}",
            status="V4",
            obj=label,
            start=0,
            end=4,
        )

    # 5. The label must not contain a U+002E ( . ) FULL STOP.
    if FULL_STOP in label:
        pos = label.find(FULL_STOP)
        errors.add("Label must not contain full stop", status="V5", obj=label, pos=pos)

    # 6. The label must not begin with a combining mark, that is: General_Category=Mark.
    if len(label) > 0 and unicodedata.category(label[0]).startswith("M"):
        errors.add(
            "Label must not begin with a combining mark", status="V6", obj=label, pos=0
        )

    # 7. Each code point in the label...
    mapping = uts46_transitional_mapping if transitional_processing else uts46_mapping
    for pos, ch in enumerate(label):
        # ... must only have certain Status values according
        # to Section 5, IDNA Mapping Table:
        if not mapping.is_valid(ch):
            status = mapping.status(ch)
            errors.add(
                f"Disallowed status '{status!s}' for code point {ucp(ch)}",
                status="V7",
                obj=label,
                start=pos,
            )

        # ... In addition, if UseSTD3ASCIIRules=true and the code point is an ASCII
        # code point (U+0000..U+007F), then it must be a lowercase letter (a-z),
        # a digit (0-9), or a hyphen-minus (U+002D).
        if use_std3_ascii_rules and ch.isascii() and ch not in STD3_VALID_CHARS:
            errors.add(
                f"Disallowed STD3 character {ch!r}", status="U1", obj=label, start=pos
            )

    # 8. If CheckJoiners, the label must satisfy the ContextJ rules...
    if check_joiners:
        check_zwnj_rule(label, errors)
        check_zwj_rule(label, errors)


def main_processing(
    domain_name: str,
    *,
    use_std3_ascii_rules: bool,
    check_hyphens: bool,
    check_bidi: bool,
    check_joiners: bool,
    transitional_processing: bool,
    ignore_invalid_punycode: bool,
    errors: ErrorList,
) -> list[str]:
    """
    Applies UTS46 Section 4 Main Processing Steps to the given inputs.
    Returns the processed labels. Records any errors in the errors list.

    This is an internal function. The public API is uts46.main_processing().
    """
    # [Comments below are quoted from UTS46 Section 4, unless in brackets.]

    # 1. Map. For each code point in the domain_name string, look up the Status value
    # in Section 5, IDNA Mapping Table, and take the following actions...
    mapping = uts46_transitional_mapping if transitional_processing else uts46_mapping
    mapped = "".join(mapping[ch] for ch in domain_name)

    # 2. Normalize. Normalize the domain_name string to Unicode Normalization Form C.
    normalized = unicodedata.normalize("NFC", mapped)

    # 3. Break. Break the string into labels at U+002E ( . ) FULL STOP.
    labels = normalized.split(FULL_STOP)

    # 4. Convert/Validate. For each label in the domain_name string:
    result_labels = []
    for label in labels:
        # If the label starts with "xn--":
        if label.startswith(ACE_PREFIX):
            # [Keep the unconverted A-Label for error messages.]
            a_label = label

            # 1. If the label contains any non-ASCII code point…, record
            #    that there was an error, and continue with the next label.
            if not label.isascii():
                pos, ch = next(
                    (i, ch) for i, ch in enumerate(label) if not ch.isascii()
                )
                errors.add(
                    f"Non-ASCII code point {ucp(ch)} in A-label",
                    status="P4",
                    obj=label,
                    pos=pos,
                )
                result_labels.append(label)
                continue

            # 2. Attempt to convert the rest of the label to Unicode according
            #    to Punycode [RFC3492]. If that conversion fails and
            #    if not IgnoreInvalidPunycode, record that there was an error,
            #    and continue with the next label. Otherwise replace the original
            #    label in the string by the results of the conversion.
            punycode = label[len(ACE_PREFIX) :]
            try:
                converted = punycode.encode("ascii").decode(
                    "punycode",
                    errors="ignore" if ignore_invalid_punycode else "strict",
                )
                # [`b"xn---"[4:].decode("punycode")` is "", but should be an error.]
                if punycode and not converted:
                    raise UnicodeError(repr(punycode))
            except UnicodeError as error:
                if not ignore_invalid_punycode:
                    errors.add(
                        f"Failed to convert from Punycode: {error.args[0]}",
                        status="P4",
                        obj=label,
                    )
                    result_labels.append(label)
                    continue
            else:
                label = converted

            # 3. If the label is empty, or if the label contains only ASCII
            #    code points, record that there was an error.
            if not label:
                errors.add(
                    "A-label converts to empty U-label",
                    status="P4",
                    obj=a_label,
                    start=len(ACE_PREFIX),
                    end=len(a_label),
                )
            elif label.isascii():
                errors.add(
                    "A-label converts to ASCII U-label",
                    status="P4",
                    obj=a_label,
                    start=len(ACE_PREFIX),
                    end=len(a_label),
                )

            # 4. Verify that the label meets the validity criteria in Section 4.1,
            #    Validity Criteria for Nontransitional Processing.
            validate_transitional = False

        else:
            # If the label does not start with “xn--”:
            # Verify that the label meets the validity criteria in Section 4.1,
            # Validity Criteria for the input Processing choice
            validate_transitional = transitional_processing

        # [This verifies Section 4.1 validity criteria 1-8, but not 9.]
        validate_label(
            label,
            check_hyphens=check_hyphens,
            check_joiners=check_joiners,
            transitional_processing=validate_transitional,
            use_std3_ascii_rules=use_std3_ascii_rules,
            errors=errors,
        )

        result_labels.append(label)

    # [Item 9 from Section 4.1 Validity Criteria couldn't be checked earlier:
    # if *any* processed label is RTL, we need to check bidi for *every* label.]
    if check_bidi:
        # [RFC 5893 Section 1.4: "A 'Bidi domain name' is a domain name that
        # contains at least one RTL label."]
        is_bidi_domain = any(is_rtl_label(label) for label in result_labels)
        # 9. If CheckBidi, and if the domain name is a Bidi domain name, then the label
        #    must satisfy all six of the numbered conditions in RFC 5893, Section 2.
        if is_bidi_domain:
            for label in result_labels:
                check_bidi_rules(label, errors=errors)

    return result_labels
