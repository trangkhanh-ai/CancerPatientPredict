# 🔧 TÁI CẤU TRÚC MODULE — Bỏ tìm kiếm khỏi Module 2 & Xử lý Random Forest

> Hai thay đổi giúp đồ án **gọn hơn, dễ giải thích hơn**, mà **không mất code nào**.
> (Biên bản quyết định của nhóm — đã áp dụng vào tài liệu repo ngày 2026-07-14.)

---

# PHẦN A — BỎ TÌM KIẾM/LỌC RA KHỎI MODULE 2

## A.1. Vì sao phải bỏ?

Module 2 hiện đang nhét **3 thứ khác concept** vào một chỗ:

| Phần | Bản chất | Concept |
|---|---|---|
| 2.1 Đếm phân bố | Gom khoá → tổng hợp | ✅ **MapReduce** |
| 2.2 Tương quan | Gom khoá → tổng hợp | ✅ **MapReduce** |
| 2.3 Tìm kiếm/lọc | Lọc dòng → trả về | ❌ **KHÔNG phải MapReduce** |

→ Trộn 2 concept vào một module nên **nhìn không hợp**, và khi thuyết trình phải giải thích
lòng vòng *"cái này là MapReduce, cái kia thì không"*.

## A.2. Chuyển đi đâu? → **MODULE 5**

**Lý do hợp lý (nói được với thầy):**
> *"Tìm kiếm/lọc là **tính năng của người dùng cuối** — người dùng chọn bộ lọc trên giao diện,
> hệ thống trả về danh sách. Nó thuộc tầng ứng dụng, không phải tầng phân tích dữ liệu lớn.
> Endpoint `/patients` thì Module 4 (Dịch vụ) đã sở hữu rồi."*

### Cấu trúc SAU khi sửa

| Module | Tên | Nội dung | Concept |
|---|---|---|---|
| 1 | Thu thập & Chuẩn hoá dữ liệu | Làm sạch + đếm vi phạm | ✅ MapReduce |
| **2** | **Phân tích Dữ liệu** *(bỏ chữ "Khai phá")* | **2.1 Đếm phân bố** · **2.2 Tương quan yếu tố nguy cơ** | ✅ **MapReduce — DUY NHẤT 1 CONCEPT** |
| 3 | Huấn luyện & Đánh giá mô hình | Group-aware split → Logistic Regression | ❌ ML Pipeline |
| 4 | Dịch vụ Dự đoán | FastAPI — 11 endpoint | ❌ Serving |
| **5** | **Ứng dụng Người dùng** | Dự đoán · **Tìm kiếm & lọc bệnh nhân** · Thống kê · Yếu tố nguy cơ · Chất lượng | ❌ UI |

> ✅ **Module 2 giờ chỉ còn MapReduce — sạch, dễ vẽ, dễ nói.**
> ✅ **Module 2 vẫn "nặng ký"** vì còn nguyên 2 job MapReduce, không bị rỗng.

## A.3. 2.1 và 2.2 khác nhau chỗ nào? (câu thầy hay vặn)

Sau khi bỏ 2.3, hai job còn lại **cùng khung MapReduce**, chỉ khác **giá trị mà mapper phát ra**:

| | Mapper phát ra | Reducer làm gì | Kết quả |
|---|---|---|---|
| **2.1 Phân bố** | `(key, **1**)` | **Cộng dồn** | `level\|High = 365` |
| **2.2 Tương quan** | `(key, **giá trị chỉ số**)` | **Tính trung bình** (Σ/n) | `mean(smoking, High) = 6.07` |

**Câu trả lời 1 dòng:**
> *"Hai job cùng khung MapReduce. Khác duy nhất: job phân bố phát value = **1** để **đếm**;
> job tương quan phát value = **giá trị thật của chỉ số** để **tính trung bình**."*

→ Đây còn là **điểm cộng**: cho thấy bạn hiểu MapReduce linh hoạt, không chỉ biết đếm.

## A.4. ⚠ CODE KHÔNG PHẢI SỬA GÌ CẢ

Đây chỉ là **thay đổi cách TRÌNH BÀY**, không phải refactor code:

| Thứ | Có sửa không? |
|---|---|
| `query_builder.py` | ❌ Giữ nguyên |
| Endpoint `GET /patients` | ❌ Giữ nguyên (vẫn thuộc Module 4) |
| `PatientSearchControl.cs` | ❌ Giữ nguyên |
| **Báo cáo / sơ đồ / thuyết trình** | ✅ **Chỉ sửa chỗ này** |

**Việc cần làm:**
1. Trong báo cáo: **xoá mục 2.3** khỏi Module 2 → **thêm vào Module 5** thành mục *"5.2 Tìm kiếm & lọc bệnh nhân"*
2. Vẽ lại **sơ đồ Module 2**: bỏ khối 2.3 (chỉ còn 2 job MapReduce)
3. Vẽ lại **sơ đồ Module 5**: thêm chi tiết luồng tìm kiếm
4. Sửa bảng "5 module" trong báo cáo theo mục A.2

## A.5. Mục 5.2 trong báo cáo — viết sẵn

> **5.2 Tìm kiếm & lọc bệnh nhân**
>
> Đáp ứng yêu cầu đề bài *"thống kê và tìm kiếm được các bệnh nhân dựa trên bộ lọc là từng chỉ số"*.
>
> Người dùng chọn bộ lọc trên giao diện: mức độ (Low/Medium/High), giới tính, khoảng tuổi, và
> **từng chỉ số cụ thể** với các toán tử `=`, `≥`, `≤`, `trong khoảng`. Ứng dụng gửi yêu cầu tới
> `GET /api/v1/patients`; phía máy chủ đối chiếu tham số với **danh sách cho phép (whitelist)** —
> chỉ 21 chỉ số hợp lệ và 4 toán tử hợp lệ được chấp nhận, sai thì trả mã **422** và **không bao giờ
> chạm tới truy vấn MongoDB** (chống tấn công tiêm mã). Truy vấn hợp lệ được đưa vào
> `db.patients.find()` với sắp xếp và phân trang, kết quả trả về dưới dạng bảng; người dùng có thể
> nhấn đúp để xem chi tiết hoặc **xuất CSV** theo đúng bộ lọc hiện tại.
>
> Khâu này **không dùng MapReduce**: tìm kiếm chỉ **lọc một số bản ghi rồi trả về**, không có bước
> gom-theo-khoá-rồi-tổng-hợp. MongoDB đã có chỉ mục (index) nên truy vấn trực tiếp là nhanh và
> phù hợp nhất với bài toán này.

---

# PHẦN B — XỬ LÝ RANDOM FOREST

## B.1. Chốt: **chỉ báo cáo Logistic Regression**, nhưng KHÔNG xoá RF khỏi code

| Cách | Kết quả |
|---|---|
| ❌ **Xoá hẳn RF** | Mất luôn lập luận đối chứng → khi thầy hỏi *"sao biết không phải do chọn nhầm thuật toán?"* thì bí |
| ✅ **Giữ code, hạ cấp xuống 1 dòng ghi chú** | Không phải trình bày gì thêm · vẫn có lá chắn khi bị hỏi |

**Chi phí giữ RF = 0** (code đã chạy, đã có số). Chỉ là **đừng cho nó một mục riêng**.

## B.2. Cách "hạ cấp" — sửa 3 chỗ trong báo cáo

### ① Bảng 5 module — bỏ chữ "RF"
```diff
- Module 3 | Huấn luyện mô hình phân lớp mức độ (LR, đối chứng RF) | PySpark ML
+ Module 3 | Huấn luyện mô hình phân lớp mức độ nghiêm trọng       | PySpark ML (Logistic Regression)
```

### ② Bảng kết quả — chỉ để 1 dòng LR
```diff
  | Mô hình                    | Accuracy | Macro-F1 |
- | Logistic Regression (chọn) | 1.0000   | 1.0000   |
- | Random Forest (đối chứng)  | 1.0000   | 1.0000   |
+ | Logistic Regression        | 1.0000   | 1.0000   |
```

### ③ Thêm **ĐÚNG MỘT CÂU** ghi chú dưới bảng (lá chắn)

> *"Ghi chú: nhóm có chạy thêm một mô hình đối chứng (Random Forest) để kiểm chứng nội bộ và thu được
> kết quả tương đương, khẳng định điểm số cao đến từ **đặc tính tách hoàn toàn của dữ liệu**
> chứ không phải do lựa chọn thuật toán. Báo cáo này chỉ trình bày chi tiết Logistic Regression."*

## B.3. Nếu thầy hỏi *"Sao chỉ có 1 mô hình?"*

> *"Đề tài tập trung vào Logistic Regression vì nó cho **xác suất từng lớp** — dễ giải thích cho
> người dùng cuối. Trong quá trình làm, nhóm em **có chạy thêm Random Forest để kiểm chứng nội bộ**
> và thấy kết quả tương đương (cùng đạt 1.00), điều này **khẳng định điểm số cao đến từ đặc tính
> của dữ liệu** — nhãn gần như là hàm xác định của 23 chỉ số — **chứ không phải do em chọn nhầm
> thuật toán**. Vì kết luận giống nhau nên báo cáo chỉ trình bày chi tiết một mô hình cho gọn."*

## B.4. Code — sửa gì?

| File | Sửa? |
|---|---|
| `src/ml/train.py` | ❌ **Giữ nguyên** (vẫn train cả LR và RF) |
| `ml_analysis.py` | ❌ **Giữ nguyên** |
| `artifacts/metrics/metrics.json` | ❌ **Giữ nguyên** (có số RF để phòng khi cần) |
| **Báo cáo Word** | ✅ Sửa 3 chỗ ở mục B.2 |
| **Sơ đồ Module 3** | ✅ Bỏ nhánh RF (chỉ vẽ nhánh LR) |

---

# PHẦN C — CHECKLIST THỰC HIỆN (kèm trạng thái)

## Tài liệu trong repo — ✅ ĐÃ LÀM XONG (2026-07-14)
- [x] `modules/` đổi tên thư mục → `Module2_PhanTichDuLieu`
- [x] `modules/README.md` · `HUONG_DAN_DOC_CODE.md` · `GIAI_DAP_CAU_HOI_NHOM.md` cập nhật theo cấu trúc mới
- [x] `cancer_bigdata/README.md` + `docs/ARCHITECTURE.md`: Module 2 = "Phân tích Dữ liệu — 2 job MapReduce"; Module 3 = "PySpark ML (Logistic Regression)"
- [x] `docs/ML_EVALUATION.md`: thêm ghi chú B.2③ (giữ bảng số cả 2 model làm bằng chứng)
- [x] Code: không sửa gì ✓

## Báo cáo Word — CÒN LẠI (nhóm tự sửa trong tai_lieu_bao_cao/)
- [ ] Bảng 5 module: đổi tên Module 2 → **"Phân tích Dữ liệu"**; bỏ "(LR, đối chứng RF)" ở Module 3
- [ ] Module 2: **xoá mục 2.3** (tìm kiếm) — chỉ còn 2.1 phân bố + 2.2 tương quan
- [ ] Module 5: **thêm mục 5.2 Tìm kiếm & lọc** (đoạn văn viết sẵn ở A.5)
- [ ] Bảng kết quả: **bỏ dòng Random Forest** + thêm **1 câu ghi chú** (B.2③)

## Sơ đồ draw.io — CÒN LẠI
- [ ] **Module 2**: chỉ còn 2 job MapReduce (bỏ khối 2.3); Shuffle/Sort là hộp riêng giữa Map và Reduce
- [ ] **Module 3**: chỉ còn nhánh Logistic Regression (bỏ nhánh RF)
- [ ] **Module 5**: thêm chi tiết luồng tìm kiếm/lọc (mục 5.2)

## Thuộc lòng
- [ ] 2.1 vs 2.2: *"job phân bố phát value = 1 để đếm; job tương quan phát value = giá trị thật để tính trung bình"*
- [ ] Câu về RF (mục B.3) — khi bị hỏi *"sao chỉ 1 mô hình?"*
- [ ] Câu về tìm kiếm: *"tìm kiếm chỉ lọc rồi trả về, không có bước tổng hợp, nên không dùng MapReduce"*

---

# TÓM TẮT — 3 CÂU

1. **Module 2** giờ chỉ còn **2 job MapReduce** (đếm phân bố + tương quan) → **một concept duy nhất, sạch sẽ**.
2. **Tìm kiếm/lọc** chuyển sang **Module 5** vì nó là **tính năng người dùng**, không phải phân tích dữ liệu lớn.
3. **Random Forest** vẫn nằm trong code nhưng **hạ xuống một dòng ghi chú** — không phải báo cáo, mà vẫn là **lá chắn** khi thầy hỏi *"sao biết không phải do chọn nhầm thuật toán?"*
