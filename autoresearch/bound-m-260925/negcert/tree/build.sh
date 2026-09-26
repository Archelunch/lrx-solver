#!/bin/sh
cd "$(dirname "$0")" && cc -O3 -march=native -Wall -Wextra -o lrxtree.tmp lrxtree.c -lpthread && mv lrxtree.tmp lrxtree
