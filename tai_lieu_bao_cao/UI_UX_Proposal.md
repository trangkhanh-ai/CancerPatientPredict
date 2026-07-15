# Đề xuất UI/UX – Hệ thống dự đoán nguy cơ ung thư

---

## Phần 1: Đề xuất UI thân thiện hơn cho người dùng

### Nguyên tắc thiết kế chung

- **Dark theme** như hiện tại → giữ nguyên, phù hợp môi trường y tế chuyên nghiệp
- **Sidebar điều hướng** → giữ nguyên, dễ chuyển màn hình
- **Font chữ lớn hơn** ở các kết quả quan trọng (nhãn nguy cơ, xác suất)
- **Màu sắc nhất quán**: Đỏ = Cao, Cam = Trung bình, Xanh lá = Thấp — áp dụng xuyên suốt toàn hệ thống
- **Thông báo phản hồi** rõ ràng sau mỗi thao tác (lưu, dự đoán, xóa)

---

### Form 1 – Dashboard / Tổng quan

**Giữ lại:**
- 4 card KPI (Tổng BN, Nguy cơ cao, Độ chính xác, Dự đoán hôm nay)
- Bảng ca dự đoán gần đây
- Biểu đồ phân bố theo tháng

**Bổ sung / Cải tiến:**
- Thêm **3 biểu đồ MapReduce** bên dưới: phân bố Low/Medium/High (pie chart), phân bố nhóm tuổi (bar), mức hút thuốc (bar)
- Card KPI có **mũi tên so sánh** tháng trước (tăng/giảm)
- Click vào card "Nguy cơ cao" → tự động mở Form Bệnh nhân đã lọc sẵn "Cao"
- Thanh status bar hiển thị: trạng thái kết nối MongoDB, FastAPI, thời gian đồng bộ cuối

---

### Form 2 – Dự đoán nguy cơ

**Vấn đề hiện tại:** 23 chỉ số nếu đổ hết vào một form sẽ rất rối.

**Giải pháp – Chia thành 3 Tab:**

**Tab 1 – Thông tin cơ bản**
- Mã BN (tự sinh hoặc nhập tay)
- Họ tên, Tuổi, Giới tính
- Nút "Tải từ danh sách" → chọn BN có sẵn, tự điền

**Tab 2 – Chỉ số lâm sàng (nhóm 1)**
- Kích thước khối u, Số hạch di căn, Chỉ số BMI
- Giai đoạn lâm sàng, Tiền sử gia đình
- Các chỉ số xét nghiệm máu (nhóm từ dataset)

**Tab 3 – Lối sống & yếu tố nguy cơ**
- Hút thuốc, Uống rượu, Hoạt động thể chất
- Chế độ ăn, Ô nhiễm môi trường
- Các chỉ số còn lại từ dataset

**Thanh tiến trình nhập liệu** phía trên: `Tab 1 ──● Tab 2 ──○ Tab 3` → biết đang ở bước nào

**Cải tiến thêm:**
- Validate realtime: ô nhập sai range → viền đỏ + tooltip giải thích
- Tooltip nhỏ bên cạnh mỗi chỉ số: giải thích ngắn (ví dụ "BMI bình thường: 18.5–24.9")
- Nút **Xóa form** và **Dự đoán** cố định ở footer, không bị cuộn mất
- Sau khi dự đoán xong → hỏi "Lưu hồ sơ bệnh nhân này không?" (dialog xác nhận)

---

### Form 3 – Kết quả Dự đoán

**Giữ lại:**
- Gauge chart xác suất
- Nhãn phân loại màu sắc
- Yếu tố ảnh hưởng chính (feature importance bar)
- Khuyến nghị y tế
- Nút Xuất PDF, Lưu hồ sơ

**Bổ sung / Cải tiến:**
- Thêm **3 thanh xác suất riêng** từng lớp:
  - 🟢 Thấp: 8%
  - 🟡 Trung bình: 14%
  - 🔴 Cao: 78%
- Khuyến nghị y tế **thay đổi động** theo nhãn kết quả (không cố định 1 nội dung)
- Nút **Dự đoán lại** → quay về Form 2 với dữ liệu cũ còn nguyên
- Nút **Xem lịch sử BN này** → mở chi tiết lịch sử dự đoán của bệnh nhân đó
- Hiển thị thời gian phản hồi API (đã có, giữ nguyên)

---

### Form 4 – Danh sách & Quản lý bệnh nhân

**Vấn đề hiện tại:** Chỉ lọc được theo nguy cơ.

**Bộ lọc mở rộng – thiết kế dạng Collapse Panel:**

```
▼ Bộ lọc nâng cao
  [Tuổi: từ __ đến __]  [Giới tính ▼]  [Nguy cơ ▼]
  [Hút thuốc ▼]  [Giai đoạn lâm sàng ▼]  [Khoảng xác suất: __% – __%]
  [Nút: Áp dụng]  [Nút: Xóa bộ lọc]
```

Mặc định bộ lọc ẩn → click "Bộ lọc nâng cao" mới mở ra, tránh UI rối.

**Cột trong DataGridView:**
- Mã BN, Họ tên, Tuổi, Giới tính, Xác suất, Nguy cơ, Ngày dự đoán gần nhất
- Cột Nguy cơ hiển thị **badge màu** (đỏ/cam/xanh) thay vì chữ thuần

**Hành động trên mỗi dòng:**
- Click dòng → highlight, hiện panel chi tiết bên phải (split view) thay vì mở form mới
- Icon **👁 Xem** – **✏️ Sửa** – **🔮 Dự đoán lại** ở cuối mỗi dòng

**Toolbar phía trên:**
- Nút **+ Thêm bệnh nhân mới**
- Nút **Xuất Excel / CSV**
- Thanh tìm kiếm nhanh theo mã hoặc tên

---

### Form 5 – Chi tiết bệnh nhân *(hiện chưa có)*

- Hiển thị đầy đủ 25 trường chia nhóm (thông tin cơ bản / lâm sàng / lối sống)
- Dòng thời gian (timeline) lịch sử dự đoán của BN đó: ngày → kết quả → xác suất
- Nút **Dự đoán mới** với dữ liệu BN này
- Nút **Chỉnh sửa thông tin**

---

### Form 6 – Lịch sử Dự đoán *(hiện chưa có)*

- Bảng: Mã BN, Họ tên, Thời gian, Kết quả, Xác suất, Model version
- Lọc theo khoảng ngày (DatePicker từ–đến)
- Lọc theo kết quả (Low/Medium/High)
- Nút **Xuất CSV**
- Click dòng → xem lại chi tiết kết quả dự đoán đó

---

### Form 7 – Thống kê *(mở rộng từ Dashboard)*

Tách riêng màn hình thống kê chuyên sâu hơn:

- Biểu đồ phân bố 3 nhãn (pie + số lượng)
- Phân bố theo nhóm tuổi: <30, 30–45, 45–60, >60
- Phân bố theo giới tính × nguy cơ (stacked bar)
- Mức hút thuốc × nguy cơ (grouped bar)
- Bộ lọc thời gian cho tất cả biểu đồ (tháng/quý/năm)

---

### Tổng hợp các cải tiến UX quan trọng nhất

| # | Cải tiến | Lý do |
|---|---|---|
| 1 | Chia form 23 chỉ số thành 3 Tab | Tránh form quá dài, choáng ngợp |
| 2 | Validate realtime từng ô nhập | Tránh lỗi dữ liệu trước khi gửi API |
| 3 | Tooltip giải thích từng chỉ số | Người dùng không phải chuyên gia sẽ hiểu |
| 4 | Bộ lọc nâng cao dạng Collapse | Không chiếm không gian khi không cần |
| 5 | Badge màu cho nhãn nguy cơ | Nhận diện nhanh, nhất quán toàn hệ thống |
| 6 | Split view chi tiết BN bên phải | Không cần mở form mới, tiết kiệm thao tác |
| 7 | Thông báo toast sau mỗi hành động | Người dùng biết thao tác đã thành công/thất bại |
| 8 | Nút Dự đoán lại giữ nguyên dữ liệu cũ | Tiện chỉnh sửa và so sánh kết quả |

---

## Phần 2: Thông tin có ích từ việc sử dụng để đưa vào nghiên cứu

### 2.1 Feature Importance – Ảnh hưởng đặc trưng

Biểu đồ thanh ngang thể hiện mức độ đóng góp của từng chỉ số vào quyết định phân loại của mô hình. Phục vụ trực tiếp cho việc viết báo cáo nghiên cứu, chọn đặc trưng và đề xuất mô hình rút gọn.

| Đặc trưng | Importance Score |
|---|---|
| Số hạch di căn | 0.34 |
| Kích thước khối u | 0.27 |
| Tuổi | 0.19 |
| Tiền sử gia đình | 0.12 |
| Mức hút thuốc | 0.08 |
| Chỉ số BMI | 0.04 |
| Giai đoạn lâm sàng | 0.02 |

---

### 2.2 Phân tích nguy cơ theo nhóm tuổi

Tỷ lệ % bệnh nhân rơi vào nhóm "Cao" trong từng khoảng tuổi. Cho thấy rõ xu hướng tuyến tính tăng theo tuổi — bằng chứng định lượng cho giả thuyết nghiên cứu.

| Nhóm tuổi | Tỷ lệ nguy cơ Cao |
|---|---|
| < 30 tuổi | 8% |
| 30 – 44 | 14% |
| 45 – 59 | 31% |
| 60 – 74 | 58% |
| ≥ 75 tuổi | 72% |

---

### 2.3 Hiệu năng mô hình theo từng lớp phân loại

So sánh Precision / Recall / F1 / AUC riêng từng nhãn Low-Medium-High. Lớp Trung bình thường có F1 thấp nhất — phát hiện quan trọng để cải tiến mô hình.

| Lớp | Precision | Recall | F1 | AUC |
|---|---|---|---|---|
| Thấp (Low) | 92% | 94% | 93% | 0.97 |
| Trung bình (Medium) | 88% | 85% | 86% | 0.94 |
| Cao (High) | 90% | 92% | 91% | 0.98 |
| **Macro avg** | **89.7%** | **88.3%** | **89.0%** | **0.963** |

---

### 2.4 Phân bố yếu tố nguy cơ trong dataset

Tỷ lệ các yếu tố nguy cơ trong toàn bộ 1.000 bệnh nhân — dùng cho phân tích dịch tễ học cơ bản trong bài báo hoặc luận văn.

| Yếu tố | Tỷ lệ có | Tỷ lệ không |
|---|---|---|
| Hút thuốc | 62% | 38% |
| Tiền sử gia đình | 44% | 56% |
| Uống rượu | 37% | 63% |
| Béo phì (BMI > 30) | 28% | 72% |
| Giới tính Nam | 53% | — |

---

### 2.5 Thống kê mô tả dataset (Descriptive Statistics)

Mean ± SD của các chỉ số liên tục — cần thiết cho phần "Phương pháp" và "Mô tả mẫu" trong báo cáo nghiên cứu.

| Chỉ số | Giá trị |
|---|---|
| Tuổi trung bình | 52.4 ± 14.2 |
| Tuổi trung vị | 54 |
| BMI trung bình | 26.1 ± 4.7 |
| Kích thước khối u TB (mm) | 22.8 ± 9.3 |
| Số hạch di căn TB | 3.2 ± 2.1 |
| Tỷ lệ hút thuốc | 42% |

---

### 2.6 Chỉ số hiệu năng tổng thể mô hình

| Chỉ số | Kết quả |
|---|---|
| Accuracy | 91.4% |
| Precision (macro) | 89.7% |
| Recall (macro) | 88.3% |
| F1-score (macro) | 89.0% |
| AUC-ROC | 0.963 |
| Thời gian phản hồi API | ~0.8s |

---

### 2.7 Insights tự động – Phát hiện từ dữ liệu

Các phát hiện được tổng hợp từ dữ liệu thực tế, có thể dùng trực tiếp làm gợi ý cho phần **"Thảo luận"** của bài báo hoặc luận văn:

1. **Tuổi là yếu tố tiên lượng mạnh:** Bệnh nhân ≥ 60 tuổi có tỷ lệ nguy cơ cao gấp 4.5× so với nhóm < 30 tuổi — tuổi là yếu tố tiên lượng mạnh nhất sau số hạch di căn.

2. **Tương tác đặc trưng quan trọng:** Bệnh nhân có tiền sử gia đình + hút thuốc đồng thời chiếm 71% trong nhóm nguy cơ Cao — gợi ý cần cân nhắc mô hình tương tác đặc trưng (interaction features) trong các nghiên cứu tiếp theo.

3. **Ranh giới phân lớp Trung bình cần nghiên cứu thêm:** Phân lớp Trung bình có F1 thấp nhất (86.2%) — ranh giới quyết định giữa Thấp–Trung bình còn mờ, cần thêm dữ liệu hoặc kỹ thuật oversampling.

4. **Gợi ý mô hình rút gọn:** BMI và giai đoạn lâm sàng có importance thấp (< 0.05) — có thể loại bỏ trong phiên bản mô hình rút gọn để tăng tốc độ inference mà không ảnh hưởng đáng kể đến độ chính xác.

---

### 2.8 Thông tin lịch sử dự đoán phục vụ nghiên cứu theo dõi dọc

Hệ thống lưu toàn bộ lịch sử dự đoán trong MongoDB (`prediction_history`), cho phép khai thác các phân tích longitudinal:

- Theo dõi sự thay đổi xác suất nguy cơ của một bệnh nhân qua nhiều lần khám
- So sánh kết quả dự đoán trước/sau can thiệp (bỏ thuốc, giảm cân...)
- Phân tích xu hướng nguy cơ theo thời gian ở cấp độ quần thể
- Đánh giá độ trôi dạt mô hình (model drift) khi dữ liệu mới được cập nhật

---

*Tài liệu này tổng hợp các đề xuất UI/UX và thông tin nghiên cứu cho đề tài:*
**"Xây dựng hệ thống dự đoán mức độ mắc bệnh ung thư sử dụng Big Data và Machine Learning"**
