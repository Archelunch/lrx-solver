"""Every deletion count agrees with the independent trusted marked replay."""
import itertools
import unittest

from integrations.zero_erasure import count_projections
from src.lrx.certificates import CertificateValidator
from src.lrx.table_bfs import Ranker


class ZeroErasureTests(unittest.TestCase):
    def test_every_short_word_and_small_state(self):
        for m, r in ((2, 1), (2, 2), (2, 3), (3, 1), (3, 2)):
            ranker = Ranker(m, r)
            validator = CertificateValidator(m, r)
            for code in range(ranker.size):
                v = ranker.vector(ranker.unrank(code))
                for length in range(5):
                    for letters in itertools.product("LRX", repeat=length):
                        word = "".join(letters)
                        counted = count_projections(v, m, r, word)
                        for row in counted["deletions"]:
                            j = row["j"]
                            replay = validator.replay_word(word, start_state=(v[:j] + v[j+1:], j))
                            self.assertEqual(row["projection_length"], replay.projection_length)
                            self.assertEqual(counted["final_vector"], replay.final_vector)
                            self.assertEqual(counted["terminal"], replay.terminal)

    def test_zero_swap_labels_continue_to_move(self):
        v = (0, 0, 1, 2)
        result = count_projections(v, 2, 2, "XLX")
        self.assertEqual(result["idle_zero_swaps"], 1)
        self.assertEqual([r["projection_length"] for r in result["deletions"]], [1, 1])

    def test_degenerate_domain_and_invalid_words_rejected(self):
        with self.assertRaises(ValueError):
            count_projections((1, 0), 1, 1, "L")
        with self.assertRaises(ValueError):
            count_projections((1, 2, 0), 2, 1, "Q")
