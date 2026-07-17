#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REDUCER (Hadoop Streaming) — cộng tổng theo key đã sort. Output: key<TAB>count."""
import sys

cur, total = None, 0
# Đọc luồng dữ liệu đầu vào đã được Hadoop tự động gom nhóm và sắp xếp (Sort & Shuffling) từ stdin
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    # Tách dòng thành cặp Khóa (key) và Giá trị (val)
    key, _, val = line.partition("\t")
    try:
        # Lấy giá trị đếm (luôn là 1 từ Mapper phát ra)
        c = int(val)
    except ValueError:
        continue
        
    # Logic cộng gộp:
    # Nếu gặp khóa mới (khác khóa đang lưu ở biến 'cur')
    if key != cur:
        # Nếu đây không phải khóa đầu tiên (đã có kết quả gom nhóm trước đó)
        if cur is not None:
            # Phát (Emit) kết quả cộng dồn cho khóa cũ ra stdout
            sys.stdout.write(f"{cur}\t{total}\n")
        # Reset biến cur sang khóa mới, và đặt lại bộ đếm total về 0
        cur, total = key, 0
    # Cộng dồn giá trị đếm vào tổng của khóa hiện tại
    total += c

# Đảm bảo in ra kết quả cho nhóm khóa cuối cùng sau khi kết thúc luồng dữ liệu
if cur is not None:
    sys.stdout.write(f"{cur}\t{total}\n")
