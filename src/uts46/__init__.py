from typing import Final

from . import _data
from ._errors import Uts46Error
from ._version import __version__, __version_tuple__
from .uts46 import (
    UTS46_SPEC_VERSION,
    decode,
    encode,
    main_processing,
    preprocessing_for_idna2008,
    to_ascii,
    to_unicode,
    validate_label,
)

__all__ = [
    "Uts46Error",
    "__version__",
    "__version_tuple__",
    "decode",
    "encode",
    "main_processing",
    "preprocessing_for_idna2008",
    "to_ascii",
    "to_unicode",
    "validate_label",
    "versions",
]

# (Show as "uts46.Uts46Error", not "uts46._errors.Uts46Error".)
Uts46Error.__module__ = __name__

versions: Final[dict[str, str]] = {
    # This package's version
    "uts46": __version__,
    # The version of UTS46 implemented by this package
    "uts46-spec": UTS46_SPEC_VERSION,
    # The version of the UTS46 IdnaMappingTable included with this package
    "uts46-data": _data.uts46_mapping.data_version,
    # The value of Python's unicodedata.unidata_version
    # when the generate-data script was run
    "uts46-generator-unidata": _data.uts46_mapping.unidata_version,
    # The version of the Unicode Database used to obtain
    # the joining types data included with this package
    "joining-types-data": _data.joining_types.data_version,
}
