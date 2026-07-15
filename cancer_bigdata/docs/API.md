# Hợp đồng API — prefix `/api/v1`

Chạy: `uvicorn src.api.main:app --host 127.0.0.1 --port 8000` (**đúng 1 worker**).
Swagger UI: `http://127.0.0.1:8000/docs`.

## 11 endpoint

| Method | Path | Query / Body | Trả về |
|---|---|---|---|
| GET | `/health` | — | `{status, mongodb, model_loaded, model_run_id, dataset_version}` |
| GET | `/model` | — | `{algorithm, feature_columns, label_mapping, metrics}` · **503** nếu chưa nạp |
| POST | `/predict` | 23 chỉ số + `patient_id?` | `{prediction_id, predicted_level, probabilities{Low,Medium,High}, latency_ms, disclaimer}` |
| GET | `/patients` | `page, page_size, level, gender, age_min, age_max, feature, operator, value, min_value, max_value, sort_by, sort_dir` | `{items[], page, page_size, total, total_pages}` |
| GET | `/patients/export` | như `/patients` (không paging) | **CSV** (StreamingResponse) |
| GET | `/patients/{id}` | — | document · **404** nếu không có |
| GET | `/predictions` | `patient_id, predicted_level, page, page_size` | lịch sử dự đoán |
| GET | `/predictions/{id}` | — | 1 prediction |
| GET | `/stats` | — | `{total, level_distribution, gender_distribution, age_group_distribution, avg_indicators_by_level, chart_indicators}` |
| GET | `/quality` | — | `{row_count_raw, row_count_valid, valid_row_pct, field_completeness_pct, unique_feature_signature, duplicated_feature_rows, checks_table[]}` |
| GET | `/correlation` | — | `{total, factors[{rank, indicator, mean_by_level, impact, pct_high_when_high_value}], top_risk_factors[]}` |

> ⚠ **Thứ tự route:** `/patients/export` được khai báo **TRƯỚC** `/patients/{patient_id}`.
> Nếu đảo ngược, request export sẽ bị khớp nhầm thành `patient_id="export"`.

## Whitelist cho `/patients` (chống injection)

- `feature` ∈ 21 chỉ số của `SCALE_1_9_COLUMNS`
- `operator` ∈ `{eq, gte, lte, between}`
- `sort_by` ∈ `{patient_id, age, level, gender}` ∪ 21 chỉ số
- Sai whitelist → **422** (không được để lọt vào Mongo query)

## Body `POST /predict`

Pydantic v2, `extra="forbid"` — 23 trường bắt buộc + `patient_id` tuỳ chọn:

```json
{
  "age": 44, "gender": 1,
  "air_pollution": 6, "alcohol_use": 7, "dust_allergy": 7,
  "occupational_hazards": 7, "genetic_risk": 6, "chronic_lung_disease": 6,
  "balanced_diet": 7, "obesity": 7, "smoking": 7, "passive_smoker": 7,
  "chest_pain": 7, "coughing_of_blood": 8, "fatigue": 5, "weight_loss": 3,
  "shortness_of_breath": 2, "wheezing": 7, "swallowing_difficulty": 8,
  "clubbing_of_finger_nails": 2, "frequent_cold": 4, "dry_cough": 5, "snoring": 3
}
```

Ràng buộc: `age` ∈ [0, 120] · `gender` ∈ {1 = Nam, 2 = Nữ} · 21 chỉ số còn lại ∈ [1..9].

## Mã lỗi chuẩn

| Mã | Ý nghĩa |
|---|---|
| **422** | sai miền giá trị / sai whitelist / body thừa trường |
| **404** | không tìm thấy bản ghi |
| **503** | model chưa nạp |
| **500** | lỗi nội bộ (không lộ stack trace) |
