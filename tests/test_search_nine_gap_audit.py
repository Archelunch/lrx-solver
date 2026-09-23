"""Independent macro, rank and negative-control checks for supplied certificates."""
import unittest
from integrations.nine_gap_audit import profile,stretch,ranks,audit
from src.lrx.certificates import replay_visible

STATE=[0,5,0,6,0,4,0,3,0,2,0,1,0,8,0,7,0]
WORD='RRXLXLLXLLXLXLLXLLXLLXRXRRXRRXRXRRXRRXLXLXLXLXLXLXLLXLLLLXRXRXRXRRXRRXRXRXRXLXLXLLXRXRXRXRX'

class NineGapTests(unittest.TestCase):
    def test_multivariate_macros_match_symbolic_price_and_sort(self):
        info=profile(STATE,WORD)
        for lengths in ([1]*9,list(range(1,10)),[9,1,7,2,3,1,4,8,2]):
            initial,word=stretch(STATE,WORD,lengths)
            self.assertEqual(replay_visible(initial,word),tuple(range(1,9))+(0,)*sum(lengths))
            self.assertEqual(len(word),info['base']+sum(b*(ell-1) for b,ell in zip(info['beta'],lengths)))

    def test_physical_root_ranks_sorted_at_each_phase(self):
        root=list(range(1,9))+[0]*9
        for phase in range(17):
            physical=root[-phase:]+root[:-phase] if phase else root
            self.assertEqual(ranks(physical,0,phase),tuple(range(17)))

    def test_corrupted_reference_and_incomplete_universe_rejected(self):
        with self.assertRaises(ValueError):profile(STATE,WORD+'X')
        with self.assertRaises(ValueError):profile(STATE,WORD+'?')
        with self.assertRaises(ValueError):
            audit(dict(format='lrx_nine_gap_comparison_certificate_v1',m=8,slots=list(range(9)),records=[]))
