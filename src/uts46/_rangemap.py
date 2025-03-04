from bisect import bisect_right
from collections.abc import Iterable, Iterator
from typing import Any, Generic, Protocol, TypeVar, overload


class Comparable(Protocol):
    # Both bisect and sorted require only __lt__.
    def __lt__(self, other: Any) -> bool: ...


K = TypeVar("K", bound=Comparable)
V = TypeVar("V")
D = TypeVar("D")


class RangeMap(Generic[K, V]):
    """
    An immutable data structure mapping ranges of keys to single values.
    Ranges are closed (inclusive of both start and end).

    Supports most of the collections.abc.Mapping[K, V] interface, except that:
    - len() returns the number of ranges, not the number of individual keys
    - keys() and iteration produce tuples of (K, K) ranges, not individual keys
    - items() produces ((K, K), V) tuples
    - values() produces one value per range, not per individual key
    """

    # Parallel sequences of range starts/ends/values sorted by starts.
    _starts: tuple[K, ...]
    _ends: tuple[K, ...]
    _values: tuple[V, ...]

    def __init__(self, ranges: Iterable[tuple[tuple[K, K], V]]):
        """
        Create a RangeMap from ((start, end), value) tuples.

        Start and end are inclusive. In the resulting RangeMap,
        rangemap[key] == value for any key in start <= key <= end.

        The ranges must be non-overlapping, but need not be sorted.
        """
        sorted_ranges = sorted(ranges)
        if not sorted_ranges:
            self._starts = self._ends = ()
            self._values = ()
            return

        # Check for overlaps
        prev = None
        for (start, end), _ in sorted_ranges:
            if end < start:
                raise ValueError(f"Invalid range: ({start!r}, {end!r})")
            # Check if start <= prev end, using only __lt__
            if prev is not None and not prev[1] < start:
                raise ValueError(f"Overlapping ranges: {prev!r}, {(start, end)!r}")
            prev = (start, end)

        keys, self._values = zip(*sorted_ranges, strict=True)
        self._starts, self._ends = zip(*keys, strict=True)

    def __bool__(self) -> bool:
        """Return True if the RangeMap contains any ranges."""
        return bool(self._values)

    def __len__(self) -> int:
        """Return the number of ranges (not individual keys)."""
        return len(self._values)

    def _find(self, key: Any) -> int | None:
        """Find the index of the range containing key."""
        if not self._starts:
            return None
        index = bisect_right(self._starts, key) - 1
        # Check if key <= self._ends[index], using only __lt__
        if index >= 0 and not self._ends[index] < key:
            return index
        return None

    def __contains__(self, key: Any) -> bool:
        """Return True if key is in any range."""
        return self._find(key) is not None

    def __getitem__(self, key: K) -> V:
        """
        Return the value for the range containing key.
        Raises KeyError if key is not in any range.
        """
        idx = self._find(key)
        if idx is None:
            raise KeyError(key)
        return self._values[idx]

    @overload
    def get(self, key: K) -> V | None: ...
    @overload
    def get(self, key: K, default: D) -> V | D: ...

    def get(self, key: K, default: Any = None) -> Any:
        """
        Return the value for the range containing key. If key is not
        in any range, return default if provided, otherwise None.
        """
        idx = self._find(key)
        if idx is None:
            return default
        return self._values[idx]

    def __iter__(self) -> Iterator[tuple[K, K]]:
        return zip(self._starts, self._ends, strict=True)

    def keys(self) -> Iterable[tuple[K, K]]:
        return zip(self._starts, self._ends, strict=True)

    def items(self) -> Iterable[tuple[tuple[K, K], V]]:
        return zip(self.keys(), self._values, strict=True)

    def values(self) -> Iterable[V]:
        return self._values

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self.items())!r})"
