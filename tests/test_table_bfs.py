import hashlib
import itertools
import tempfile
import unittest

from src.lrx.reference_bfs import bfs_visible
from src.lrx.table_bfs import (
    DistanceTable,
    Ranker,
    build_table,
    table_paths,
    write_table,
)


class RankerTests(unittest.TestCase):
    def test_rank_unrank_bijection(self):
        for m, r in [(1, 2), (3, 2), (4, 3), (5, 2), (2, 5)]:
            ranker = Ranker(m, r)
            seen = set()
            for code in range(ranker.size):
                pos = ranker.unrank(code)
                self.assertEqual(ranker.rank(pos), code)
                v = ranker.vector(pos)
                self.assertEqual(ranker.positions(v), pos)
                seen.add(v)
            self.assertEqual(len(seen), ranker.size)
            expected = set(itertools.permutations(ranker.root()))
            self.assertEqual(seen, expected)

    def test_neighbours_match_literal_moves(self):
        ranker = Ranker(4, 3)
        for code in range(0, ranker.size, 7):
            v = ranker.vector(ranker.unrank(code))
            lp, rp, xp = ranker.neighbours(ranker.positions(v))
            self.assertEqual(ranker.vector(lp), v[1:] + v[:1])
            self.assertEqual(ranker.vector(rp), v[-1:] + v[:-1])
            self.assertEqual(ranker.vector(xp), (v[1], v[0]) + v[2:])


class TableTests(unittest.TestCase):
    def test_distances_match_independent_reference_bfs(self):
        for m, r in [(2, 2), (3, 2), (4, 2), (3, 3), (5, 2), (4, 3)]:
            dist, meta = build_table(m, r)
            self.assertTrue(meta["complete"])
            ref = bfs_visible(m, r, max_vertices=100_000)
            self.assertEqual(ref.status, "COMPLETE")
            ranker = Ranker(m, r)
            self.assertEqual(len(ref.distances), ranker.size)
            for v, d in ref.distances.items():
                self.assertEqual(dist[ranker.rank(ranker.positions(v))], d, (m, r, v))
            self.assertEqual(meta["radius"], max(ref.distances.values()))

    def test_known_radii(self):
        # Progress notes, sections 1 and 6 (references/source-manifest.md).
        for (m, r), radius in {(6, 2): 25, (5, 3): 21, (4, 4): 17, (5, 2): 19}.items():
            self.assertEqual(build_table(m, r)[1]["radius"], radius)

    def test_parallel_build_identical(self):
        serial, _ = build_table(5, 2)
        parallel, _ = build_table(5, 2, workers=2, chunk=100)
        self.assertEqual(serial, parallel)

    def test_refuses_before_allocation(self):
        with self.assertRaises(MemoryError):
            build_table(12, 4, max_bytes=10_000)

    def test_write_load_roundtrip_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist, meta = build_table(3, 2)
            meta = write_table(tmp, 3, 2, dist, meta)
            self.assertEqual(meta["table_sha256"], hashlib.sha256(dist).hexdigest())
            with self.assertRaises(FileExistsError):
                write_table(tmp, 3, 2, dist, meta)
            table = DistanceTable(tmp, 3, 2)
            self.assertEqual(table.distance((1, 2, 3, 0, 0)), 0)
            top = table.states_at(table.radius)
            self.assertTrue(top)
            self.assertTrue(all(table.distance(v) == table.radius for v in top))
            spread = table.spread_at(table.radius, 3)
            self.assertTrue(set(spread) <= set(top))
            bin_path, _ = table_paths(tmp, 3, 2)
            data = bytearray(bin_path.read_bytes())
            data[0] ^= 1
            bin_path.write_bytes(bytes(data))
            with self.assertRaises(ValueError):
                DistanceTable(tmp, 3, 2)


if __name__ == "__main__":
    unittest.main()
