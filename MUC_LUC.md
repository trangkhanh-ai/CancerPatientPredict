# MỤC LỤC THƯ MỤC — d:\1BigDataproject1\final

Cập nhật: 2026-07-14. Cấu trúc sau khi dọn dẹp:

```
final/
├── cancer_bigdata/        ⭐ REPO CHÍNH — code CHẠY ĐƯỢC (sửa code thì sửa ở đây)
├── modules/               📖 BẢN SAO code chia theo 5 module, CÓ CHÚ THÍCH — để đọc/nộp/vấn đáp
├── tai_lieu_bao_cao/      📄 Báo cáo docx/pdf + tài liệu md + hinh_anh/ (không phải code)
├── luu_tru_file_goc/      🗄 File code rời ban đầu + zip + Excel gốc (đã có bản chính thức
│                             trong cancer_bigdata/ — giữ để đối chiếu, KHÔNG dùng để chạy)
│
│  ── các thư mục di sản từ những lần nộp trước (giữ nguyên, không đụng) ──
├── CancerUI/              Bản WinForms cũ (đã thay bằng cancer_bigdata/winforms)
├── final/                 Snapshot cũ (files/, files2/, zip, docx)
├── final+spark/           Snapshot cũ có train_spark.py
├── cleandata cancer/      Notebook + script làm sạch dữ liệu ban đầu
└── _run/                  Log/output của các lần chạy thử cũ
```

## Dùng nhanh

| Muốn làm gì | Vào đâu |
|---|---|
| Chạy hệ thống (MapReduce/Mongo/ML/API/WinForms) | `cancer_bigdata/` — làm theo `docs/RUNBOOK.md` |
| Đọc hiểu code theo module, có chú thích [QUAN TRỌNG] | `modules/` — bắt đầu từ `HUONG_DAN_DOC_CODE.md` |
| Xem báo cáo Word/PDF, hình kiến trúc | `tai_lieu_bao_cao/` |
| Tìm lại file gốc trước khi tổ chức repo | `luu_tru_file_goc/` |

## Trong cancer_bigdata/ (repo chính)

| Thư mục | Nội dung |
|---|---|
| `src/common` `src/hadoop` `src/mongodb` `src/ml` `src/api` | Code Python (chạy với `PYTHONPATH=src`) |
| `winforms/` | Solution C# WinForms (.NET 8) — `dotnet run --project CancerBigData` |
| `data/` `artifacts/` `models/` | Dữ liệu · output MapReduce/metrics · PipelineModel |
| `docs/` + `README.md` | ARCHITECTURE · API · RUNBOOK · ML_EVALUATION |

⚠ Nhắc lại: `modules/` là **bản sao để đọc** — sửa code trong đó không ảnh hưởng hệ thống.
Sửa thật thì sửa trong `cancer_bigdata/` rồi copy lại sang `modules/` nếu muốn đồng bộ.
