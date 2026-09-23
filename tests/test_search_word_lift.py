"""Independent marked BFS checks for fixed-word routing and sweep construction."""
from collections import deque
from itertools import product
import unittest

from integrations.word_lift import lift_fixed_word,left_sweep_lift
from src.lrx.state import apply_marked_L,apply_marked_R,apply_marked_X
from src.lrx.certificates import replay_visible

OPS={'L':apply_marked_L,'R':apply_marked_R,'X':apply_marked_X}


def smaller_start(m,r,word):
    u=tuple(range(1,m+1))+(0,)*(r-1)
    for c in reversed(word):
        u=u[-1:]+u[:-1] if c=='L' else u[1:]+u[:1] if c=='R' else (u[1],u[0])+u[2:]
    return u


def changing_word(u,word):
    for c in word:
        v=replay_visible(u,c)
        if v==u: return False
        u=v
    return True


def reference(m,r,u,j,word):
    root=tuple(range(1,m+1))+(0,)*(r-1)
    queue=deque([((u,j),0,0)])
    seen={((u,j),0)}
    while queue:
        state,i,d=queue.popleft()
        if i==len(word) and state[0]==root and state[1]>=m:
            return d
        for c,op in OPS.items():
            nxt=op(state)
            k=i
            if nxt[0]!=state[0]:
                if i==len(word) or c!=word[i]: continue
                k+=1
            key=(nxt,k)
            if key not in seen:
                seen.add(key);queue.append((nxt,k,d+1))
    return None


class WordLiftTests(unittest.TestCase):
    def test_fixed_word_matches_independent_bfs(self):
        checked=0
        for m,r in ((2,1),(2,2),(3,1),(3,2)):
            for length in range(5):
                for letters in product('LRX',repeat=length):
                    word=''.join(letters);u=smaller_start(m,r,word)
                    for j in range(m+r):
                        if not changing_word(u,word): continue
                        result=lift_fixed_word(m,r,u,j,word)
                        checked+=1
                        self.assertEqual(result['length'],reference(m,r,u,j,word),(m,r,u,j,word))
        self.assertGreater(checked,1000)

    def test_left_sweep_bound_and_exact_router(self):
        successes=misses=0
        for m,r in ((2,1),(3,2),(4,2)):
            for length in range(8):
                for letters in product('LX',repeat=length):
                    word=''.join(letters);u=smaller_start(m,r,word)
                    for j in range(m+r):
                        if not changing_word(u,word): continue
                        result=left_sweep_lift(m,r,u,j,word)
                        if result['status']=='WITNESS':
                            successes+=1
                            exact=lift_fixed_word(m,r,u,j,word)
                            self.assertLessEqual(exact['length'],result['length'])
                            self.assertLessEqual(result['overhead'],result['overhead_bound'])
                        else: misses+=1
        self.assertGreater(successes,100)
        self.assertGreater(misses,100)

    def test_sweep_bound_is_sharp_in_conjecture_domain(self):
        for m,r in ((8,2),(8,9),(9,3),(12,20)):
            word='L'*(m+r-2)+'X'
            u=smaller_start(m,r,word)
            result=left_sweep_lift(m,r,u,m+r-1,word)
            self.assertEqual(result['overhead'],2)
            self.assertEqual(result['overhead_bound'],2)
            self.assertEqual(result['length'],m+r+1)

    def test_free_trajectory_subclass(self):
        checked=0
        m,r=3,2
        for length in range(5):
            for letters in product('LRX',repeat=length):
                word=''.join(letters);u=smaller_start(m,r,word)
                for initial in range(m+r):
                    j=initial;legal=True
                    for c in word:
                        if ((c=='L' and j==0) or (c=='R' and j==m+r-1)
                                or (c=='X' and j<2)):
                            legal=False;break
                        j+=-1 if c=='L' else 1 if c=='R' else 0
                    if not legal or (1<j<m): continue
                    if not changing_word(u,word): continue
                    result=lift_fixed_word(m,r,u,initial,word)
                    checked+=1
                    self.assertEqual(result['status'],'WITNESS')
                    self.assertLessEqual(result['overhead'],2)
        self.assertGreater(checked,20)

    def test_fixed_word_infeasibility_is_not_global(self):
        self.assertEqual(lift_fixed_word(4,2,(1,2,3,4,0),2,'')['status'],'NO_FIXED_WORD_LIFT')
        self.assertEqual(lift_fixed_word(4,2,(1,2,3,4,0),0,'')['length'],1)
        self.assertEqual(lift_fixed_word(4,2,(1,2,3,4,0),1,'')['length'],2)

    def test_bad_inputs(self):
        for args in [(1,1,(1,),0,''),(3,2,(1,2,3,0),5,''),
                     (3,2,(1,2,3,0),2,'Q'),(3,2,(2,1,3,0),2,''),
                     (2,3,(0,0,1,2),0,'X')]:
            with self.assertRaises(ValueError): lift_fixed_word(*args)
        with self.assertRaises(ValueError): left_sweep_lift(3,2,(2,3,0,1),0,'R')
