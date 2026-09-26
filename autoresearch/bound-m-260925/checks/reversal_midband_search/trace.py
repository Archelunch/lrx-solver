import sys
from mb import *
def trace(st, w):
    """physical cells, cursor; print cells after each maximal rotation+X block"""
    a=list(st); n=len(a); c=0
    names=lambda a: ' '.join('.' if x==0 else str(x) for x in a)
    print('     ', names(a))
    seg=''
    for ch in w:
        seg+=ch
        if ch=='L': c=(c+1)%n
        elif ch=='R': c=(c-1)%n
        else:
            j=(c+1)%n; x,y=a[c],a[j]; a[c],a[j]=y,x
            print('%-10s c=%2d swap %s<->%s  %s' % (seg, c, x or '.', y or '.', names(a)))
            seg=''
    print('%-10s end c=%d' % (seg, c))
if __name__=='__main__':
    m,g=int(sys.argv[1]),int(sys.argv[2]); o=(int(sys.argv[3]),int(sys.argv[4])) if len(sys.argv)>4 else (1,1)
    trace(state_0g(m,g,o), sys.argv[-1])
