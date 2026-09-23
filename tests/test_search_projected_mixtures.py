import itertools
import unittest
from fractions import Fraction
from integrations.mixture_lp import optimize,solve
from integrations.projected_mixtures import project,comparison,materialize,verify_mixture
from test_search_nine_gap_audit import STATE,WORD

class ProjectedMixtureTests(unittest.TestCase):
    def test_exact_boundary_and_complementary_columns(self):
        ps=[dict(base=35,gamma=[8]),dict(base=36,gamma=[4])]
        result=optimize(ps)
        self.assertEqual(result['status'],'CERTIFICATE')
        self.assertEqual(result['weights'],['1/2','1/2'])
        self.assertEqual(result['base'],'71/2')
        verify_mixture(ps,result['weights'])
        with self.assertRaises(ValueError):verify_mixture([dict(base=37,gamma=[6])],['1'])
        self.assertEqual(optimize([dict(base=37,gamma=[6])])['status'],'NO_CERTIFICATE')
        self.assertEqual(optimize([dict(base=1,gamma=[7])])['status'],'NO_CERTIFICATE')

    def test_proposer_matches_exact_two_column_interval(self):
        for a,b in itertools.product(range(3,10),repeat=2):
            ps=[dict(base=32,gamma=[a]),dict(base=36,gamma=[b])]
            candidates=[Fraction(0),Fraction(1)]
            if a!=b:candidates.append(Fraction(6-b,a-b))
            feasible=[x for x in candidates if 0<=x<=1 and x*a+(1-x)*b<=6]
            result=optimize(ps)
            if feasible:
                expected=min(x*32+(1-x)*36 for x in feasible)
                self.assertEqual(Fraction(result['base']),expected)
                verify_mixture(ps,result['weights'])
            else:self.assertEqual(result['status'],'NO_CERTIFICATE')

    def test_projection_and_literal_expansion_all_masks(self):
        source=dict(state=STATE,word=WORD);checked=0
        for mask in range(1,512):
            state,word,_=project(source,mask,0)
            labels=[x for x in state if x]
            for cut in range(len(state)):
                p=comparison(state,word,cut,labels)
                if p:
                    lengths=[1+(j%3) for j in range(mask.bit_count())]
                    result=materialize(p,lengths)
                    self.assertLessEqual(result['length'],result['upper']);checked+=1
                    break
        self.assertEqual(checked,511)

    def test_reject_corruption(self):
        with self.assertRaises(ValueError):project(dict(state=STATE,word=WORD+'X'),511,0)
        with self.assertRaises(ValueError):project(dict(state=STATE,word=WORD),0,0)
        with self.assertRaises(ValueError):verify_mixture([dict(base=30,gamma=[2])],['2'])
        with self.assertRaises(ValueError):comparison(STATE,WORD,0,[1]*8)
        self.assertIsNone(solve([[1,2],[2,4]],[1,2],exact=True))

class MixtureRegressionTests(unittest.TestCase):
    def test_simplex_matches_exact_vertices_in_two_dimensions(self):
        import random
        rng=random.Random(73)
        for _ in range(80):
            ps=[dict(base=rng.randrange(20,60),gamma=[rng.randrange(13),rng.randrange(13)]) for _ in range(3)]
            constraints=[([p['gamma'][j] for p in ps],6) for j in range(2)]
            constraints += [([int(i==j) for i in range(3)],0) for j in range(3)]
            feasible=[]
            for rows in itertools.combinations(constraints,2):
                w=solve([[1]*3]+[a for a,b in rows],[1]+[b for a,b in rows],exact=True)
                if w is not None and min(w)>=0 and all(sum(x*p['gamma'][j] for x,p in zip(w,ps))<=6 for j in range(2)):
                    feasible.append(sum(x*p['base'] for x,p in zip(w,ps)))
            result=optimize(ps)
            if feasible:self.assertEqual(Fraction(result['base']),min(feasible))
            else:self.assertEqual(result['status'],'NO_CERTIFICATE')

    def test_archive_residual_byte_order_and_table_agree(self):
        from integrations.mixture_inventory import residual_inventory
        from pathlib import Path
        archive=Path(__file__).resolve().parents[1]/'autoresearch/loop-260923-2107/incoming/verification.zip'
        masks=residual_inventory(archive)
        self.assertEqual(sum(b.bit_count() for b in masks.values()),4495529)
        self.assertEqual((masks[300]>>58)&1,0)
        self.assertEqual((masks[90]>>19755)&1,1)
