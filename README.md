# UTS46: Unicode Compatibility Processing for Internationalized Domain Names

[![CI](https://github.com/medmunds/uts46/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/medmunds/uts46/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/uts46)](https://pypi.org/project/uts46/)


A Python implementation of [Unicode Technical Standard #46][UTS46], *Unicode
IDNA Compatibility Processing.* Converts internationalized domain names (IDNs)
to and from ASCII representations (RFC 5890 A-labels, sometimes called
"Punycode"[^1]), using the UTS46 ToASCII and ToUnicode operations.

```python
import uts46

uts46.encode("солідарні.ua")  # b'xn--80ahukbpc4oe.ua'
uts46.decode(b"xn--80ahukbpc4oe.ua")  # 'солідарні.ua'

# UTS46 converts to lowercase (Ε → ε, Ä → ä)
uts46.encode("Είναι.Är.صغير.世界")  # b'xn--kxaekss.xn--r-zfa.xn--wgbhp8d.xn--rhqv96g'
uts46.decode(b"xn--kxaekss.xn--r-zfa.xn--wgbhp8d.xn--rhqv96g")  # 'είναι.är.صغير.世界'

# UTS46 allows most symbols and emoji (unlike IDNA 2008)
uts46.encode("🧪.test")  # b'xn--0v9h.test'
uts46.decode(b"xn--0v9h.test")  # '🧪.test'
```

The uts46 package:
* implements UTS46 v16.0.0
* passes the full suite of UTS46 conformance tests
* provides both [high level](#usage) encode() and decode() functions
  plus [lower level](#uts46-operations) UTS46 operations
* optionally registers Python [codecs](#codecs) (`"тест.test".encode("uts46")`)
* also implements related [IDNA algorithms](#whatwg-idna-algorithms)
  from the *WHATWG Url Standard*
* is written in pure Python and has no dependencies outside the standard library
* includes type annotations
* supports Python 3.10 and later
* is released under the MIT License

The implementation is inspired by (and directly adapts some code from)
the [idna] package, which provides IDNA 2008 encoding and decoding.
There are [differences](#difference-from-idna-package) between uts46 and
using idna's `uts46` option.

This Python implementation is an independent project, and is not endorsed
or supported by the Unicode Consortium or WHATWG.

[^1]: Technically, only the part *after* the "xn--" has been encoded using
      the Punycode algorithm. The "xn--" is an RFC 5890 "ACE Prefix,"
      and the prefix plus the Punycode-encoded segment makes an "A-label."


[idna]: https://pypi.org/project/idna/
[UTS46]: https://www.unicode.org/reports/tr46/


## Installation

The uts46 package is available for installation from PyPI:

```bash
pip install uts46
```

## Usage

For typical usage, the uts46 `encode()` and `decode()` functions convert
Unicode IDNs to ASCII and back:

```python
import uts46

uts46.encode("δοκιμή.test")  # b'xn--jxalpdlp.test'
uts46.decode(b"xn--jxalpdlp.test")  # 'δοκιμή.test'
```

Both functions can take either `str` or `bytes` input. (Encode non-ASCII
bytes input as utf-8.) `encode()` returns ASCII `bytes` and `decode()`
returns a Unicode `str`.

By default, the functions perform strict validation checks. UTS46 defines
input parameters that can skip some of these checks. See the inline
documentation for [`encode()`][encode] and [`decode()`][decode] for details.

Failed validation checks and other problems will raise `uts46.Uts46Error`,
a subclass of `UnicodeError`.

[encode]: ./src/uts46/uts46.py#:~:text=def%20encode
[decode]: ./src/uts46/uts46.py#:~:text=def%20decode


### Transitional processing

UTS46 is built on top of IDNA 2008, which handles a small set of characters
differently from the earlier IDNA 2003 standard. UTS46 normally follows
IDNA 2008 for these "deviation characters," but it also defines a "transitional
processing" option that uses the IDNA 2003 mappings instead.

The uts46 package provides *non-transitional* processing by default:

```python
# "ß" is an IDNA 2003/2008 "deviation character"
uts46.encode("faß.de")  # b'xn--fa-hia.de' -- non-transitional
uts46.encode("faß.de", transitional_processing=True)  # b'fass.de'
```

At this point, the vast majority of applications and infrastructure have
updated to IDNA 2008. Newer versions of UTS46 have deprecated the transitional
processing option, and it should be used only for legacy compatibility.

Unicode's [*Internationalized Domain Names FAQ*][IDNFAQ] explains more.

[IDNFAQ]: https://www.unicode.org/faq/idn.html

### Codecs

The uts46 package includes codecs that work with Python's `str.encode()`
and `bytes.decode()` functions. These are not installed by default. To register
the codecs, `import uts46.codecs`.

```python
import uts46.codecs  # registers codecs

"Próf.test".encode("uts46")  # b'xn--prf-hna.test'
b"xn--prf-hna.test".decode("uts46")  # 'próf.test'
```

The available encodings are:
* `"uts46"` (aliases `"uts-46"`, `"UTS 46"`, `"idna-uts46"`)
* `"uts46-transitional"`—uses deprecated
  [transitional processing](#transitional-processing) (aliases
  `"uts-46-transitional"`, `"UTS 46 Transitional"`, `"idna-uts46-transitional"`)

The uts46 codecs support `errors="strict"` (the default) and `errors="ignore"`,
but no other error handling schemes:

```python
b"xn--oops.test".decode("uts46")  # raises Uts46Error
b"xn--oops.test".decode("uts46", errors="ignore")  # '䨿.test'
```

### UTS46 operations

The uts46 package also provides the individual operations specified by UTS46:

* Section 4 Main Processing Steps: [`uts46.main_processing()`][main_processing]
* Section 4.1 Validity Criteria for a label:
  [`uts46.validate_label()`][validate_label]
* Section 4.2 ToASCII operation: [`uts46.to_ascii()`][to_ascii]
* Section 4.3 ToUnicode operation: [`uts46.to_unicode()`][to_unicode]
* Section 4.4 Preprocessing for IDNA2008:
  [`uts46.preprocessing_for_idna2008()`][preprocessing_for_idna2008]

See each function's inline documentation for more information.

(Avoid using any uts46 functions or variables that start with an underscore,
or that are imported from a submodule beginning with an underscore. These are
not part of the uts46 public API, and they may change without notice.)

[main_processing]: ./src/uts46/uts46.py#:~:text=def%20main_processing
[validate_label]: ./src/uts46/uts46.py#:~:text=def%20validate_label
[to_ascii]: ./src/uts46/uts46.py#:~:text=def%20to_ascii
[to_unicode]: ./src/uts46/uts46.py#:~:text=def%20to_unicode
[preprocessing_for_idna2008]: ./src/uts46/uts46.py#:~:text=def%20preprocessing_for_idna2008

### WHATWG IDNA algorithms

The uts46 package provides implementations of the [WHATWG URL Standard][WHATWG]
IDNA "domain to ASCII" and "domain to Unicode" algorithms in the `uts46.whatwg`
module:

```python
from uts46.whatwg import domain_to_ascii, domain_to_unicode

domain_to_ascii("ޓެސްޓް.test")  # 'xn--xqbfb2hvab.test'
domain_to_unicode("xn--xqbfb2hvab.test")  # 'ޓެސްޓް.test'
```

The uts46.whatwg functions take and return `str` domains (not `bytes`). Both
functions take `be_strict` (default True) and `transitional` (default False)
keyword arguments. See the [`domain_to_ascii()`][domain_to_ascii] and
[`domain_to_unicode()`][domain_to_unicode] inline documentation for details.

[WHATWG]: https://url.spec.whatwg.org/#idna
[domain_to_ascii]: ./src/uts46/whatwg.py#:~:text=def%20domain_to_ascii
[domain_to_unicode]: ./src/uts46/whatwg.py#:~:text=def%20domain_to_unicode

## Difference from idna package

The Python [idna] (IDNA 2008) package includes some UTS46 support through
its `uts46=True` option. There are differences between the packages:
* idna implements only UTS46 section 4.4, *Preprocessing for IDNA 2008*
* uts46 implements the complete UTS46 specification

One noteable difference is the handling of emoji domains:

```python
uts46.encode("☕.example")  # 'xn--53h.example'
idna.encode("☕.example", uts46=True)  # raises idna.core.InvalidCodepoint
```

In terms of [UTS46 Conformance] and [conformance testing]:
* The uts46 package satisfies all three conformance clauses C1, C2 and C3,
  and it passes the full suite of conformance tests.
* The idna package's `uts46=True` option satisfies only clause C3, and it
  therefore skips conformance tests involving IDNA 2008 disallowed characters.

For any domain, `idna.encode(domain, uts46=True)` should produce the
same results as `idna.encode(uts46.preprocessing_for_idna2008(domain))`.

[UTS46 Conformance]: https://unicode.org/reports/tr46/#Conformance
[conformance testing]: https://unicode.org/reports/tr46/#Conformance_Testing

## Development

The uts46 project is hosted on GitHub: https://github.com/medmunds/uts46.

Contributions are welcome, including bug reports, fixes, and improvements to the
tests and documentation. Suggestions for enhancements are also welcome, keeping
in mind the package's focus on precisely implementing UTS46.

### Development setup

To set up a development environment:

```shell
# Clone the repository
git clone https://github.com/medmunds/uts46.git
cd uts46

# Install editable package and development dependencies
pip install -e '.[dev]'

# Set up pre-commit hooks (optional, but encouraged for PRs)
pre-commit install
```

This project uses [ruff] for linting and formatting Python code, [mypy] for
static type checking, and several [pre-commit-hooks]. If you have installed
[pre-commit] as shown above, the tools will run automatically when you commit
code. To run them manually:

```shell
pre-commit run --all-files

# Or individual tools
ruff check .
ruff format .
mypy .
```

[mypy]: https://mypy.readthedocs.io/
[pre-commit]: https://pre-commit.com/
[pre-commit-hooks]: https://github.com/pre-commit/pre-commit-hooks
[ruff]: https://docs.astral.sh/ruff/

### Building

To build a package distribution from source, use PyPA's standard [build] tool:

```shell
python -m build
```

(`pip install build` first if you don't have build.)

[build]: https://build.pypa.io/

### Generating _data.py

The _data.py file in the package source is generated from the UTS46
[IDNA Mapping Table] and other Unicode data.

If you need to rebuild it (e.g., to update to a newer Unicode version), edit
the configuration in the `[tool.uts46.generate-data]` section of pyproject.toml
and then run:

```shell
python tools/generate-data.py
```

The updated _data.py should be committed to the repository.

[IDNA Mapping Table]: https://unicode.org/reports/tr46/#IDNA_Mapping_Table

### Testing

Package tests use `unittest`. To run all tests:

```shell
python tests
# or
python -m unittest
```

To run a specific test suite, such as the conformance tests:

```shell
python -m unittest tests.test_conformance
```

The package includes a comprehensive test suite that verifies conformance
with the UTS46 specification, using the official test data provided by Unicode.
The tests automatically download that data when needed, and cache it locally
in the data directory (which is ignored by git).
