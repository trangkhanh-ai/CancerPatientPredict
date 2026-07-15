#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDUCER — Tương quan yếu tố nguy cơ (Module 2).
Nhận input đã sort theo key. Output TSV:
  MEAN   <indicator>  <level>  <trung bình>  <n>
  XTAB   <indicator>  <bucket> <level>  <count>
  N      <level>      <count>
Sau đó (ở bước import/API) tính RANK = mean(High) - mean(Low) để xếp hạng mức ảnh hưởng.
"""
import sys


def flush(key, vals):
    if key is None:
        return
    parts = key.split("|")
    kind = parts[0]
    if kind == "mean":
        ind, lv = parts[1], parts[2]
        nums = [float(v) for v in vals]
        n = len(nums)
        avg = sum(nums) / n if n else 0.0
        sys.stdout.write(f"MEAN\t{ind}\t{lv}\t{avg:.2f}\t{n}\n")
    elif kind == "xtab":
        ind, bk, lv = parts[1], parts[2], parts[3]
        total = sum(int(v) for v in vals)
        sys.stdout.write(f"XTAB\t{ind}\t{bk}\t{lv}\t{total}\n")
    elif kind == "n":
        sys.stdout.write(f"N\t{parts[1]}\t{sum(int(v) for v in vals)}\n")


def main():
    cur, buff = None, []
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        key, _, val = line.partition("\t")
        if key != cur:
            flush(cur, buff)
            cur, buff = key, []
        buff.append(val)
    flush(cur, buff)


if __name__ == "__main__":
    main()
