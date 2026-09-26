#!/bin/sh
cd "$(dirname "$0")" && cc -O3 -march=native -Wall -Wextra -o lrxtree_wide.tmp lrxtree_wide.c -lpthread && mv lrxtree_wide.tmp lrxtree_wide
