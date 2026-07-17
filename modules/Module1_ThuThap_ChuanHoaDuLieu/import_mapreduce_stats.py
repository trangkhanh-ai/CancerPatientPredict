# -*- coding: utf-8 -*-
"""
Nạp kết quả phân bố từ MapReduce (artifacts/distributions.tsv) vào collection stats_mapreduce.
Mỗi lần chạy tạo 1 document snapshot có created_at (để /stats lấy mapreduce_run_at mới nhất).

⚠️ [QUAN TRỌNG - PHỤC VỤ VẤN ĐÁP]:
- Tệp này KHÔNG PHẢI là hàm Map (Mapper) hay Reduce (Reducer) của Hadoop.
- Đây chỉ là tệp tiện ích Python (Utility Script) dùng để đọc tệp kết quả TSV cuối cùng
  sau khi chạy Hadoop MapReduce xong, rồi lưu thông tin đó vào MongoDB để API/WinForms hiển thị.
  
Chạy: python -m src.mongodb.import_mapreduce_stats --input artifacts/distributions.tsv
"""
import sys, os, argparse, datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mongodb.client import get_db  # noqa: E402


def parse_tsv(path: str) -> dict:
    """Đọc tệp kết quả TSV từ MapReduce và chuyển đổi thành một từ điển Python."""
    dist = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            # Chia dòng theo ký tự Tab (\t) thành: khóa (key) và giá trị (val)
            key, _, val = line.partition("\t")
            try:
                # Lưu khóa và ép kiểu giá trị đếm sang số nguyên
                dist[key] = int(val)
            except ValueError:
                continue
    return dist


def main():
    # Khởi tạo bộ phân tích tham số dòng lệnh CLI
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    # Bước 1: Đọc và phân tích tệp TSV
    dist = parse_tsv(args.input)
    now = datetime.datetime.utcnow()
    
    # Bước 2: Tách nhỏ kết quả phân bố thành các nhóm nhỏ (level, giới tính, nhóm tuổi) để tiện truy vấn
    # Lấy phân bố mức độ (level): Lọc các khóa bắt đầu bằng 'level|'
    level = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("level|")}
    # Lấy phân bố giới tính (gender): Lọc các khóa bắt đầu bằng 'gender|'
    gender = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("gender|")}
    # Lấy phân bố nhóm tuổi (age_group): Lọc các khóa bắt đầu bằng 'age_group|'
    age_group = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("age_group|")}

    # Bước 3: Đóng gói thành một JSON Document hoàn chỉnh chứa thông tin thống kê phân phối
    doc = {"created_at": now, "source": "hadoop_streaming", "n_keys": len(dist),
           "level_distribution": level, "gender_distribution": gender,
           "age_group_distribution": age_group, "distributions": dist}
           
    # Bước 4: Kết nối MongoDB và đẩy bản ghi này vào collection stats_mapreduce
    db = get_db()
    db.stats_mapreduce.insert_one(doc)
    print(f"[OK] stats_mapreduce +1 doc | keys={len(dist)} level={level} at {now.isoformat()}")


if __name__ == "__main__":
    main()
