# API (FastAPI) — endpoints

Prefix: `/api/v1`. Chạy (1 worker cho demo vì mỗi worker tạo 1 SparkSession):
```
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```
| Method | Path | Mô tả |
|---|---|---|
| GET | /health | trạng thái mongo/model |
| GET | /model | thông tin model đã nạp |
| POST | /predict | dự đoán 23 chỉ số → Low/Medium/High + xác suất (lưu predictions) |
| GET | /patients | danh sách + lọc theo chỉ số (whitelist) + phân trang |
| GET | /patients/{id} | chi tiết bệnh nhân (404 nếu không có) |
| GET | /predictions, /predictions/{id} | lịch sử dự đoán |
| GET | /stats | thống kê (đầu ra R2) |
| GET | /quality | chất lượng dữ liệu (valid_row_pct vs field_completeness_pct) |

Đã kiểm bằng TestClient: đủ endpoint; /predict trả 503 khi chưa nạp model; 422 khi input sai miền.
Lọc /patients an toàn: chỉ nhận field/operator trong whitelist (chống injection).
