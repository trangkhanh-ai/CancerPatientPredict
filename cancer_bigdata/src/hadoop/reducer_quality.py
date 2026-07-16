#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDUCER — Module 1: Gom theo check_name, tính Σ đếm (MapReduce Streaming).

╔══════════════════════════════════════════════════════════════════════╗
║  MỤC ĐÍCH:                                                        ║
║  Nhận input đã SORT theo key từ mapper_quality.py,                 ║
║  gom các cặp (check_name, 1) cùng key lại và cộng dồn.            ║
║                                                                    ║
║  INPUT (từ stdout của mapper, qua sort):                           ║
║    invalid_age\t1                                                  ║
║    invalid_age\t1                                                  ║
║    rows_total\t1                                                   ║
║    rows_total\t1                                                   ║
║    ...                                                             ║
║                                                                    ║
║  OUTPUT FORMAT: check_name<TAB>count                               ║
║    rows_total\t1000                                                ║
║    (nếu có vi phạm: invalid_gender\tN, invalid_age\tN, ...)       ║
║                                                                    ║
║  THUẬT TOÁN:                                                       ║
║    - Đọc từng dòng, tách key và value bằng TAB                     ║
║    - Vì input đã sort → các dòng cùng key nằm liền nhau            ║
║    - Khi gặp key mới → in ra (key_cũ, tổng_cũ), reset bộ đếm     ║
║    - Kết thúc → in key cuối cùng                                   ║
║                                                                    ║
║  ĐÂY LÀ REDUCER KINH ĐIỂN (streaming word-count pattern):         ║
║    Read sorted stream → group by key → aggregate                   ║
║                                                                    ║
║  KHỚP SƠ ĐỒ: module1_JOB_kiem_dinh_chat_luong_TOPOLOGY.png       ║
║    R · Reduce đếm (Σ): Read() → Sort() gom theo check_name →      ║
║    reduce(): Σ 1 theo từng check → quality_report                  ║
║                                                                    ║
║  CHẠY CỤC BỘ:                                                     ║
║    cat cancer_patients_ml_ready.csv                                ║
║      | python mapper_quality.py | sort                             ║
║      | python reducer_quality.py > quality_report.tsv              ║
╚══════════════════════════════════════════════════════════════════════╝

Tác giả: Nhóm đồ án Big Data — HUFLIT
Ngày: 2026-07-15
"""
import sys


def main():
    """
    Reducer chính — đọc stream đã sort, gom theo key, cộng dồn value.
    
    Biến trạng thái:
      cur   = key hiện tại đang gom (None lúc bắt đầu)
      total = tổng đếm cho key hiện tại
    
    Khi key thay đổi (key != cur):
      → In ra dòng kết quả cho key trước: "cur<TAB>total"
      → Reset cur = key mới, total = 0
    
    Cuối stream: in dòng cuối cùng.
    
    Ví dụ output (dữ liệu sạch 1000/1000):
      rows_total	1000
    
    Nếu có vi phạm:
      invalid_gender	5
      invalid_risk_scale	12
      rows_total	1000
    """
    cur = None       # Key đang gom hiện tại
    total = 0        # Bộ đếm tổng cho key hiện tại

    for line in sys.stdin:
        # ── Bỏ newline, bỏ dòng trống ──
        line = line.rstrip("\n")
        if not line:
            continue

        # ── Tách key và value bằng TAB ──
        # Format: "check_name\t1"
        key, _, val = line.partition("\t")

        # ── Phát hiện key mới → in kết quả key cũ ──
        if key != cur:
            if cur is not None:
                sys.stdout.write(f"{cur}\t{total}\n")
            cur = key
            total = 0

        # ── Cộng dồn value ──
        total += int(val)

    # ── In key cuối cùng ──
    if cur is not None:
        sys.stdout.write(f"{cur}\t{total}\n")


if __name__ == "__main__":
    main()
