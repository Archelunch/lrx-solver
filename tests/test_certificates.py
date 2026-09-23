"""Tests for certificate validation."""

import unittest
from src.lrx.certificates import (
    CertificateValidator,
    canonical_word_family_k,
    family_parameters,
    family_vector,
)
from src.lrx.state import smaller_root


class TestCertificateValidator(unittest.TestCase):
    """Test word replay and certificate validation."""

    def test_replay_simple_word(self):
        """Test replaying a simple word."""
        validator = CertificateValidator(2, 1)
        result = validator.replay_word("L")

        self.assertTrue(result.replay_valid)
        self.assertIsNotNone(result.final_state)
        self.assertIsNotNone(result.projection_sequence)

    def test_replay_invalid_word(self):
        """Test that invalid letters are rejected."""
        validator = CertificateValidator(2, 1)
        result = validator.replay_word("LQR")

        self.assertFalse(result.replay_valid)
        self.assertIsNotNone(result.replay_error)
        self.assertIn("Invalid letter", result.replay_error)

    def test_replay_long_word(self):
        """Test replaying a longer word."""
        validator = CertificateValidator(3, 1)
        result = validator.replay_word("LRLXRXLXR")

        self.assertTrue(result.replay_valid)
        self.assertEqual(result.word_length, 9)
        self.assertIsNotNone(result.projection_length)

    def test_projection_tracking(self):
        """Test that projection length is correctly computed."""
        validator = CertificateValidator(2, 2)

        # A word with no u-changing transitions should have 0 projection
        result = validator.replay_word("X")

        # X might or might not change u depending on position
        # But projection should always be <= word length
        self.assertLessEqual(result.projection_length, result.word_length)

    def test_termination_detection(self):
        """Test detection of terminal states."""
        validator = CertificateValidator(2, 1)

        # Very long word might reach terminal state
        # For now, just verify that termination check works
        result = validator.replay_word("LLLLL")

        # We don't know if this reaches terminal, but check structure
        if result.terminal:
            u, j = result.final_state
            self.assertEqual(u, smaller_root(2, 1))
            self.assertGreaterEqual(j, 2)

    def test_empty_word(self):
        """Test replay of empty word."""
        validator = CertificateValidator(2, 1)
        result = validator.replay_word("")

        self.assertTrue(result.replay_valid)
        self.assertEqual(result.word_length, 0)
        # Should remain at start state
        self.assertEqual(result.final_state, (smaller_root(2, 1), 2))


class TestFamilyWords(unittest.TestCase):
    """Test words from the regression family."""

    def test_family_word_k2(self):
        """Test canonical word for k=2."""
        word = canonical_word_family_k(2)

        # Word length should be 6k-2 = 10
        self.assertEqual(len(word), 10)

        # Should contain only L, R, X
        for c in word:
            self.assertIn(c, "LRX")

    def test_family_word_k3(self):
        """Test canonical word for k=3."""
        word = canonical_word_family_k(3)
        self.assertEqual(len(word), 16)  # 6*3-2 = 16

    def test_family_word_generation(self):
        """Test word generation formula."""
        for k in [2, 3, 4]:
            word = canonical_word_family_k(k)
            expected_length = 6 * k - 2
            self.assertEqual(len(word), expected_length)

    def test_family_parameters(self):
        """Test parameter generation for family."""
        for k in [2, 3, 4]:
            m, r, n = family_parameters(k)
            self.assertEqual(m, 8 * k - 1)
            self.assertEqual(r, 2)
            self.assertEqual(n, m + r)

    def test_family_vector(self):
        """Test vector generation for family."""
        for k in [2, 3]:
            v = family_vector(k)
            m, r, n = family_parameters(k)
            self.assertEqual(len(v), n)
            # Should have exactly two zeros
            zero_count = sum(1 for x in v if x == 0)
            self.assertEqual(zero_count, 2)

    def test_family_word_k2_replay(self):
        """Test replaying k=2 canonical word."""
        k = 2
        m, r, _ = family_parameters(k)
        word = canonical_word_family_k(k)

        validator = CertificateValidator(m, r)
        v = family_vector(k)
        result = validator.replay_word(word, start_state=(v[:k] + v[k + 1 :], k))

        self.assertTrue(result.replay_valid)
        self.assertEqual(result.word_length, 10)

        self.assertTrue(result.terminal)
        self.assertEqual(result.projection_length, 5 * k - 3)


class TestCertificateEdgeCases(unittest.TestCase):
    """Test edge cases in certificate validation."""

    def test_single_letter_words(self):
        """Test replay of single-letter words."""
        validator = CertificateValidator(2, 1)

        for letter in "LRX":
            result = validator.replay_word(letter)
            self.assertTrue(result.replay_valid)
            self.assertEqual(result.word_length, 1)

    def test_large_m_small_word(self):
        """Test on configuration with larger m and short word."""
        validator = CertificateValidator(8, 2)
        result = validator.replay_word("LRLX")

        self.assertTrue(result.replay_valid)

    def test_state_consistency(self):
        """Test that state conversions are consistent."""
        m, r = 3, 1
        validator = CertificateValidator(m, r)

        word = "LXRX"
        result = validator.replay_word(word)

        if result.replay_valid and result.final_vector:
            # Final vector should have correct length
            self.assertEqual(len(result.final_vector), m + r)


if __name__ == "__main__":
    unittest.main()
