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
    """
    Thực hiện gom nhóm và tính toán kết quả cuối cùng cho mỗi khóa sau khi đã nhận đủ dữ liệu.
    """
    if key is None:
        return
    parts = key.split("|")
    kind = parts[0]
    
    # 1. Nếu khóa dạng 'mean': Tính giá trị trung bình cộng phân tán của chỉ số
    if kind == "mean":
        ind, lv = parts[1], parts[2]
        nums = [float(v) for v in vals]
        n = len(nums)
        # Tính trung bình cộng = Tổng giá trị / Số lượng bản ghi
        avg = sum(nums) / n if n else 0.0
        # Xuất kết quả định dạng: MEAN <tên_chỉ_số> <mức_độ_bệnh> <trung_bình> <số_lượng>
        sys.stdout.write(f"MEAN\t{ind}\t{lv}\t{avg:.2f}\t{n}\n")
        
    # 2. Nếu khóa dạng 'xtab': Tính tổng số bệnh nhân cho bảng chéo (cross-tab)
    elif kind == "xtab":
        ind, bk, lv = parts[1], parts[2], parts[3]
        total = sum(int(v) for v in vals)
        # Xuất kết quả định dạng: XTAB <tên_chỉ_số> <mức_độ_chỉ_số> <mức_độ_bệnh> <tổng_số>
        sys.stdout.write(f"XTAB\t{ind}\t{bk}\t{lv}\t{total}\n")
        
    # 3. Nếu khóa dạng 'n': Thống kê tổng số bệnh nhân theo mức độ nguy cơ
    elif kind == "n":
        sys.stdout.write(f"N\t{parts[1]}\t{sum(int(v) for v in vals)}\n")


def main():
    cur, buff = None, []
    # Đọc luồng dữ liệu đã sắp xếp khóa từ stdin (do Hadoop truyền vào)
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        key, _, val = line.partition("\t")
        
        # Nếu chuyển sang một khóa mới (khác khóa 'cur' đang lưu)
        if key != cur:
            # Thực thi hàm flush() để tính toán và xuất dữ liệu cho khóa cũ
            flush(cur, buff)
            # Chuyển sang khóa mới và làm rỗng bộ nhớ đệm buffer
            cur, buff = key, []
        # Lưu trữ tạm thời các giá trị (values) của khóa hiện tại vào bộ nhớ đệm
        buff.append(val)
        
    # Đảm bảo flush nốt nhóm khóa cuối cùng khi kết thúc luồng stdin
    flush(cur, buff)


if __name__ == "__main__":
    main()
