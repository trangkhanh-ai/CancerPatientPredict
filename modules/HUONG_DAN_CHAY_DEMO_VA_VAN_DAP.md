# HƯỚNG DẪN CHẠY DEMO (MongoDB → API → WinForms) + KỊCH BẢN VẤN ĐÁP

> Chuỗi khởi động luôn theo thứ tự: **MongoDB → FastAPI → WinForms**.
> Tắt theo thứ tự ngược lại. Mỗi phần chạy ở 1 cửa sổ PowerShell riêng.

```
[1] MongoDB :27017  ──▶  [2] FastAPI :8000 (nạp Spark model 1 lần)  ──▶  [3] WinForms
     kho dữ liệu              bộ não / serving layer                      giao diện
```

---

## BƯỚC 1 — MongoDB (kho dữ liệu)

### 1.1. Kiểm tra MongoDB có đang chạy không

```powershell
Test-NetConnection localhost -Port 27017
# TcpTestSucceeded : True  → đang chạy, sang 1.2
```

Nếu `False` — khởi động bằng một trong hai cách:

```powershell
# Cách A: dịch vụ Windows (nếu cài MongoDB Community)
net start MongoDB

# Cách B: Docker
docker run -d -p 27017:27017 --name mongo7 mongo:7
```

### 1.2. Nạp dữ liệu (chỉ cần làm 1 lần — chạy lại cũng không sao vì idempotent)

```powershell
cd d:\1BigDataproject1\final\cancer_bigdata
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'

python src/mongodb/create_collections.py      # tạo 6 collections + validator
python src/mongodb/create_indexes.py          # unique patient_id + index
python src/mongodb/import_patients.py --input data/processed/cancer_patients_ml_ready.csv
python src/mongodb/import_mapreduce_stats.py --input artifacts/distributions.tsv
python src/mongodb/verify_database.py         # PHẢI in: VERIFY: PASS
```

**Kết nối MongoDB nằm ở đâu trong code?** Chuỗi cấu hình:
`.env` (`MONGO_URI=mongodb://localhost:27017`, `MONGO_DB=cancer_project`)
→ `src/api/settings.py` đọc env → `src/mongodb/client.py` tạo `MongoClient`
→ `src/api/deps.py` (`get_db`) bơm DB vào từng endpoint qua `Depends(get_db)`.
Muốn đổi sang MongoDB Atlas: chỉ sửa `MONGO_URI` trong `.env`, KHÔNG sửa code.

---

## BƯỚC 2 — FastAPI (bộ não, cổng :8000)

```powershell
cd d:\1BigDataproject1\final\cancer_bigdata
$env:JAVA_HOME  = 'C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot'  # Spark cần JDK 17
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Chờ dòng `[startup] model_loaded=True` (~20 giây — Spark nạp PipelineModel đúng 1 lần).

Kiểm tra nhanh trên trình duyệt:
- `http://127.0.0.1:8000/docs` — Swagger, phải thấy đủ 11 endpoint
- `http://127.0.0.1:8000/api/v1/health` — phải ra `{"status":"ok","mongodb":"ok","model_loaded":true,...}`

Lưu ý:
- Chạy **đúng 1 worker** (mặc định) — mỗi worker tạo 1 SparkSession riêng, tốn RAM.
- Lần `POST /predict` đầu tiên mất ~50–60 giây (Spark khởi động codegen) — KHÔNG phải treo.
- **Nếu máy vừa ngủ (sleep)**: JVM Spark chết ngầm → /predict trả 500 dù /health vẫn ok.
  Cách sửa: Ctrl+C tắt uvicorn rồi chạy lại lệnh trên.

---

## BƯỚC 3 — WinForms C# (giao diện)

```powershell
cd d:\1BigDataproject1\final\cancer_bigdata\winforms
dotnet run --project CancerBigData
```

(Hoặc mở `CancerBigData.sln` bằng Visual Studio → F5.)

- Địa chỉ API đọc từ `CancerBigData/appsettings.json`:
  `"ApiBaseUrl": "http://localhost:8000/api/v1/"` — **bắt buộc có `/api/v1/` và dấu `/` cuối**.
- Thanh trạng thái dưới cùng tự gọi `/health` mỗi 30 giây:
  **xanh** = API + model OK · **vàng** = API sống nhưng model chưa nạp · **đỏ** = không nối được API.

### Kịch bản demo gợi ý (đi từng tab, ~5 phút)

1. **✔ Chất lượng dữ liệu** — mở đầu: "dữ liệu 1000 dòng, 100% hợp lệ, nhưng chỉ 152 vector
   đặc trưng duy nhất / 848 dòng trùng" → dẫn vào lý do group-aware split.
2. **📊 Thống kê** — donut High 365 / Medium 332 / Low 303; cột trung bình chỉ số theo mức độ.
3. **⚠ Yếu tố nguy cơ** — top 5: alcohol_use (+4.60) · coughing_of_blood (+4.58) · obesity
   (+4.27) · passive_smoker (+3.90, 100% High khi 7–9) · genetic_risk (+3.65).
4. **👥 Danh sách bệnh nhân** — demo đúng yêu cầu đề bài "lọc theo TỪNG chỉ số":
   chọn Mức độ = High, chỉ số = obesity, toán tử ≥, giá trị 7 → Tìm → Xuất CSV.
   Thử nhập bậy để khoe whitelist: không thể — UI chỉ cho chọn trong danh sách.
5. **🩺 Dự đoán** — nhập bộ chỉ số cao (7–8) → Dự đoán → High ~95%; nhắc disclaimer học thuật.
   (Nếu là lần predict đầu sau khi bật API: nói trước với giám khảo là chờ ~1 phút.)

---

## GIẢI THÍCH CODE THEO 2 LUỒNG — dễ trình bày nhất

### Luồng 1: bấm "Tìm kiếm" ở tab Danh sách bệnh nhân (đường đi của 1 request)

```
[C#] BuildQuery()                 gom lựa chọn UI → ?level=High&feature=obesity&operator=gte&value=7
  ↓
[C#] ApiClient.SearchPatientsAsync()   HttpClient static gọi GET /api/v1/patients (async, không block UI)
  ↓
[Py] api_router.patients()        nhận query param
  ↓
[Py] query_builder.build_patient_query()   ĐỐI CHIẾU WHITELIST: field ∈ 21 chỉ số,
                                  operator ∈ {eq,gte,lte,between} — sai → 422, chặn injection
  ↓
[Py] data_services.list_patients()    db.patients.find(query).sort().skip().limit()  ← MONGODB Ở ĐÂY
  ↓
[C#] FillGrid()                   parse JSON → DataGridView, tô màu Low/Medium/High
```

### Luồng 2: bấm "Dự đoán" ở tab Dự đoán

```
[C#] BuildFeatures()              23 ô nhập → JSON (key trùng từng chữ FEATURE_COLUMNS)
  ↓
[Py] schemas.PredictRequest       Pydantic validate: age 0–120, gender {1,2}, chỉ số [1..9],
                                  extra="forbid" (thừa field → 422)
  ↓
[Py] model_service.predict()      asyncio.Lock → Spark PipelineModel.transform(1 dòng)
                                  → predicted_level + probabilities (model nạp sẵn từ startup)
  ↓
[Py] api_router.predict()         lưu lịch sử vào db.predictions (try/except riêng —
                                  Mongo chết vẫn trả kết quả)  ← MONGODB Ở ĐÂY (chỉ ghi sổ)
  ↓
[C#] hiển thị mức độ + 3 thanh xác suất + disclaimer; bắt riêng 503 (model chưa nạp) / 422
```

**Chốt lại vai trò từng công nghệ:** MongoDB = kho phục vụ tìm kiếm/thống kê ·
Spark = huấn luyện + suy luận model · FastAPI = cổng duy nhất nối 2 thế giới ·
WinForms = hiển thị, không tính toán.

---

## 10 CÂU VẤN ĐÁP DỰ KIẾN + TRẢ LỜI NGẮN

1. **Vì sao dùng MongoDB mà không phải MySQL?**
   Document JSON khớp thẳng bản ghi bệnh nhân 25 trường + dễ thêm trường dẫn xuất
   (feature_signature, age_group) không cần ALTER TABLE; aggregation pipeline phục vụ
   thống kê; đề bài yêu cầu lưu MongoDB.

2. **Dữ liệu vào MongoDB bằng cách nào? Chạy lại có bị nhân đôi không?**
   `import_patients.py` dùng bulk `UpdateOne(upsert=True)` khớp theo `patient_id` —
   idempotent: chạy 10 lần vẫn đúng 1000 document. Thêm 2 tầng chặn: index unique
   `patient_id` + JSON Schema validator trên collection.

3. **Vì sao phải group-aware split?**
   1000 dòng nhưng chỉ 152 vector 23-đặc-trưng duy nhất (848 dòng trùng). Random split
   theo dòng sẽ đưa cùng cấu hình sang cả train lẫn test → leakage. Nên chia theo NHÓM
   `feature_signature` (SHA-256 của 23 chỉ số), assert overlap = 0.

4. **Accuracy = 1.0 có phải mô hình quá giỏi / có gian lận không?**
   Không do leakage (overlap=0 đã assert). Cũng không phải mô hình giỏi: 152 vector có
   0 xung đột nhãn → nhãn gần như là HÀM XÁC ĐỊNH của 23 chỉ số → dữ liệu separable.
   Đây là đặc tính của dataset học thuật; dữ liệu thực có nhiễu sẽ thấp hơn.

5. **Chống injection ở API thế nào?**
   Whitelist 3 tập trong `query_builder.py` (field/operator/sort) + ép `int()` mọi giá
   trị; ngoài tập → 422, chuỗi lạ không bao giờ chạm tới Mongo query.

6. **Vì sao model chỉ nạp 1 lần? Vì sao 1 worker?**
   Nạp SparkSession + PipelineModel mất hàng chục giây — nạp trong lifespan startup để
   mỗi request chỉ transform. Nhiều worker = nhiều SparkSession = ngốn RAM vô ích.

7. **MapReduce trong đồ án nằm ở đâu, chạy kiểu gì?**
   Hadoop Streaming: mapper/reducer là script Python đọc stdin ghi stdout, nối bằng
   `cat | mapper | sort | reducer`. Job 1 đếm phân bố (word-count style ~26 cặp key/dòng);
   job 2 tính mean theo level + bảng chéo bucket → xếp hạng impact = mean(High) − mean(Low).

8. **Ở C# vì sao chỉ có 1 HttpClient static? Vì sao phải async?**
   Tạo HttpClient mỗi request gây cạn socket (socket exhaustion). Async/await để UI
   thread không bị đứng khi chờ mạng; tuyệt đối không `.Result`/`.Wait()` (deadlock).

9. **`/patients/export` vì sao phải khai báo trước `/patients/{patient_id}`?**
   FastAPI khớp route theo thứ tự khai báo — đảo lại thì "export" bị hiểu là
   `patient_id="export"` và trả 404.

10. **valid_row_pct khác gì field_completeness_pct?**
    valid_row_pct = % DÒNG đạt mọi ràng buộc (thang 1–9, gender 1/2, tuổi 0–120…);
    field_completeness_pct = % Ô dữ liệu không bị thiếu. Một dòng đủ ô vẫn có thể
    sai miền giá trị → hai chỉ số đo hai thứ khác nhau.

---

## SỰ CỐ THƯỜNG GẶP KHI DEMO

| Triệu chứng | Nguyên nhân → Cách xử lý |
|---|---|
| WinForms báo đỏ "API: KHÔNG kết nối được" | Chưa bật uvicorn → chạy Bước 2 |
| Tab có dữ liệu nhưng Dự đoán báo "Model chưa được nạp (503)" | Thiếu `models/current/` hoặc JAVA_HOME sai → kiểm tra log uvicorn lúc startup |
| /predict trả 500 sau khi máy ngủ | JVM Spark chết ngầm → restart uvicorn |
| Mọi request 404 từ C# | appsettings.json thiếu `/api/v1/` hoặc thiếu `/` cuối |
| `ModuleNotFoundError: common` | Quên `$env:PYTHONPATH='src'` hoặc không đứng ở gốc repo |
| Spark lỗi "class file version 61.0" | Java < 17 → đặt JAVA_HOME trỏ JDK 17 |
| Tab trống, /health báo `mongodb: down` | MongoDB chưa chạy → Bước 1.1 |
