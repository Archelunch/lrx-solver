#!/bin/sh
# Build the C oracle with the system compiler (no dependencies).  Builds to a temporary name and renames, so
# processes already running keep their binary.
cd "$(dirname "$0")" && cc -O3 -march=native -Wall -Wextra -o lrxfast.tmp lrxfast.c -lpthread && mv lrxfast.tmp lrxfast
