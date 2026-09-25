import hashlib
import tempfile
import unittest
from pathlib import Path

from src.lrx.table_bfs import build_table, table_paths, write_table
from tools.table_bfs_lowmem import build_table_lowmem


class LowMemTableTests(unittest.TestCase):
    def test_matches_reference_build_5_2(self):
        m, r = 5, 2
        with tempfile.TemporaryDirectory() as ref_dir, tempfile.TemporaryDirectory() as low_dir:
            dist, meta = build_table(m, r, workers=1)
            ref_meta = write_table(ref_dir, m, r, dist, meta)
            ref_bin, _ = table_paths(ref_dir, m, r)

            low_meta = build_table_lowmem(m, r, low_dir, workers=2)
            low_bin, _ = table_paths(low_dir, m, r)

            self.assertEqual(
                hashlib.sha256(ref_bin.read_bytes()).hexdigest(),
                hashlib.sha256(low_bin.read_bytes()).hexdigest(),
            )
            self.assertEqual(ref_meta["table_sha256"], low_meta["table_sha256"])
            self.assertEqual(ref_meta["radius"], low_meta["radius"])
            self.assertEqual(ref_meta["layer_sizes"], low_meta["layer_sizes"])
            self.assertTrue(low_meta["complete"])


if __name__ == "__main__":
    unittest.main()
