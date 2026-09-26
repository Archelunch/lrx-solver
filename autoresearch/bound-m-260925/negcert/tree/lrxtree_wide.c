/* lrxtree_wide.c -- lrxtree.c with the vector in a 128-bit word (still 4 bits per cell): n <= 20, m <= 13
 * (symbols 0..m+2 <= 15 fit a nibble), up to 8 zeros.  Search entries store the 80-bit key (n-1 cells + context
 * in bits 76..79) as u64 + u16.  Model, abstraction, tables, verification, search order and output are those of
 * lrxtree.c unchanged; on every n <= 16 instance the two binaries must give identical minima and expansion counts
 * (crosscheck_wide.py).
 * Addition (driver convenience, same search): --batch FILE, lines "K s0,s1,...,s(n-1)": after the tables are
 * built and verified once, run the same passes (weighted, then exact) from every listed start vector (same
 * multiset of symbols as --u0) with its own K; each block of output is preceded by "BATCH i K".  Used for suffix
 * re-optimization: a RESULT NONE K there proves that start state has no accepted sorting word with F_W < K.
 * Addition 2: --target t0,...,t(n-1) (unit weights W = (1,0,0) only): the accepted terminal is the single vector
 * t (a rearrangement of --u0) instead of the canonical roots; each table is rooted at the abstraction of t (the
 * same backward Dijkstra and verify(), so h is again a verified lower bound on the distance to t), and a NONE K
 * proves every reduced word from the start vector to t has length >= K.  The graph is undirected and reversal
 * maps reduced words to reduced words, so this is d(start, t).  Used for prefix re-optimization.
 *
 * Header of lrxtree.c:
 * lrxtree.c -- lrxfast.c generalized to refined origins (tree leaves): n = m + r symbols, r >= 2 zeros.
 * Symbols: label x -> x-1, picked zero of block j -> m+j, every other zero -> m+2 (the code ZO of
 * negcert_general.encode; unweighted zeros are interchangeable: the cost and the zero-zero test read only
 * zero-ness and the two picked symbols).  Abstract roots = labels then every distinct arrangement of the zero
 * symbols (negcert_general.roots_of).  Everything else is lrxfast.c unchanged.
 *
 * Original header of lrxfast.c:
 * lrxfast.c -- C port of the exact oracle of negcert_general.py (same model, same abstraction, same proof).
 *
 * Model (Lemma C of negcert_general.py, transcribed letter by letter in step()):
 *   concrete state = (vector, context); vector = permutation of n = m+2 distinct symbols packed 4 bits each,
 *   position 0 (cursor) in the low nibble.  Symbols: label x -> x-1, zero of block j -> m+j.
 *   context c = kind*4 + flags, kind in {S=0, X=1, L=2, R=3}, flag bit j only for a weighted zero j.
 *   F_W = sum of step costs + final(c).  Reduced words only (no LR, RL, XX), as in the Python model.
 * Abstraction (Lemma A): labels -> class codes 0..k-1, zero j -> k+j; a table h(abstract vector, context) is the
 *   exact cost-to-go in the abstract graph (backward Dijkstra), then verify() checks independently of the build
 *   h(u,c) <= w + h(t,c') on every abstract node and letter, h(root,c) <= final(c), no node unreached.
 * Search (Theorem): A* with max over verified tables, integer f buckets, pruning every node with g + h >= K
 *   (K = claimed bound, or the best terminal found so far).  If the bucket loop ends with no terminal below K,
 *   every reduced (hence every accepted) sorting word has F_W >= K.  Node cap / memory exhaustion prints
 *   RESULT INCOMPLETE and never a bound.
 * Differences from the Python reference that do not change the proof:
 *   - with both zero weights 0 the two zeros keep distinct symbols (a double cover of the Python graph, same
 *     minimum, same roots up to zero order);
 *   - weighted mode (--omega a/b) orders buckets by a*g + b*h: a column generator only, never a bound.
 *
 * Usage: lrxfast --m M --u0 s0,s1,... --W wB,w0,w1 [--K K] [--table c1,c2,...,cm]... [--cap N] [--mem-gb G]
 *                [--threads T] [--omega b/a]... [--wcap N] [--then-exact] [--no-search]
 *   weighted passes (priority a*g + b*h, omega = b/a) run first, each capped at --wcap expansions; a word
 *   found there ends the run; otherwise, with --then-exact (or without --omega), the exact A* runs.
 *   --table gives the class index of labels 1..m (in label order).  lrxtree_wide adds --batch FILE, --batch-stop N.
 * Output lines: TABLE ..., START ..., WEIGHTED NOTFOUND|INCOMPLETE ..., WSTATS ..., STATS ...,
 *   RESULT FOUND F word | RESULT NONE K (a proof, exact pass only) | RESULT INCOMPLETE reason
 */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/time.h>

typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
typedef unsigned __int128 V;
#define NMAX 20
#define KEYSH 76

enum { KS = 0, KX = 1, KL = 2, KR = 3 };
#define INF 65535
#define MAXT 8

static int n, m, wB, W0, W1;
static V VMASK;
static int NC, CTX[16], CIDX[16];
static int ZC[3]; /* multiplicities of the zero symbols m, m+1, m+2 in the start vector */
static int HAVE_TGT = 0;
static V TGT;

static double now(void) {
    struct timeval tv;
    gettimeofday(&tv, 0);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}
static long rss_mb(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    return ru.ru_maxrss / (1024 * 1024); /* macOS: bytes */
}
static void *xmalloc(size_t s) {
    void *p = malloc(s);
    if (!p) {
        printf("RESULT INCOMPLETE malloc of %zu bytes failed\n", s);
        exit(3);
    }
    return p;
}

static inline V rotl(V v) { return (v >> 4) | ((v & 15) << (4 * (n - 1))); }
static inline V rotr(V v) { return ((v << 4) & VMASK) | (v >> (4 * (n - 1))); }
static inline V swp(V v) { return (v & ~(V)0xFF) | ((v & 15) << 4) | ((v >> 4) & 15); }

typedef struct {
    int zt;   /* symbols >= zt are zeros */
    int z[2]; /* symbol of weighted zero j, -1 if weight 0 */
} Space;

/* step(): exact transcription of negcert_general.make_step.  ch: 0=L 1=R 2=X.  Returns cost or -1. */
static inline int step(const Space *sp, V u, int c, int ch, V *t, int *c2) {
    int kind = c >> 2, cost = wB, nf = 0, j;
    if (ch == 0) {
        if (kind == KR) return -1;
        int u0 = (int)(u & 15);
        for (j = 0; j < 2; j++) {
            if (sp->z[j] < 0) continue;
            int w = j ? W1 : W0, fj = (c >> j) & 1, cr = u0 == sp->z[j];
            if (fj) {
                if (!cr) nf |= 1 << j;
            } else if (cr)
                cost += w;
        }
        *t = rotl(u);
        *c2 = KL * 4 + nf;
        return cost;
    }
    if (ch == 1) {
        if (kind == KL) return -1;
        V tt = rotr(u);
        int t0 = (int)(tt & 15);
        for (j = 0; j < 2; j++) {
            if (sp->z[j] < 0) continue;
            int w = j ? W1 : W0, fj = (c >> j) & 1, cr = t0 == sp->z[j];
            if (fj) {
                nf |= 1 << j;
                if (cr) cost += w;
            } else if (cr)
                nf |= 1 << j;
        }
        *t = tt;
        *c2 = KR * 4 + nf;
        return cost;
    }
    if (kind == KX) return -1;
    int a = (int)(u & 15), b = (int)((u >> 4) & 15);
    if (a >= sp->zt && b >= sp->zt) return -1;
    for (j = 0; j < 2; j++) {
        if (sp->z[j] < 0) continue;
        int w = j ? W1 : W0, fj = (c >> j) & 1, a0 = a == sp->z[j], a1 = b == sp->z[j];
        cost += w * (fj ? 1 - a0 : a0) + ((a0 || a1) ? 2 * w : 0);
        if (a1) nf |= 1 << j;
    }
    *t = swp(u);
    *c2 = KX * 4 + nf;
    return cost;
}
static inline int final_cost(int c) { return W0 * (c & 1) + W1 * ((c >> 1) & 1); }
static inline V inverse(V t, int kind) { return kind == KL ? rotr(t) : kind == KR ? rotl(t) : swp(t); }

/* ------------------------------------------------------------------ pattern tables */
typedef struct {
    int k, K;          /* classes, symbols (k + 2) */
    int cnt0[16];      /* multiplicity of each abstract symbol */
    u8 lut[256];       /* byte -> byte (two nibbles) concrete -> abstract */
    u64 N;             /* abstract vectors */
    u16 *h;            /* N * NC */
    Space sp;
    V root[256];
    int nroot;
} Table;

static inline V abstr(const Table *T, V v) {
    V r = 0;
    for (int i = 0; i < (n + 1) / 2; i++) r |= (V)T->lut[(int)((v >> (8 * i)) & 255)] << (8 * i);
    return r & VMASK;
}
static inline u64 rank_of(const Table *T, V a) {
    int cnt[16];
    memcpy(cnt, T->cnt0, sizeof cnt);
    u64 M = T->N, r = 0;
    int rem = n;
    for (int i = 0; i < n - 1; i++) {
        int s = (int)((a >> (4 * i)) & 15);
        u64 less = 0;
        for (int q = 0; q < s; q++) less += cnt[q];
        r += M * less / rem;
        M = M * cnt[s] / rem;
        cnt[s]--;
        rem--;
    }
    return r;
}
static inline V unrank(const Table *T, u64 r) {
    int cnt[16];
    memcpy(cnt, T->cnt0, sizeof cnt);
    u64 M = T->N;
    V a = 0;
    int rem = n;
    for (int i = 0; i < n; i++) {
        for (int s = 0; s < T->K; s++) {
            if (!cnt[s]) continue;
            u64 blk = M * cnt[s] / rem;
            if (r < blk) {
                a |= (V)s << (4 * i);
                M = blk;
                cnt[s]--;
                rem--;
                break;
            }
            r -= blk;
        }
    }
    return a;
}

static void table_init(Table *T, const int *cls /* class of label 1..m */) {
    int k = 0, smap[16] = {0};
    for (int x = 0; x < m; x++)
        if (cls[x] + 1 > k) k = cls[x] + 1;
    T->k = k;
    T->K = k + 2;
    memset(T->cnt0, 0, sizeof T->cnt0);
    for (int x = 0; x < m; x++) {
        smap[x] = cls[x];
        T->cnt0[cls[x]]++;
    }
    smap[m] = k;
    smap[m + 1] = k + 1;
    smap[m + 2] = k + 2;
    T->cnt0[k] = ZC[0];
    T->cnt0[k + 1] = ZC[1];
    T->cnt0[k + 2] = ZC[2];
    T->K = k + 3;
    for (int b = 0; b < 256; b++) T->lut[b] = smap[b & 15] | (smap[b >> 4] << 4);
    u64 N = 1;
    for (int i = 2; i <= n; i++) N *= i;
    for (int s = 0; s < T->K; s++)
        for (int i = 2; i <= T->cnt0[s]; i++) N /= i;
    T->N = N;
    T->sp.zt = k;
    T->sp.z[0] = W0 ? k : -1;
    T->sp.z[1] = W1 ? k + 1 : -1;
    V lab = 0;
    for (int x = 0; x < m; x++) lab |= (V)cls[x] << (4 * x);
    /* every distinct arrangement of the zero symbols k, k+1, (k+2)^extra after the labels */
    int r = n - m;
    T->nroot = 0;
    if (HAVE_TGT) {
        T->root[T->nroot++] = abstr(T, TGT);
        return;
    }
    /* enumerate r-digit words over {0,1,2} with digit counts (1, 1, extra) */
    int tot = 1;
    for (int i = 0; i < r; i++) tot *= 3;
    for (int code = 0; code < tot; code++) {
        int c = code, cnt[3] = {0, 0, 0};
        V v = lab;
        for (int q = 0; q < r; q++) {
            int d = c % 3;
            c /= 3;
            cnt[d]++;
            v |= (V)(k + d) << (4 * (m + q));
        }
        if (cnt[0] == ZC[0] && cnt[1] == ZC[1] && cnt[2] == ZC[2]) {
            if (T->nroot >= 256) { printf("RESULT ERROR too many abstract roots\n"); exit(2); }
            T->root[T->nroot++] = v;
        }
    }
}

/* buckets: LIFO stacks of fixed blocks from a shared free list (no realloc copying, bounded memory) */
#define BLK 16384
typedef struct Blk {
    struct Blk *next;
    u32 len;
    u32 a[BLK];
} Blk;
typedef struct {
    Blk *head;
} Bucket;
static __thread Blk *freelist = 0;
static __thread size_t bucket_bytes = 0;
static size_t bucket_limit = (size_t)-1;
static int bucket_push(Bucket *b, u32 x) {
    if (!b->head || b->head->len == BLK) {
        Blk *k = freelist;
        if (k)
            freelist = k->next;
        else {
            if (bucket_bytes + sizeof(Blk) > bucket_limit) return -1;
            k = malloc(sizeof(Blk));
            if (!k) return -1;
            bucket_bytes += sizeof(Blk);
        }
        k->len = 0;
        k->next = b->head;
        b->head = k;
    }
    b->head->a[b->head->len++] = x;
    return 0;
}
static inline int bucket_pop(Bucket *b, u32 *x) {
    while (b->head && b->head->len == 0) {
        Blk *k = b->head;
        b->head = k->next;
        k->next = freelist;
        freelist = k;
    }
    if (!b->head) return 0;
    *x = b->head->a[--b->head->len];
    return 1;
}
static void bucket_free(Bucket *b) {
    u32 x;
    while (bucket_pop(b, &x)) b->head->len = 0;
}

/* backward Dijkstra from the abstract roots (as PatternTable.__init__), level-synchronous over integer values:
 * all nodes with h == val are final (every write stores val + cost > val), so the threads of one level only
 * lower entries of later levels, with an atomic min; stale bucket entries are skipped. */
typedef struct {
    Table *T;
    int id, nth, R;
    Bucket *ring;
    u64 pending;
} BArg;
static pthread_mutex_t bmu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t bcv = PTHREAD_COND_INITIALIZER;
static int bcount = 0, bgen = 0, bval = 0, bdone = 0;
static u64 bpend_total = 0;
static BArg *BARGS;
static void level_barrier(int nth) {
    /* last thread in: sum pending, decide termination, advance the level */
    pthread_mutex_lock(&bmu);
    int gen = bgen;
    if (++bcount == nth) {
        u64 tot = 0;
        for (int i = 0; i < nth; i++) tot += BARGS[i].pending;
        bpend_total = tot;
        bdone = tot == 0;
        bval++;
        bcount = 0;
        bgen++;
        pthread_cond_broadcast(&bcv);
    } else
        while (gen == bgen) pthread_cond_wait(&bcv, &bmu);
    pthread_mutex_unlock(&bmu);
}
static void *build_worker(void *p) {
    BArg *A = p;
    Table *T = A->T;
    int R = A->R;
    for (;;) {
        int val = bval;
        Bucket *b = &A->ring[val % R];
        u32 node;
        while (bucket_pop(b, &node)) {
            A->pending--;
            if (__atomic_load_n(&T->h[node], __ATOMIC_RELAXED) != val) continue;
            u64 j = node / NC;
            int c2 = CTX[node % NC], kind = c2 >> 2, ch = kind == KL ? 0 : kind == KR ? 1 : 2;
            V t = unrank(T, j), u = inverse(t, kind);
            u64 ju = rank_of(T, u) * NC;
            for (int ci = 0; ci < NC; ci++) {
                V tt;
                int cc, cost = step(&T->sp, u, CTX[ci], ch, &tt, &cc);
                if (cost < 0 || cc != c2) continue;
                int w = val + cost;
                if (w >= INF) { printf("RESULT INCOMPLETE table value overflow\n"); exit(3); }
                u16 *hp = &T->h[ju + ci], old = __atomic_load_n(hp, __ATOMIC_RELAXED);
                int won = 0;
                while (w < old) {
                    if (__atomic_compare_exchange_n(hp, &old, (u16)w, 0, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {
                        won = 1;
                        break;
                    }
                }
                if (won) {
                    if (bucket_push(&A->ring[w % R], (u32)(ju + ci))) { printf("RESULT INCOMPLETE bucket memory\n"); exit(3); }
                    A->pending++;
                }
            }
        }
        level_barrier(A->nth);
        if (bdone) break;
    }
    while (freelist) {
        Blk *k = freelist;
        freelist = k->next;
        free(k);
    }
    return 0;
}
static void table_build(Table *T, int nth) {
    u64 NN = T->N * NC;
    if (NN >= 0xFFFFFFFFull) {
        printf("RESULT INCOMPLETE table too large for u32 node ids\n");
        exit(3);
    }
    if (nth < 1) nth = 1;
    if (nth > 64) nth = 64;
    T->h = xmalloc(NN * sizeof(u16));
    memset(T->h, 0xFF, NN * sizeof(u16));
    int R = wB + 3 * (W0 + W1) + 2;
    BArg A[64];
    pthread_t th[64];
    BARGS = A;
    for (int i = 0; i < nth; i++) {
        A[i].T = T;
        A[i].id = i;
        A[i].nth = nth;
        A[i].R = R;
        A[i].ring = calloc(R, sizeof(Bucket));
        A[i].pending = 0;
    }
    int sp = 0;
    for (int r = 0; r < T->nroot; r++) {
        u64 j = rank_of(T, T->root[r]);
        for (int ci = 0; ci < NC; ci++) {
            int v = final_cost(CTX[ci]);
            u64 node = j * NC + ci;
            if (v < T->h[node]) {
                T->h[node] = v;
                /* seeded in the main thread's free list scope: push via a temporary, handed to worker sp */
                Bucket *bb = &A[sp % nth].ring[v % R];
                Blk *k = malloc(sizeof(Blk));
                k->len = 0;
                k->next = bb->head;
                bb->head = k;
                k->a[k->len++] = (u32)node;
                A[sp % nth].pending++;
                sp++;
            }
        }
    }
    bcount = 0;
    bgen = 0;
    bval = 0;
    bdone = 0;
    for (int i = 0; i < nth; i++) pthread_create(&th[i], 0, build_worker, &A[i]);
    for (int i = 0; i < nth; i++) {
        pthread_join(th[i], 0);
        free(A[i].ring);
    }
}

/* verify(): independent of the build; parallel over vector ranks */
typedef struct {
    Table *T;
    u64 lo, hi, edges, hmax, bad;
    char msg[200];
} VArg;
static void *verify_worker(void *p) {
    VArg *A = p;
    Table *T = A->T;
    for (u64 j = A->lo; j < A->hi && !A->bad; j++) {
        V u = unrank(T, j);
        int isroot = 0;
        for (int r = 0; r < T->nroot; r++) isroot |= u == T->root[r];
        u64 rk[3] = {~0ull, ~0ull, ~0ull};
        for (int ci = 0; ci < NC; ci++) {
            int c = CTX[ci], hv = T->h[j * NC + ci];
            if (hv >= INF) {
                A->bad = 1;
                snprintf(A->msg, 200, "unreached abstract node rank %llu ctx %d", (unsigned long long)j, c);
                break;
            }
            if ((u64)hv > A->hmax) A->hmax = hv;
            if (isroot && hv > final_cost(c)) {
                A->bad = 1;
                snprintf(A->msg, 200, "h exceeds final cost at an abstract root");
                break;
            }
            for (int ch = 0; ch < 3; ch++) {
                V t;
                int c2, cost = step(&T->sp, u, c, ch, &t, &c2);
                if (cost < 0) continue;
                if (rk[ch] == ~0ull) rk[ch] = rank_of(T, t);
                A->edges++;
                if (hv > cost + T->h[rk[ch] * NC + CIDX[c2]]) {
                    A->bad = 1;
                    snprintf(A->msg, 200, "inconsistent h at rank %llu ctx %d letter %d", (unsigned long long)j, c, ch);
                    break;
                }
            }
        }
    }
    return 0;
}
static int table_verify(Table *T, int nth, u64 *edges, u64 *hmax) {
    pthread_t th[64];
    VArg A[64];
    if (nth < 1) nth = 1;
    if (nth > 64) nth = 64;
    for (int i = 0; i < nth; i++) {
        memset(&A[i], 0, sizeof A[i]);
        A[i].T = T;
        A[i].lo = T->N * i / nth;
        A[i].hi = T->N * (i + 1) / nth;
        pthread_create(&th[i], 0, verify_worker, &A[i]);
    }
    int ok = 1;
    *edges = *hmax = 0;
    for (int i = 0; i < nth; i++) {
        pthread_join(th[i], 0);
        *edges += A[i].edges;
        if (A[i].hmax > *hmax) *hmax = A[i].hmax;
        if (A[i].bad) {
            ok = 0;
            printf("VERIFY FAILED: %s\n", A[i].msg);
        }
    }
    return ok;
}

/* ------------------------------------------------------------------ concrete search */
static Table TB[MAXT];
static int NT = 0, ANYTIME = 0;
static Space CSP;

static inline int H(V v, int c) {
    int best = 0, ci = CIDX[c];
    for (int i = 0; i < NT; i++) {
        int x = TB[i].h[rank_of(&TB[i], abstr(&TB[i], v)) * NC + ci];
        if (x > best) best = x;
    }
    return best;
}

#pragma pack(push, 1)
typedef struct {
    u64 key;  /* low 64 bits of the 80-bit key */
    u16 khi;  /* bits 64..79 */
    u16 g, h;
} Ent;
#pragma pack(pop)
/* dense node pool (chunked, indices stable) + open-addressing index with 32-bit fingerprints */
#define PCH 22
static Ent **POOL;
static u64 NPOOL = 0, NCHUNK = 0, MAXCHUNK;
static u64 *HX, HCAP = 0;
static size_t MEM_BUDGET, MEM_FIXED;
static V LOWMASK;
static u64 XORALL;
static inline Ent *ent(u64 i) { return &POOL[i >> PCH][i & ((1ull << PCH) - 1)]; }
static inline V pack(V v, int c) { return (v & LOWMASK) | ((V)c << KEYSH); }
static inline V ekey(const Ent *e) { return ((V)e->khi << 64) | e->key; }
static inline V unpack(V key, int *c) {
    V v = key & LOWMASK;
    u64 x = (u64)v ^ (u64)(v >> 64);
    x ^= x >> 32;
    x ^= x >> 16;
    x ^= x >> 8;
    x ^= x >> 4;
    *c = (int)(key >> KEYSH);
    return v | ((V)(((x & 15) ^ XORALL) & 15) << (4 * (n - 1)));
}
static inline u64 mix(V k) {
    u64 x = ((u64)k ^ ((u64)(k >> 64) * 0xD6E8FEB86659FD93ull)) * 0x9E3779B97F4A7C15ull;
    x ^= x >> 31;
    x *= 0xBF58476D1CE4E5B9ull;
    x ^= x >> 29;
    return x;
}
static size_t mem_used(void) { return MEM_FIXED + NCHUNK * (sizeof(Ent) << PCH) + HCAP * 8 + bucket_bytes; }
/* returns the index slot; *idx = pool index if present, else ~0 */
static inline u64 hfind(V key, u64 *idx) {
    u64 hs = mix(key), fp = hs >> 32, i = hs & (HCAP - 1);
    for (;;) {
        u64 x = HX[i];
        if (!x) {
            *idx = ~0ull;
            return i;
        }
        if ((x >> 32) == fp && ekey(ent((x & 0xFFFFFFFFull) - 1)) == key) {
            *idx = (x & 0xFFFFFFFFull) - 1;
            return i;
        }
        i = (i + 1) & (HCAP - 1);
    }
}
static int hgrow(void) {
    u64 nc = HCAP ? HCAP * 2 : (1ull << 24);
    if (mem_used() + nc * 8 > MEM_BUDGET) return -1;
    u64 *nx = calloc(nc, 8);
    if (!nx) return -1;
    free(HX);
    HX = nx;
    HCAP = nc;
    for (u64 i = 0; i < NPOOL; i++) {
        u64 hs = mix(ekey(ent(i))), j = hs & (HCAP - 1);
        while (HX[j]) j = (j + 1) & (HCAP - 1);
        HX[j] = ((hs >> 32) << 32) | (i + 1);
    }
    return 0;
}
/* insert a new node at index slot sl (from hfind); returns pool index or ~0 on memory exhaustion */
static u64 hinsert(u64 sl, V key, int g, int h) {
    if (NPOOL >= 0xFFFFFFF0ull) return ~0ull;
    if ((NPOOL >> PCH) >= NCHUNK) {
        if (NCHUNK >= MAXCHUNK || mem_used() + (sizeof(Ent) << PCH) > MEM_BUDGET) return ~0ull;
        POOL[NCHUNK] = malloc(sizeof(Ent) << PCH);
        if (!POOL[NCHUNK]) return ~0ull;
        NCHUNK++;
    }
    u64 i = NPOOL++;
    Ent *e = ent(i);
    e->key = (u64)key;
    e->khi = (u16)(key >> 64);
    e->g = g;
    e->h = h;
    HX[sl] = ((mix(key) >> 32) << 32) | (i + 1);
    if (NPOOL * 4 > HCAP * 3) {        /* load 0.75: grow if memory allows, else tolerate up to 0.92 */
        if (hgrow() && NPOOL * 100 > HCAP * 92) return ~0ull;
    }
    return i;
}

static void search_reset(void) {
    for (u64 i = 0; i < NCHUNK; i++) free(POOL[i]);
    NCHUNK = NPOOL = 0;
    free(HX);
    HX = 0;
    HCAP = 0;
}
/* one search pass; oa = ob = 0: exact A*; otherwise weighted (priority oa*g + ob*h), a column generator only.
   returns 0 found, 1 none / not found, 3 incomplete */
static int search(V u0, int K, int oa, int ob, long long cap, V rootmask, V rootpat, double t0) {
    search_reset();
    if (hgrow()) { printf("RESULT INCOMPLETE no memory left for the search\n"); return 3; }
    int Kcur = K >= 0 ? K : 60000;
    int weighted = oa > 0 && ob > 0;
    if (!weighted) oa = ob = 1;
    size_t NB = (size_t)(oa + ob) * (Kcur + 1) + 1;
    Bucket *bk = calloc(NB, sizeof(Bucket));
    u64 idx, sl = hfind(pack(u0, KS), &idx);
    hinsert(sl, pack(u0, KS), 0, 0);
    bucket_push(&bk[0], 0);
    long long expanded = 0;
    int best_term = Kcur;
    u64 term_idx = 0;
    const char *incomplete = 0;
    double ts = now(), tlog = ts;
    size_t p;
    for (p = 0; p < NB && !incomplete; p++) {
        if (!weighted && (int)p >= best_term) break;
        Bucket *b = &bk[p];
        u32 s;
        while (bucket_pop(b, &s)) {
            Ent *e = ent(s);
            {   /* stale: its current priority (clamped as when pushed) differs from this bucket */
                size_t pe = (size_t)oa * e->g + (size_t)ob * e->h;
                if (weighted ? pe > p : pe != p) continue;
            }
            if (weighted && e->g + e->h >= best_term) continue;
            if (e->g + e->h >= best_term) continue;
            expanded++;
            if (cap && expanded > cap) { incomplete = "node cap reached"; break; }
            if ((expanded & 0xFFFFF) == 0 && now() - tlog > 30) {
                tlog = now();
                fprintf(stderr, "  ... %lldM expansions, f=%d, stored %llu, %.0f s, mem %.2f GB\n", expanded >> 20,
                        e->g + e->h, (unsigned long long)NPOOL, tlog - ts, mem_used() / 1073741824.0);
            }
            int c, g = e->g;
            V v = unpack(ekey(e), &c);
            if (HAVE_TGT ? v == TGT : (v & rootmask) == rootpat) {
                int tot = g + final_cost(c);
                if (tot < best_term) {
                    best_term = tot;
                    term_idx = s;
                    if (weighted && !ANYTIME) break;
                }
            }
            for (int ch = 0; ch < 3; ch++) {
                V t;
                int c2, cost = step(&CSP, v, c, ch, &t, &c2);
                if (cost < 0) continue;
                int ng = g + cost;
                V k2 = pack(t, c2);
                u64 i2, sl2 = hfind(k2, &i2);
                int hv;
                if (i2 != ~0ull) {
                    Ent *e2 = ent(i2);
                    if (e2->g <= ng) continue;
                    hv = e2->h;
                    if (ng + hv >= best_term) continue;
                    e2->g = ng;
                } else {
                    hv = H(t, c2);
                    if (ng + hv >= best_term) continue;
                    i2 = hinsert(sl2, k2, ng, hv);
                    if (i2 == ~0ull) { incomplete = "node store full (memory cap)"; break; }
                }
                size_t pr = (size_t)oa * ng + (size_t)ob * hv;
                if (pr < p) pr = p; /* weighted priorities can decrease along an edge: keep it in the current bucket */
                if (bucket_push(&bk[pr], (u32)i2)) { incomplete = "bucket memory exhausted (memory cap)"; break; }
            }
            if (incomplete) break;
            if (weighted && !ANYTIME && best_term < Kcur) break;
        }
        if (weighted && !ANYTIME && best_term < Kcur) break;
        if (incomplete) break; /* keep p = the interrupted bucket */
        bucket_free(b);
    }
    double te = now();
    printf("%s expanded=%lld stored=%llu search_s=%.1f total_s=%.1f rss_mb=%ld mem_gb=%.2f omega=%d/%d\n", weighted ? "WSTATS" : "STATS", expanded,
           (unsigned long long)NPOOL, te - ts, te - t0, rss_mb(), mem_used() / 1073741824.0, ob, oa);
    fflush(stdout);
    for (size_t q = 0; q < NB; q++) bucket_free(&bk[q]);
    free(bk);
    if (incomplete && !(weighted && best_term < Kcur)) {
        if (weighted) printf("WEIGHTED INCOMPLETE %s (priority bucket %zu)\n", incomplete, p);
        else printf("RESULT INCOMPLETE %s (interrupted bucket f=%zu; every bucket below it was fully expanded, so min F >= %zu is proved)\n", incomplete, p, p);
        return 3;
    }
    if (best_term >= Kcur) {
        if (weighted) printf("WEIGHTED NOTFOUND weighted search is not exhaustive: no bound\n");
        else if (K >= 0) printf("RESULT NONE %d\n", K);
        else { printf("RESULT INCOMPLETE no terminal below internal limit %d\n", Kcur); return 3; }
        return 1;
    }
    /* reconstruct: walk back through stored g-values (predecessor with g_p + cost <= g) */
    char *word = xmalloc(1 << 16);
    int wl = 0, c;
    V u = unpack(ekey(ent(term_idx)), &c);
    int g = ent(term_idx)->g;
    while (!(u == u0 && c == KS)) {
        int kind = c >> 2, ch = kind == KL ? 0 : kind == KR ? 1 : 2, ok = 0;
        V pv = inverse(u, kind);
        for (int q = -1; q < NC && !ok; q++) {
            int pc = q < 0 ? KS : CTX[q];
            if (q < 0 && pv != u0) continue;
            u64 ps;
            hfind(pack(pv, pc), &ps);
            if (ps == ~0ull) continue;
            V t;
            int c2, cost = step(&CSP, pv, pc, ch, &t, &c2);
            if (cost >= 0 && t == u && c2 == c && ent(ps)->g + cost <= g) {
                ok = 1;
                word[wl++] = "LRX"[ch];
                u = pv;
                c = pc;
                g = ent(ps)->g;
            }
        }
        if (!ok || wl >= (1 << 16) - 1) { printf("RESULT ERROR reconstruction failed\n"); exit(2); }
    }
    for (int i = 0; i < wl / 2; i++) {
        char x = word[i];
        word[i] = word[wl - 1 - i];
        word[wl - 1 - i] = x;
    }
    word[wl] = 0;
    printf("RESULT FOUND %d %s\n", best_term, word);
    free(word);
    return 0;
}

int main(int argc, char **argv) {
    int u0s[NMAX + 1], nu = 0, K = -1, tables[MAXT][16], nth = 4, nosearch = 0, om_a[8], om_b[8], nom = 0, then_exact = 0;
    long long cap = 0, wcap = 0;
    const char *batch = 0;
    int batch_stop = 0, inc_run = 0;
    double memgb = 11.0;
    for (int i = 1; i < argc; i++) {
        char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : "";
        if (!strcmp(a, "--m")) m = atoi(v), i++;
        else if (!strcmp(a, "--u0")) {
            for (char *p = v; *p;) {
                if (nu > NMAX) { printf("RESULT ERROR n > %d\n", NMAX); return 2; }
                u0s[nu++] = (int)strtol(p, &p, 10);
                if (*p == ',') p++;
            }
            i++;
        } else if (!strcmp(a, "--W")) sscanf(v, "%d,%d,%d", &wB, &W0, &W1), i++;
        else if (!strcmp(a, "--K")) K = atoi(v), i++;
        else if (!strcmp(a, "--cap")) cap = atoll(v), i++;
        else if (!strcmp(a, "--mem-gb")) memgb = atof(v), i++;
        else if (!strcmp(a, "--threads")) nth = atoi(v), i++;
        else if (!strcmp(a, "--omega") && nom < 8) { sscanf(v, "%d/%d", &om_b[nom], &om_a[nom]); nom++; i++; } /* omega = b/a */
        else if (!strcmp(a, "--wcap")) wcap = atoll(v), i++;
        else if (!strcmp(a, "--then-exact")) then_exact = 1;
        else if (!strcmp(a, "--anytime")) ANYTIME = 1; /* weighted passes keep improving the incumbent until --wcap */
        else if (!strcmp(a, "--no-search")) nosearch = 1;
        else if (!strcmp(a, "--batch")) batch = v, i++;
        else if (!strcmp(a, "--target")) {
            int x = 0;
            for (char *p = v; *p && x <= NMAX;) {
                TGT |= (V)(strtol(p, &p, 10) & 15) << (4 * x++);
                if (*p == ',') p++;
            }
            HAVE_TGT = x;
            i++;
        }
        else if (!strcmp(a, "--batch-stop")) batch_stop = atoi(v), i++; /* stop after N consecutive INCOMPLETE */
        else if (!strcmp(a, "--table")) {
            int x = 0;
            for (char *p = v; *p;) {
                tables[NT][x++] = (int)strtol(p, &p, 10);
                if (*p == ',') p++;
            }
            if (x != m) { printf("RESULT ERROR table needs %d classes\n", m); return 2; }
            NT++, i++;
        } else { printf("RESULT ERROR bad argument %s\n", a); return 2; }
    }
    n = nu;
    if (n < m + 2 || n > NMAX || n - m > 8 || m > 13 || m < 2 || wB < 1 || W0 < 0 || W1 < 0) { printf("RESULT ERROR bad parameters\n"); return 2; }
    {
        int seen[16] = {0};
        for (int i = 0; i < n; i++) {
            if (u0s[i] < 0 || u0s[i] > m + 2 || (u0s[i] < m && seen[u0s[i]])) { printf("RESULT ERROR u0: labels 0..m-1 once, zero symbols m, m+1 at most once, m+2 for the other zeros\n"); return 2; }
            seen[u0s[i]]++;
        }
        for (int i = 0; i < m; i++) if (seen[i] != 1) { printf("RESULT ERROR u0 misses a label\n"); return 2; }
        ZC[0] = seen[m], ZC[1] = seen[m + 1], ZC[2] = seen[m + 2];
        /* a weighted zero must be present, once; an unweighted picked zero may be encoded as m+2 */
        if (ZC[0] > 1 || ZC[1] > 1 || (W0 && ZC[0] != 1) || (W1 && ZC[1] != 1) || n - m < 2) { printf("RESULT ERROR u0 zero symbols\n"); return 2; }
    }
    if (HAVE_TGT) {
        int tc[16] = {0}, uc[16] = {0};
        for (int i = 0; i < n; i++) uc[u0s[i]]++, tc[(int)((TGT >> (4 * i)) & 15)]++;
        if (HAVE_TGT != n || memcmp(tc, uc, sizeof tc) || W0 || W1) { printf("RESULT ERROR --target: a rearrangement of --u0, W = (1,0,0) only\n"); return 2; }
    }
    VMASK = ((V)1 << (4 * n)) - 1;
    LOWMASK = ((V)1 << (4 * (n - 1))) - 1;
    XORALL = 0;
    for (int i = 0; i < n; i++) XORALL ^= u0s[i];
    /* contexts(W) */
    NC = 0;
    for (int i = 0; i < 16; i++) CIDX[i] = -1;
    for (int kind = KX; kind <= KR; kind++)
        for (int f = 0; f < 4; f++) {
            if ((f & 1) && !W0) continue;
            if ((f & 2) && !W1) continue;
            if (kind == KX && f == 3) continue;
            CIDX[kind * 4 + f] = NC;
            CTX[NC++] = kind * 4 + f;
        }
    CSP.zt = m;
    CSP.z[0] = W0 ? m : -1;
    CSP.z[1] = W1 ? m + 1 : -1;
    V u0 = 0;
    for (int i = 0; i < n; i++) u0 |= (V)u0s[i] << (4 * i);
    V rootpat = 0;
    for (int i = 0; i < m; i++) rootpat |= (V)i << (4 * i);
    V rootmask = ((V)1 << (4 * m)) - 1;
    double t0 = now();
    size_t pdb_bytes = 0;
    int allok = 1;
    for (int ti = 0; ti < NT; ti++) {
        double t1 = now();
        table_init(&TB[ti], tables[ti]);
        table_build(&TB[ti], nth);
        double t2 = now();
        u64 edges, hmax;
        int ok = table_verify(&TB[ti], nth, &edges, &hmax);
        pdb_bytes += TB[ti].N * NC * 2;
        /* start bound for this table alone */
        int sb = -1;
        for (int ch = 0; ch < 3; ch++) {
            V t;
            int c2, cost = step(&CSP, u0, 0, ch, &t, &c2);
            if (cost < 0) continue;
            int v = cost + TB[ti].h[rank_of(&TB[ti], abstr(&TB[ti], t)) * NC + CIDX[c2]];
            if (sb < 0 || v < sb) sb = v;
        }
        printf("TABLE %d classes=%d vectors=%llu nodes=%llu edges=%llu %s maxh=%llu start_bound=%d build_s=%.1f verify_s=%.1f rss_mb=%ld\n",
               ti, TB[ti].k, (unsigned long long)TB[ti].N, (unsigned long long)(TB[ti].N * NC), (unsigned long long)edges,
               ok ? "consistent" : "INCONSISTENT", (unsigned long long)hmax, sb, t2 - t1, now() - t2, rss_mb());
        fflush(stdout);
        allok &= ok;
    }
    if (!allok) { printf("RESULT ERROR table verification failed\n"); return 1; }
    int sb = -1;
    for (int ch = 0; ch < 3; ch++) {
        V t;
        int c2, cost = step(&CSP, u0, 0, ch, &t, &c2);
        if (cost < 0) continue;
        int v = cost + H(t, c2);
        if (sb < 0 || v < sb) sb = v;
    }
    printf("START bound=%d\n", sb);
    fflush(stdout);
    if (nosearch) return 0;

    MEM_BUDGET = (size_t)(memgb * 1073741824.0);
    MEM_FIXED = pdb_bytes + (size_t)(0.25 * 1073741824.0);
    if (MEM_FIXED + (1ull << 28) > MEM_BUDGET) { printf("RESULT INCOMPLETE no memory left for the search\n"); return 3; }
    bucket_limit = MEM_BUDGET;
    MAXCHUNK = 1 + (MEM_BUDGET >> PCH) / sizeof(Ent);
    POOL = calloc(MAXCHUNK, sizeof(Ent *));
    int rc = 3;
    if (batch) {
        FILE *bf = fopen(batch, "r");
        if (!bf) { printf("RESULT ERROR cannot open batch file\n"); return 2; }
        char line[512];
        int bi = 0;
        while (fgets(line, sizeof line, bf)) {
            char *p = line;
            int bK = (int)strtol(p, &p, 10), cnt[16] = {0}, x = 0;
            V bu = 0;
            u64 bx = 0;
            while (*p && *p != '\n') {
                while (*p == ' ' || *p == ',') p++;
                if (!*p || *p == '\n') break;
                int sym = (int)strtol(p, &p, 10);
                if (sym < 0 || sym > 15 || x >= n) { printf("RESULT ERROR bad batch line %d\n", bi); return 2; }
                cnt[sym]++;
                bx ^= sym;
                bu |= (V)sym << (4 * x++);
            }
            int okm = x == n && bx == XORALL;
            for (int q = 0; q < m; q++) okm &= cnt[q] == 1;
            okm &= cnt[m] == ZC[0] && cnt[m + 1] == ZC[1] && cnt[m + 2] == ZC[2];
            if (!okm) { printf("RESULT ERROR batch line %d is not a rearrangement of --u0\n", bi); return 2; }
            printf("BATCH %d %d\n", bi++, bK);
            fflush(stdout);
            int brc = 3;
            for (int ps = 0; ps < nom; ps++) {
                brc = search(bu, bK, om_a[ps], om_b[ps], wcap, rootmask, rootpat, t0);
                if (brc == 0) break;
            }
            if (brc != 0 && (nom == 0 || then_exact)) brc = search(bu, bK, 0, 0, cap, rootmask, rootpat, t0);
            fflush(stdout);
            inc_run = brc == 3 ? inc_run + 1 : 0;
            if (batch_stop && inc_run >= batch_stop) { printf("BATCH STOP after %d consecutive INCOMPLETE\n", inc_run); break; }
        }
        fclose(bf);
        return 0;
    }
    for (int ps = 0; ps < nom; ps++) {
        rc = search(u0, K, om_a[ps], om_b[ps], wcap, rootmask, rootpat, t0);
        if (rc == 0) return 0;
    }
    if (nom == 0 || then_exact) rc = search(u0, K, 0, 0, cap, rootmask, rootpat, t0);
    return rc == 3 ? 3 : 0;
}
