class Uts46Error(UnicodeError):
    """Exception for all UTS46 related problems"""

    # Documented (but untyped) properties of UnicodeError
    reason: str | None
    encoding: str | None
    object: str | bytes | None
    start: int | None
    end: int | None

    # Relevant conformance testing status code (if any), as described
    # in https://www.unicode.org/Public/idna/16.0.0/IdnaTestV2.txt
    status: str | None

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        encoding: str | None = None,
        obj: str | bytes | None = None,
        start: int | None = None,
        end: int | None = None,
        status: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.encoding = encoding
        self.object = obj
        self.start = start
        self.end = end
        self.status = status


class ErrorList(list[Uts46Error]):
    """
    Accumulates a list of Uts46Errors. Or if fail_fast is True,
    immediately raises the first error when it is added.
    """

    def __init__(self, *, fail_fast: bool = False) -> None:
        super().__init__()
        self.fail_fast = fail_fast

    def add(
        self,
        reason: str,
        *,
        status: str | None = None,
        obj: str | bytes | None = None,
        pos: int | None = None,
        start: int | None = None,
        end: int | None = None,
        encoding: str | None = None,
    ) -> Uts46Error:
        if pos is not None:
            assert start is None and end is None
            start = pos
            end = pos + 1
        if encoding is None:
            encoding = "uts46"

        message = reason
        if obj is not None:
            message += f" in {obj!r}"
        if start is not None:
            if end is None or end <= start + 1:
                message += f" at position {start}"
            else:
                message += f" at positions {start} to {end}"
        if status:
            message += f" [{status}]"

        error = Uts46Error(
            message,
            reason=reason,
            encoding=encoding,
            obj=obj,
            start=start,
            end=end,
            status=status,
        )
        self.append(error)
        if self.fail_fast:
            raise error
        return error


def ucp(c: str | int) -> str:
    """Format a character or code point as U+XXXX."""
    cp = c if isinstance(c, int) else ord(c)
    return f"U+{cp:04X}"
