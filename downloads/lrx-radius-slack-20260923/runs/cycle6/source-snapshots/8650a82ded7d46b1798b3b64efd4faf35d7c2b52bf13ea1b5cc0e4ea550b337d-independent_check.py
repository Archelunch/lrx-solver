#!/usr/bin/env python3
"""Independent literal-tuple/resource BFS and word verifier, stdlib only."""
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time


def moves(s):
    return (s[1:] + s[:1], s[-1:] + s[:-1], (s[1], s[0]) + s[2:])


def bfs(root):
    dist = {root: 0}
    q = deque([root])
    while q:
        s = q.popleft()
        for t in moves(s):
            if t not in dist:
                dist[t] = dist[s] + 1
                q.append(t)
    return dist


def unmark(s):
    return tuple(0 if x == -1 else x for x in s)


def deletion(s):
    return tuple(x for x in s if x != -1)


def marked_bfs(m, r, P):
    """Reverse multi-source BFS in (literal marked word, projection length)."""
    goal = tuple(range(1, m + 1)) + (0,) * r
    dist, q = {}, deque()
    for j in range(m, m + r):
        s = goal[:j] + (-1,) + goal[j + 1:]
        dist[s, 0] = 0
        q.append((s, 0))
    best = {}
    while q:
        s, p = q.popleft()
        length = dist[s, p]
        v = unmark(s)
        best[v] = min(best.get(v, math.inf), length)
        deleted = deletion(s)
        for t in moves(s):
            if t == s:
                continue
            pp = p + int(deletion(t) != deleted)
            key = t, pp
            if pp <= P and key not in dist:
                dist[key] = length + 1
                q.append(key)
    return best, len(dist)


def literal_full_slack(m, r, extra=2):
    """A third calculation: literal resource BFS, then filter by full length."""
    goal = tuple(range(1, m + 1)) + (0,) * r
    actual = bfs(goal)
    cap = max(actual.values()) + extra
    dist, q = {}, deque()
    for j in range(m, m + r):
        s = goal[:j] + (-1,) + goal[j + 1:]
        dist[s, 0] = 0
        q.append((s, 0))
    profiles = [dict() for _ in range(extra + 1)]
    while q:
        s, p = q.popleft()
        length = dist[s, p]
        v = unmark(s)
        for e in range(max(0, length - actual[v]), extra + 1):
            profiles[e][v] = min(profiles[e].get(v, math.inf), p)
        if length == cap:
            continue
        deleted = deletion(s)
        for t in moves(s):
            if t == s:
                continue
            pp = p + int(deletion(t) != deleted)
            key = t, pp
            if key not in dist:
                dist[key] = length + 1
                q.append(key)
    return [{str(k): v for k, v in sorted(Counter(profile.values()).items())}
            for profile in profiles]


def verify_word(v, j, word, P, expected_length):
    assert v[j] == 0
    s = tuple(v[:j]) + (-1,) + tuple(v[j + 1:])
    projected = 0
    for letter in word:
        before = deletion(s)
        s = moves(s)["LRX".index(letter)]
        projected += deletion(s) != before
    m = max(v)
    assert unmark(s) == tuple(range(1, m + 1)) + (0,) * v.count(0)
    assert len(word) == expected_length
    assert projected <= P
    return {"length": len(word), "projection_length": projected,
            "endpoint": list(unmark(s)), "marked_endpoint": s.index(-1)}


def check_case(m, r, binary):
    start = time.monotonic()
    smaller = bfs(tuple(range(1, m + 1)) + (0,) * (r - 1))
    P = max(smaller.values())
    actual = bfs(tuple(range(1, m + 1)) + (0,) * r)
    lifts, expanded = marked_bfs(m, r, P)
    assert len(actual) == math.factorial(m + r) // math.factorial(r)
    assert len(smaller) == math.factorial(m + r - 1) // math.factorial(r - 1)
    hist = dict(sorted(Counter(lifts.values()).items()))
    gaps = dict(sorted(Counter(lifts[v] - actual[v] for v in lifts).items()))
    assert all(k >= 0 for k in gaps)
    result = {"m": m, "r": r, "P": P, "visible_states": len(actual),
              "expanded_states": expanded, "max_A_P": max(lifts.values()),
              "missing": len(actual) - len(lifts),
              "excess": sum(c > P + m - 2 for c in lifts.values()),
              "full_radius": max(actual.values()), "max_lift_gap": max(gaps),
              "histogram": {str(k): v for k, v in hist.items()},
              "gap_histogram": {str(k): v for k, v in gaps.items()}}
    if binary:
        proc = subprocess.run([str(binary), str(m), str(r), "--witness", "--full"],
                              check=True, capture_output=True, text=True)
        cpp = json.loads(proc.stdout)
        for key in ("P", "visible_states", "max_A_P", "missing", "excess",
                    "full_radius", "max_lift_gap", "histogram", "gap_histogram"):
            assert cpp[key] == result[key], (m, r, key, cpp[key], result[key])
        for sample in cpp["max_examples"] + cpp["violations"]:
            if sample["A_P"] >= 0:
                verify_word(sample["v"], sample["marked_index"], sample["word"], P, sample["A_P"])
        result["cpp_equal"] = True
    result["elapsed_seconds"] = round(time.monotonic() - start, 4)
    return result


def family_audit():
    results = []
    for k in range(2, 51):
        for m in (8*k-1, 8*k, 10*k):
            v = list(range(1, k+1)) + [0] + list(range(k+1, m-k+2)) + [0] + list(range(m-k+2, m+1))
            word = "L"*(k-1)+"X"+"RX"*(k-1)+"R"*k+"X"+"LX"*(k-2)+"LLL"
            marks = [j for j, x in enumerate(v) if x == 0]
            for j in marks:
                certificate = verify_word(v, j, word, 5*k-3, 6*k-2)
                assert certificate["projection_length"] == 5*k-3
            # Universal elementary radius lower bound: any label can start at
            # circular displacement floor((m+1)/2); each generator moves its
            # position by at most one. Used separately in the textual lemma.
            assert (m+1)//2 + (m-2) >= 6*k-2
            results.append({"k": k, "m": m, "word_length": len(word), "projection": 5*k-3})
    return {"cases": len(results), "marked_words": 2*len(results),
            "scope": "Explicit words and projection lengths only; no all-size distance lower bound inferred.",
            "results": results}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--binary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--verify-result", type=Path, action="append", default=[])
    p.add_argument("--family", action="store_true")
    p.add_argument("--packed-binary", type=Path)
    p.add_argument("--verify-packed", type=Path)
    a = p.parse_args()
    out = {"method": "literal marked-word resource BFS; independent of C++ ranks and recurrence", "cases": []}
    if a.packed_binary:
        out['packed_comparisons'] = []
        for n in range(4, 8):
            for m in range(2, n-1):
                r = n-m
                cpp = json.loads(subprocess.run([str(a.packed_binary.resolve()), str(m), str(r), '2'],
                                               check=True, capture_output=True, text=True).stdout)
                literal = literal_full_slack(m, r)
                assert literal == [layer['histogram'] for layer in cpp['layers']], (m, r)
                out['packed_comparisons'].append({'m': m, 'r': r, 'layers_equal': 3})
    if a.verify_packed:
        data = json.loads(a.verify_packed.read_text())
        out['packed_word_certificates'] = []
        for sample in data['exceptional_states']:
            for layer in sample['layers']:
                cert = verify_word(sample['v'], layer['marked_index'], layer['word'],
                                   layer['minimum_projection'], layer['word_length'])
                assert cert['projection_length'] == layer['minimum_projection']
                assert cert['length'] <= sample['distance'] + layer['extra_full_steps']
                out['packed_word_certificates'].append({'v': sample['v'], **cert})
    if a.family:
        out["family"] = family_audit()
    if a.verify_result:
        out["word_certificates"] = []
        for path in a.verify_result:
            data = json.loads(path.read_text())
            for sample in data["max_examples"] + data["violations"]:
                if "word" in sample:
                    c = verify_word(sample["v"], sample["marked_index"], sample["word"], data["P"], sample["A_P"])
                    out["word_certificates"].append({"source": str(path), "v": sample["v"], **c})
    elif not a.family and not a.packed_binary and not a.verify_packed:
        binary = a.binary.resolve() if a.binary else None
        for n in range(4, 8):
            for m in range(2, n-1):
                r = n-m
                row = check_case(m, r, binary)
                out["cases"].append(row)
                print(json.dumps({k: row[k] for k in ("m", "r", "P", "max_A_P", "full_radius", "missing", "excess")}), flush=True)
    out["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")


if __name__ == "__main__":
    main()
