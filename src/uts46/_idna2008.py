"""
Utility functions from IDNA 2008 (RFC 5892 and RFC 5893).
"""

import re
import unicodedata

from ._data import joining_types
from ._errors import ErrorList, ucp

# From RFC 5890 Section 2.3.2.5
ACE_PREFIX = "xn--"

# From RFC 5892 Appendix B.1: the only CONTEXTJ chars are ZWNJ and ZWJ.
ZWNJ = "\N{ZERO WIDTH NON-JOINER}"
ZWJ = "\N{ZERO WIDTH JOINER}"
CONTEXTJ_CHARS = {ZWNJ, ZWJ}

VIRAMA_COMBINING_CLASS = 9


def has_virama_before(label: str, pos: int, errors: ErrorList) -> bool:
    """
    Return True if the character before pos is a virama.

    Records an error if the character's combining class cannot be determined
    because Python's unicodedata doesn't recognize it.
    """
    if pos < 1:
        return False
    ch = label[pos - 1]
    combining_class = unicodedata.combining(ch)
    if combining_class == 0 and unicodedata.name(ch, "unknown") == "unknown":
        # Char likely comes from a newer version of Unicode
        errors.add(
            f"Unknown combining class for {ucp(ch)}",
            status="CX",
            obj=label,
            pos=pos - 1,
        )
    return combining_class == VIRAMA_COMBINING_CLASS


def check_zwnj_rule(label: str, errors: ErrorList) -> None:
    """
    Verifies that label satisfies the RFC 5892 Appendix A.1 ContextJ rule
    for ZERO WIDTH NON JOINER. Records violations in the errors list.
    """
    # ZWNJ is only allowed:
    # - immediately following a virama
    # - OR in the sequence of joining types:
    #   L or D, zero or more T, ZWNJ, zero or more T, R or D
    label_joining_types: str | None = None
    next_pos = 0
    while (pos := label.find(ZWNJ, next_pos)) >= 0:
        next_pos = pos + 1
        if has_virama_before(label, pos, errors):
            continue
        if label_joining_types is None:
            # Map the label chars to their joining type characters (C, D, R, L, T),
            # substituting "z" for the ZWNJ and "x" for non-joining.
            label_joining_types = "".join(
                "z" if ch == ZWNJ else joining_types.get(ch, "x") for ch in label
            )
        before = label_joining_types[: pos + 1]  # including ZWNJ
        after = label_joining_types[pos:]  # including ZWNJ
        if re.search(r"[LD]T*z$", before) and re.search(r"^zT*[RD]", after):
            continue
        errors.add(
            "Invalid context for zero width non-joiner",
            status="C1",
            obj=label,
            pos=pos,
        )


def check_zwj_rule(label: str, errors: ErrorList) -> None:
    """
    Verifies that label satisfies the RFC 5892 Appendix A.2 ContextJ rule
    for ZERO WIDTH JOINER. Records violations in the errors list.
    """
    # ZWJ is only allowed immediately following a virama
    next_pos = 0
    while (pos := label.find(ZWJ, next_pos)) >= 0:
        next_pos = pos + 1
        if not has_virama_before(label, pos, errors):
            errors.add(
                "Invalid context for zero width joiner",
                status="C2",
                obj=label,
                pos=pos,
            )


def is_rtl_label(label: str) -> bool:
    """Checks whether label is an RTL label."""
    # RFC 5893 section 1.4: "An RTL label is a label that contains at least one
    # character of type R, AL, or AN."
    return any(unicodedata.bidirectional(ch) in {"R", "AL", "AN"} for ch in label)


VALID_RTL_DIRS = {"R", "AL", "AN", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"}
VALID_LTR_DIRS = {"L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"}


def check_bidi_rules(label: str, errors: ErrorList) -> None:
    """
    Verifies label satisfies all six of the numbered conditions
    in RFC 5893, Section 2. Records violations in the errors list.
    """
    # This code is adapted from the idna package's check_bidi() implementation.
    # https://github.com/kjd/idna/blob/v3.10/idna/core.py#L70
    if not label:
        return

    # Bidi rule 1
    ch = label[0]
    bidi = unicodedata.bidirectional(ch)
    rtl = False
    if bidi in {"R", "AL"}:
        rtl = True
    elif bidi != "L":
        errors.add(
            f"Invalid directionality {bidi!r} in bidirectional"
            f" label for first character {ucp(ch)}",
            status="B1",
            obj=label,
            pos=0,
        )

    valid_ending = False
    number_type: str | None = None
    for pos, ch in enumerate(label):
        bidi = unicodedata.bidirectional(ch)
        if bidi == "":
            # Char likely comes from a newer version of Unicode
            errors.add(
                f"Unknown directionality for {ucp(ch)}",
                status="BX",
                obj=label,
                pos=pos,
            )

        if rtl:
            # Bidi rule 2
            if bidi not in VALID_RTL_DIRS:
                errors.add(
                    f"Invalid directionality {bidi!r}"
                    f" in a right-to-left label for {ucp(ch)}",
                    status="B2",
                    obj=label,
                    pos=pos,
                )
            # Bidi rule 3
            if bidi in {"R", "AL", "EN", "AN"}:
                valid_ending = True
            elif bidi != "NSM":
                valid_ending = False
            # Bidi rule 4
            if bidi in {"AN", "EN"}:
                if number_type is None:
                    number_type = bidi
                elif number_type != bidi:
                    errors.add(
                        "Invalid mixed numeral types in a right-to-left label",
                        status="B4",
                        obj=label,
                        pos=pos,
                    )
        else:  # ltr
            # Bidi rule 5
            if bidi not in VALID_LTR_DIRS:
                errors.add(
                    f"Invalid directionality {bidi!r}"
                    f" in a left-to-right label for {ucp(ch)}",
                    status="B5",
                    obj=label,
                    pos=pos,
                )
            # Bidi rule 6
            if bidi in {"L", "EN"}:
                valid_ending = True
            elif bidi != "NSM":
                valid_ending = False

    if not valid_ending:
        errors.add(
            f"Invalid directionality {bidi!r} in a bidirectional"
            f" label for last character {ucp(ch)}",
            status="B3" if rtl else "B6",
            obj=label,
            pos=len(label) - 1,
        )
