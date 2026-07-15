# GIẢI ĐÁP CÂU HỎI NHÓM — theo từng Module (dùng khi vẽ draw.io + vấn đáp)

> Trả lời các thắc mắc khi vẽ sơ đồ và ôn bài. Mỗi mục có ví dụ cụ thể lấy từ code thật.

---

## MODULE 1 — Thu thập & Chuẩn hoá dữ liệu

### 1.1. Có cần bản vẽ riêng cho Module 1 không?

**Nên giữ**, vì Module 1 là bước "Excel → CSV sạch → MongoDB" — không có nó thì sơ đồ
tổng thiếu điểm xuất phát. Vẽ gọn 1 hàng ngang là đủ:

```
Excel gốc (25 cột, RAW-case)
   → [MAP] làm sạch từng dòng (đổi tên cột, ép kiểu, kiểm miền giá trị)
   → [R2] đếm vi phạm theo check_name
   → CSV sạch (snake_case) → import_patients.py → MongoDB (collection patients)
```

### 1.2. `map()` của Module 1: key–value là gì?

Làm sạch bản chất là **map-only** (mỗi dòng độc lập, không cần gom nhóm):

| | Key | Value |
|---|---|---|
| **Input của map** | offset dòng trong file (Hadoop tự cấp, mình không dùng) | 1 dòng CSV thô, ví dụ: `P100,44,1,6,7,...,High` |
| **Output nhánh dữ liệu sạch** | `patient_id` (ví dụ `P100`) | dòng đã chuẩn hoá snake_case |
| **Output nhánh vi phạm** (đi vào R2) | `check_name` (tên phép kiểm) | `1` (đếm 1 vi phạm) |

Ví dụ output nhánh vi phạm nếu gặp dòng lỗi:

```
invalid_age	1
invalid_risk_scale	1
```

Với dataset này: **0 vi phạm** → mọi counter đều 0, giữ 1000/1000 dòng (số liệu thật trong báo cáo).

### 1.3. "Cast double" là sao?

Giá trị đọc từ Excel/CSV luôn là **chuỗi (string)**: `"44"`, `"7"`, có khi là `"7.0"`.
Muốn kiểm tra miền giá trị (tuổi 0–120, chỉ số 1–9) thì phải **ép sang kiểu số** trước —
đó là "cast":

```python
v = int(float(raw))    # "7"  → 7.0 → 7   ·   "7.0" → 7.0 → 7
```

Đi qua `float` trước rồi mới `int` để cả `"7"` lẫn `"7.0"` đều ra `7`.
(Trong Spark thì `inferSchema` tự đoán cột số thành double — cùng một ý.)
Nếu cast thất bại (chuỗi rác như `"abc"`) → dòng đó bị tính là vi phạm → phát key cho R2.

### 1.4. R2 nhận (read) cái gì? Trông như thế nào?

R2 là reducer **đếm số vi phạm theo `check_name`**. Sau pha shuffle/sort, nó đọc từ stdin
các dòng `key<TAB>1` **đã được gom cạnh nhau theo key**:

```
# INPUT của R2 (đã sort):          # OUTPUT của R2:
duplicate_patient_id	1
duplicate_patient_id	1           duplicate_patient_id	2
invalid_age	1                     invalid_age	3
invalid_age	1                     invalid_risk_scale	1
invalid_age	1
invalid_risk_scale	1
```

Logic chỉ có một: *key giống dòng trước thì cộng dồn, key đổi thì in tổng ra rồi đếm lại* —
y hệt `reducer_distribution.py`. Kết quả cuối cùng đổ vào collection `data_quality`
và hiển thị ở tab "Chất lượng dữ liệu".

---

## MODULE 2 — Phân tích Dữ liệu *(tên mới — đã bỏ "Khai phá", đã chuyển Tìm kiếm sang Module 5)*

### 2.1. Vẽ 1 sơ đồ hay 2?

Đồng ý **vẽ 1 sơ đồ, tách 2 nhánh (2 MapReduce job)** — vì cả hai cùng input, cùng khuôn
Map → Shuffle/Sort → Reduce, chỉ khác loại key:

```
                        CSV sạch (1000 dòng)
                        ┌────────┴────────┐
              JOB 1: PHÂN BỐ          JOB 2: TƯƠNG QUAN
   [MAP]  phát (key, 1):            [MAP]  phát 2 loại:
     level|High                       mean|obesity|High → 7        (giá trị chỉ số)
     gender|1                         xtab|obesity|cao|High → 1    (đếm bảng chéo)
     age_group|30-39
     indicator|obesity|7
   [SHUFFLE/SORT] gom theo key      [SHUFFLE/SORT] gom theo key
   [REDUCE] cộng dồn                [REDUCE] mean = tổng/n · xtab = cộng dồn
     level|High → 365                 MEAN obesity High 6.68
   → distributions.tsv              → correlation.tsv → impact = mean(High) − mean(Low)
```

### 2.2. Map phase / Reduce phase "chỉnh giống Module 1", shuffle nằm ở đâu?

Khuôn 3 pha vẽ **thống nhất cho mọi job** — nhưng lưu ý một chỗ dễ bị giám khảo bắt:

- **Shuffle/Sort KHÔNG nằm bên trong Reduce** — nó là pha đứng giữa, do framework
  (Hadoop) thực hiện: gom mọi cặp cùng key về một reducer và sắp thứ tự.
  Trong lệnh demo của mình, chính lệnh `sort` đóng vai này:
  `cat csv | mapper.py | sort | reducer.py` — vẽ `sort` thành hộp riêng giữa Map và Reduce.
- Reducer sau đó chỉ việc đọc tuần tự: key đổi = nhóm mới. Nếu vẽ shuffle nằm trong
  reduce thì sai bản chất Hadoop (reducer không tự gom key được).

### 2.3. "Tìm kiếm & lọc" — QUYẾT ĐỊNH MỚI: chuyển sang Module 5 (mục 5.2)

Đây là **yêu cầu số 4 của đề bài**: *"thống kê và tìm kiếm bệnh nhân theo bộ lọc từng chỉ số"*.
Nó **không phải MapReduce** (chỉ lọc dòng rồi trả về, không có bước gom-khoá-tổng-hợp) nên
nhóm đã quyết định **đưa ra khỏi Module 2** để Module 2 thuần một concept MapReduce.
Vị trí mới: **Module 5 — mục 5.2** (tính năng người dùng cuối); endpoint `GET /patients`
vẫn thuộc sở hữu Module 4. **Code không sửa gì** — chỉ đổi cách trình bày/sơ đồ.
Luồng chạy để giải thích:

```
Người dùng chọn bộ lọc trên WinForms (mức độ = High, obesity ≥ 7, tuổi 30–50...)
  → GET /api/v1/patients?level=High&feature=obesity&operator=gte&value=7
  → query_builder.py ĐỐI CHIẾU WHITELIST (21 chỉ số · eq/gte/lte/between; sai → 422)
  → db.patients.find({level:"High", obesity:{$gte:7}}).sort().skip().limit()
  → trả JSON phân trang → hiển thị bảng + nút Xuất CSV
```

Câu thuộc lòng khi bị hỏi vì sao không dùng MapReduce cho tìm kiếm:
> *"Tìm kiếm chỉ **lọc một số bản ghi rồi trả về**, không có bước gom-theo-khoá-rồi-tổng-hợp;
> MongoDB đã có index nên truy vấn trực tiếp là nhanh và phù hợp nhất."*

---

## MODULE 3 — Huấn luyện & Đánh giá mô hình

### 3.1. Module 3 không theo MapReduce — đúng

Đúng vậy, Module 3 dùng **Spark MLlib** (DataFrame + Pipeline), không phải khuôn
map/reduce thủ công. Vẽ theo pipeline:

```
CSV sạch → feature_signature → group-aware split (697 train / 303 test, overlap=0)
        → VectorAssembler → StandardScaler → LogisticRegression → đánh giá 1 lần trên test
        → PipelineModel (lưu vào models/current/ cho Module 4 dùng)
```

### 3.2. Random Forest — QUYẾT ĐỊNH MỚI: "hạ cấp" xuống 1 câu ghi chú (không xoá)

Chốt của nhóm: **báo cáo và sơ đồ chỉ trình bày Logistic Regression**; RF giữ nguyên
trong code/metrics nhưng chỉ xuất hiện đúng **một câu ghi chú** dưới bảng kết quả:

> *"Ghi chú: nhóm có chạy thêm một mô hình đối chứng (Random Forest) để kiểm chứng nội bộ
> và thu được kết quả tương đương, khẳng định điểm số cao đến từ đặc tính tách hoàn toàn
> của dữ liệu chứ không phải do lựa chọn thuật toán. Báo cáo này chỉ trình bày chi tiết
> Logistic Regression."*

Phân công rõ:
- **Sơ đồ Module 3**: chỉ vẽ nhánh LR (bỏ hộp RF).
- **Báo cáo Word**: bảng kết quả 1 dòng LR + câu ghi chú trên; bảng 5 module ghi
  "PySpark ML (Logistic Regression)".
- **Code (`train.py`, `ml_analysis.py`, `metrics.json`)**: GIỮ NGUYÊN — số RF là "lá chắn"
  khi bị hỏi *"sao biết không phải do chọn nhầm thuật toán?"*.

Câu trả lời khi thầy hỏi "sao chỉ 1 mô hình?": LR cho **xác suất từng lớp** nên dễ giải
thích cho người dùng; nhóm có chạy thêm RF đối chứng nội bộ, kết quả tương đương (cùng 1.00)
→ điểm cao đến từ đặc tính dữ liệu (separable), không phải do chọn thuật toán → báo cáo
trình bày một mô hình cho gọn.

### 3.3. `feature_signature` là sao?

Là **"chứng minh thư" của một cấu hình bệnh nhân**: lấy đúng 23 chỉ số theo đúng thứ tự,
nối bằng `|`, băm SHA-256:

```
age|gender|air_pollution|...|snoring
"44|1|6|7|7|7|6|6|7|7|7|7|7|8|5|3|2|7|8|2|4|5|3"  --SHA-256-->  "eb532c41...  (64 ký tự hex)"
```

Hai bệnh nhân có **cùng 23 chỉ số → cùng signature** (dù khác `patient_id`).
Nó dùng để làm 2 việc quan trọng nhất đồ án:

1. **Phát hiện trùng**: 1000 dòng nhưng chỉ **152 signature duy nhất** → 848 dòng trùng vector.
2. **Group-aware split**: chia train/test theo **nhóm signature** chứ không theo dòng —
   nếu chia theo dòng, cùng một cấu hình rơi vào cả train lẫn test = mô hình "học thuộc"
   chứ không "học hiểu" (leakage). Sau khi chia, `assert overlap == 0`.

Một câu chốt để vấn đáp: *"signature trả lời câu hỏi: hai dòng này có phải CÙNG MỘT
trường hợp lâm sàng không — nếu phải thì chúng buộc phải ở cùng một phía train hoặc test."*

---

## MODULE 4 — Dịch vụ Dự đoán (FastAPI) — giải thích lại từ đầu

**Nó là gì:** cái "cổng" duy nhất đứng giữa mọi thứ backend (MongoDB, Spark model) và
người dùng (WinForms). WinForms không bao giờ chạm trực tiếp Mongo hay Spark — chỉ gọi HTTP.

**Vì sao cần nó:** (1) WinForms là C#, Spark/Mongo là Python — cần 1 giao diện chung là
HTTP/JSON; (2) gom mọi kiểm tra an toàn (validate, whitelist) về một chỗ; (3) sau này thay
WinForms bằng web/mobile thì backend giữ nguyên.

**Cách hoạt động — 3 ý chính:**

1. **Khởi động (lifespan):** nạp SparkSession + PipelineModel **đúng 1 lần** khi server bật
   (mất ~20s). Nhờ vậy mỗi request /predict chỉ việc transform, không nạp lại model.
   Chạy **1 worker** duy nhất (nhiều worker = nhiều SparkSession = ngốn RAM).
2. **11 endpoint, prefix `/api/v1`** — chia 3 nhóm:
   - Trạng thái: `/health` (API/Mongo/model sống không), `/model` (thông tin model)
   - Dự đoán: `POST /predict` (23 chỉ số → mức độ + xác suất), `/predictions` (lịch sử)
   - Khai thác dữ liệu: `/patients` + `/patients/export` (tìm kiếm/lọc/CSV),
     `/stats`, `/quality`, `/correlation` (phục vụ 4 tab còn lại)
3. **Phòng thủ:** Pydantic `extra="forbid"` + kiểm miền giá trị → sai là **422**;
   whitelist bộ lọc trong query_builder → chuỗi lạ không lọt vào Mongo; model chưa nạp
   → **503**; lỗi bất ngờ → **500** nhưng không lộ stack trace; route `/patients/export`
   khai báo trước `/patients/{id}` để không bị nuốt.

Vẽ draw.io: 1 hộp to "FastAPI :8000" — bên trái nhận HTTP từ WinForms, bên phải 2 mũi tên
xuống MongoDB (dữ liệu) và PipelineModel (dự đoán), bên trong ghi 3 gạch đầu dòng:
*nạp model 1 lần · validate/whitelist · 11 endpoint*.

---

## MODULE 5 — Tab "Yếu tố nguy cơ" (RiskCorrelationControl) để làm gì?

Nó trả lời câu hỏi: **"chỉ số nào liên quan mạnh nhất đến việc bệnh nặng?"** — phần
*insight* cho người dùng, lấy kết quả phân tích tương quan của Module 2 (không dùng ML).

- Công thức xếp hạng: **impact = trung bình chỉ số ở nhóm High − trung bình ở nhóm Low**.
  Ví dụ alcohol_use: nhóm High trung bình 6.83, nhóm Low 2.23 → impact = **+4.60** → hạng 1.
- Cột "% High khi chỉ số 7–9": trong số bệnh nhân có chỉ số đó ở mức cao, bao nhiêu % rơi
  vào nhóm High — ví dụ passive_smoker = **100%** (ai hút thuốc thụ động mức 7–9 đều High).
- Top 5 thật của dataset: alcohol_use (+4.60) · coughing_of_blood (+4.58) · obesity (+4.27)
  · passive_smoker (+3.90) · genetic_risk (+3.65). Yếu nhất: snoring (+1.09).

**Giá trị khi demo/vấn đáp:** tab Dự đoán chỉ nói "bệnh nhân này High", còn tab này nói
"vì những yếu tố NÀO mà mức độ thường High" — một cái là dự đoán cá nhân (ML), một cái là
tri thức rút từ toàn bộ dữ liệu (thống kê). Nhớ nói rõ: **tương quan ≠ nhân quả**, và đây
là kết quả aggregation MapReduce chứ không phải model ML — thể hiện đúng chất "Big Data
analytics" của đề bài.

---

## Checklist chỉnh sơ đồ draw.io (tóm tắt các quyết định ở trên)

- [ ] Module 1: giữ bản vẽ, 1 hàng ngang; map-only + R2 đếm vi phạm; ghi rõ key–value 2 nhánh
- [ ] Module 2: gộp thành 1 sơ đồ, CHỈ 2 nhánh job MapReduce; **Shuffle/Sort vẽ thành hộp
      riêng giữa Map và Reduce** (chính là lệnh `sort`); KHÔNG vẽ khối tìm kiếm ở đây nữa
- [ ] Module 3: vẽ dạng pipeline Spark (không map/reduce); CHỈ nhánh Logistic Regression
      (RF không vẽ — chỉ là 1 câu ghi chú trong báo cáo); nhớ hộp feature_signature → group-aware split
- [ ] Module 4: 1 hộp FastAPI với 3 ý: nạp model 1 lần · validate/whitelist · 11 endpoint
- [ ] Module 5: 5 tab, mỗi tab ghi endpoint nó gọi; thêm mục **5.2 Tìm kiếm & lọc bệnh nhân**
      (vẽ luồng: bộ lọc UI → GET /patients → whitelist → Mongo find → bảng + xuất CSV);
      tab Yếu tố nguy cơ chú thích "impact = mean(High) − mean(Low), từ Module 2"
