#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDUCER (Hadoop Streaming) — Module 2 · JOB 1: Cộng tổng theo key đã sort.

Nhận input đã SORT từ mapper_distribution.py.
Gom các cặp (key, 1) cùng key → cộng dồn → output: key<TAB>count.

Đây là reducer kinh điển (word-count pattern):
  Read sorted stream → group by key → Σ count

KHỚP SƠ ĐỒ: module2_JOB1_dem_phan_bo_TOPOLOGY.png
  R · Reduce đếm (Σ): Read() → Sort() gom theo key → reduce(): Σ → distributions.tsv

OUTPUT MẪU:
  level|High\t365
  level|Low\t303
  level|Medium\t332
  gender|1\t598
  gender|2\t402
  age_group|30-39\t358
  ...
  → Tổng 199 dòng (khớp distributions.tsv thật)
"""
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
