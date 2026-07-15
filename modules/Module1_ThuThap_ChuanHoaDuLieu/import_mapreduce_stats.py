# -*- coding: utf-8 -*-
"""
Nạp kết quả phân bố từ MapReduce (artifacts/distributions.tsv) vào collection stats_mapreduce.
Mỗi lần chạy tạo 1 document snapshot có created_at (để /stats lấy mapreduce_run_at mới nhất).
Chạy: python -m src.mongodb.import_mapreduce_stats --input artifacts/distributions.tsv
"""
import sys, os, argparse, datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mongodb.client import get_db  # noqa: E402


def parse_tsv(path: str) -> dict:
    dist = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            key, _, val = line.partition("\t")
            try:
                dist[key] = int(val)
            except ValueError:
                continue
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    dist = parse_tsv(args.input)
    now = datetime.datetime.utcnow()
    # tách vài nhóm hay dùng cho tiện tra cứu
    level = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("level|")}
    gender = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("gender|")}
    age_group = {k.split("|", 1)[1]: v for k, v in dist.items() if k.startswith("age_group|")}

    doc = {"created_at": now, "source": "hadoop_streaming", "n_keys": len(dist),
           "level_distribution": level, "gender_distribution": gender,
           "age_group_distribution": age_group, "distributions": dist}
    db = get_db()
    db.stats_mapreduce.insert_one(doc)
    print(f"[OK] stats_mapreduce +1 doc | keys={len(dist)} level={level} at {now.isoformat()}")


if __name__ == "__main__":
    main()
