#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REDUCER (Hadoop Streaming) — cộng tổng theo key đã sort. Output: key<TAB>count."""
import sys

cur, total = None, 0
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    key, _, val = line.partition("\t")
    try:
        c = int(val)
    except ValueError:
        continue
    if key != cur:
        if cur is not None:
            sys.stdout.write(f"{cur}\t{total}\n")
        cur, total = key, 0
    total += c
if cur is not None:
    sys.stdout.write(f"{cur}\t{total}\n")
