#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDUCER — Module 2 · JOB 2: Tương quan yếu tố nguy cơ (MapReduce).

Nhận input đã sort theo key từ mapper_correlation.py. Output TSV 3 loại:
  MEAN   <indicator>  <level>  <trung bình>  <n>   → trung bình chỉ số theo mức độ
  XTAB   <indicator>  <bucket> <level>  <count>    → bảng chéo thấp/TB/cao × Low/Med/High
  N      <level>      <count>                      → tổng số bệnh nhân từng mức độ

KHÁC JOB 1: Reducer này KHÔNG chỉ đếm mà còn TÍNH TRUNG BÌNH (Σ giá trị / n).
  - key "mean|..." → gom giá trị thực, tính mean
  - key "xtab|..." → cộng dồn (đếm)
  - key "n|..."    → cộng dồn (đếm)

Sau bước reduce, API tính: impact = mean(High) - mean(Low) để xếp hạng.

KHỚP SƠ ĐỒ: module2_JOB2_tuong_quan_TOPOLOGY.png
  R · Reduce mean/count: MEAN = Σ giá trị / n · XTAB = Σ đếm
  → impact = mean(High) - mean(Low) → xếp hạng nguy cơ

KẾT QUẢ THẬT (khớp Tab Yếu tố nguy cơ):
  MEAN  alcohol_use  High  6.83  365   →   impact = 6.83 - 2.23 = +4.60 (hạng 1)
  MEAN  alcohol_use  Low   2.23  303
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
