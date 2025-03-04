import unittest

from uts46._rangemap import RangeMap


class RangeMapTests(unittest.TestCase):
    def test_constructor_empty(self):
        rangemap = RangeMap[int, bool]([])
        self.assertEqual(list(rangemap), [])
        self.assertEqual(list(rangemap.keys()), [])
        self.assertEqual(list(rangemap.items()), [])
        self.assertEqual(list(rangemap.values()), [])

    def test_constructor_valid_ranges(self):
        ranges = [((1, 5), "A"), ((6, 10), "B"), ((12, 15), "C"), ((18, 18), "D")]
        rangemap = RangeMap(ranges)
        self.assertEqual(list(rangemap.items()), ranges)

    def test_constructor_overlapping_ranges(self):
        ranges = [((5, 10), "B"), ((1, 5), "A")]
        with self.assertRaisesRegex(ValueError, r"Overlapping ranges:"):
            RangeMap(ranges)

    def test_constructor_invalid_range(self):
        ranges = [((10, 5), "A")]
        with self.assertRaisesRegex(ValueError, r"Invalid range:"):
            RangeMap(ranges)

    def test_getitem_in_range(self):
        ranges = [((6, 10), "B"), ((1, 5), "A")]
        rangemap = RangeMap(ranges)
        self.assertEqual(rangemap[1], "A")
        self.assertEqual(rangemap[5], "A")
        self.assertEqual(rangemap[6], "B")
        self.assertEqual(rangemap[10], "B")

    def test_getitem_out_of_range(self):
        ranges = [((1, 5), "A"), ((7, 10), "B")]
        rangemap = RangeMap(ranges)
        with self.assertRaises(KeyError):
            _ = rangemap[0]
        with self.assertRaises(KeyError):
            _ = rangemap[6]
        with self.assertRaises(KeyError):
            _ = rangemap[11]

    def test_get_with_default(self):
        ranges = [((1, 5), "A"), ((7, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(rangemap.get(5), "A")
        self.assertIsNone(rangemap.get(6))
        self.assertIsNone(rangemap.get(11))
        self.assertEqual(rangemap.get(11, "Default"), "Default")

    def test_contains(self):
        ranges = [((1, 5), "A"), ((7, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertIn(1, rangemap)
        self.assertIn(5, rangemap)
        self.assertNotIn(6, rangemap)
        self.assertNotIn(11, rangemap)

    def test_bool(self):
        self.assertFalse(RangeMap([]))
        rangemap = RangeMap([((1, 5), "A")])
        self.assertTrue(rangemap)

    def test_len(self):
        self.assertEqual(len(RangeMap([])), 0)
        rangemap = RangeMap([((1, 5), "A")])
        self.assertEqual(len(rangemap), 1)

    def test_iter_ranges(self):
        ranges = [((1, 5), "A"), ((6, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(list(rangemap), [(1, 5), (6, 10)])

    def test_keys(self):
        ranges = [((1, 5), "A"), ((6, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(list(rangemap.keys()), [(1, 5), (6, 10)])

    def test_items(self):
        ranges = [((1, 5), "A"), ((6, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(list(rangemap.items()), ranges)

    def test_values(self):
        ranges = [((1, 5), "A"), ((6, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(list(rangemap.values()), ["A", "B"])

    def test_repr(self):
        ranges = [((1, 5), "A"), ((6, 10), "B")]
        rangemap = RangeMap(ranges)
        self.assertEqual(repr(rangemap), "RangeMap([((1, 5), 'A'), ((6, 10), 'B')])")

        # repr should be a valid constructor
        rehydrated = eval(repr(rangemap))
        self.assertEqual(list(rehydrated.items()), ranges)

        self.assertEqual(repr(RangeMap([])), "RangeMap([])")


if __name__ == "__main__":
    unittest.main()
