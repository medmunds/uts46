# uts46 changelog

## In development

*Unreleased changes*

### Fixes

* Change default `uts46.decode(..., ignore_invalid_punycode=False, ...)`.


## v0.2.0

*2025-03-25*

### Fixes

* Fix a problem with incorrect mappings on Python 3.10, by changing uts46's
  generated IDNA mapping table data to avoid depending on the specific Unicode
  data version available at runtime.


## v0.1.0

*2025-03-23*

Initial development release. Has bugs on Python 3.10.
