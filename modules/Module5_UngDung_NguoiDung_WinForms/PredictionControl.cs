using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 4/5 — Tab "Dự đoán": nhập 23 chỉ số (age 0–120, gender Nam/Nữ, 21 chỉ số 1–9),
    /// gọi POST /api/v1/predict (async), hiển thị mức độ + xác suất 3 lớp + disclaimer.
    /// Bắt lỗi: 503 → "Model chưa được nạp"; 422 → thông báo lỗi validate.
    /// </summary>
    /// <remarks>
    /// ===================== MỤC LỤC FILE =====================
    /// [QUAN TRỌNG] BuildFeatures()  — gom 23 ô nhập thành JSON body; tên key phải trùng
    ///              từng chữ FEATURE_COLUMNS (backend đặt extra="forbid", thừa/sai tên → 422)
    /// [QUAN TRỌNG] PredictAsync()   — gọi POST /predict async; bắt RIÊNG ApiException 503
    ///              (model chưa nạp) và 422 (nhập sai miền) để báo lỗi dễ hiểu
    /// [QUAN TRỌNG] FormatValidationError() — dịch mảng detail[].loc/msg của FastAPI 422
    ///              thành từng dòng "• trường: lỗi" cho người dùng đọc được
    /// Phần còn lại:
    ///   INDICATORS        — bảng (key snake_case, nhãn tiếng Việt) cho 21 chỉ số
    ///   BuildUi()         — lưới 3 cột × 7 hàng NumericUpDown + panel kết quả (layout)
    ///   DrawProbabilities()— vẽ 3 thanh xác suất Low/Medium/High bằng GDI+
    ///   ResetInputs()     — đưa form về mặc định
    /// =========================================================
    /// </remarks>
    public class PredictionControl : UserControl
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color MED = Color.FromArgb(224, 160, 26);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color BLUE = Color.FromArgb(47, 111, 237);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        // 21 chỉ số thang 1–9 (đúng thứ tự schema canonical) + nhãn tiếng Việt
        private static readonly (string Key, string Label)[] INDICATORS =
        {
            ("air_pollution", "Ô nhiễm không khí"),
            ("alcohol_use", "Sử dụng rượu bia"),
            ("dust_allergy", "Dị ứng bụi"),
            ("occupational_hazards", "Nguy cơ nghề nghiệp"),
            ("genetic_risk", "Nguy cơ di truyền"),
            ("chronic_lung_disease", "Bệnh phổi mãn tính"),
            ("balanced_diet", "Chế độ ăn cân bằng"),
            ("obesity", "Béo phì"),
            ("smoking", "Hút thuốc"),
            ("passive_smoker", "Hút thuốc thụ động"),
            ("chest_pain", "Đau ngực"),
            ("coughing_of_blood", "Ho ra máu"),
            ("fatigue", "Mệt mỏi"),
            ("weight_loss", "Sụt cân"),
            ("shortness_of_breath", "Khó thở"),
            ("wheezing", "Thở khò khè"),
            ("swallowing_difficulty", "Khó nuốt"),
            ("clubbing_of_finger_nails", "Ngón tay dùi trống"),
            ("frequent_cold", "Cảm lạnh thường xuyên"),
            ("dry_cough", "Ho khan"),
            ("snoring", "Ngáy"),
        };

        private readonly ApiClient _api = new ApiClient();

        private readonly NumericUpDown _numAge = new NumericUpDown();
        private readonly ComboBox _cbGender = new ComboBox();
        private readonly TextBox _txtPatientId = new TextBox();
        private readonly Dictionary<string, NumericUpDown> _inputs = new();
        private readonly Button _btnPredict = new Button();
        private readonly Button _btnReset = new Button();

        private readonly Panel _pnlResult = new Panel();
        private readonly Label _lblLevel = new Label();
        private readonly Label _lblLatency = new Label();
        private readonly Label _lblDisclaimer = new Label();
        private readonly Label _lblStatus = new Label();
        private PredictResponseDto _result;

        public PredictionControl()
        {
            BackColor = Color.FromArgb(238, 241, 245);
            Dock = DockStyle.Fill;
            BuildUi();
        }

        private void BuildUi()
        {
            var title = new Label
            {
                Text = "Dự đoán mức độ mắc bệnh ung thư",
                Left = 16, Top = 12, AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold)
            };

            // ---- panel nhập liệu (trái) ----
            var pnlInput = new Panel
            {
                Left = 12, Top = 44, Width = 720, Height = 540,
                BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle,
                AutoScroll = true,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Bottom
            };

            // hàng đầu: mã BN (tuỳ chọn) + tuổi + giới tính
            AddLabel(pnlInput, "Mã BN (tuỳ chọn):", 12, 14);
            _txtPatientId.SetBounds(128, 10, 100, 24); pnlInput.Controls.Add(_txtPatientId);

            AddLabel(pnlInput, "Tuổi:", 250, 14);
            _numAge.SetBounds(290, 10, 64, 24); _numAge.Minimum = 0; _numAge.Maximum = 120; _numAge.Value = 35;
            pnlInput.Controls.Add(_numAge);

            AddLabel(pnlInput, "Giới tính:", 376, 14);
            _cbGender.Items.AddRange(new object[] { "Nam", "Nữ" });
            _cbGender.SelectedIndex = 0; _cbGender.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbGender.SetBounds(440, 10, 90, 24); pnlInput.Controls.Add(_cbGender);

            var hint = new Label
            {
                Text = "Các chỉ số dưới đây theo thang 1 (nhẹ nhất) → 9 (nặng nhất):",
                Left = 12, Top = 46, AutoSize = true, ForeColor = MUT
            };
            pnlInput.Controls.Add(hint);

            // 21 chỉ số — lưới 3 cột × 7 hàng
            const int colW = 232, rowH = 54, x0 = 12, y0 = 72;
            for (int i = 0; i < INDICATORS.Length; i++)
            {
                var (key, label) = INDICATORS[i];
                int cx = x0 + (i % 3) * colW;
                int cy = y0 + (i / 3) * rowH;
                var lb = new Label { Text = label, Left = cx, Top = cy, AutoSize = true, ForeColor = Color.FromArgb(60, 66, 74) };
                var num = new NumericUpDown { Minimum = 1, Maximum = 9, Value = 1 };
                num.SetBounds(cx, cy + 18, 70, 24);
                _inputs[key] = num;
                pnlInput.Controls.Add(lb);
                pnlInput.Controls.Add(num);
            }

            int btnY = y0 + 7 * rowH + 8;
            _btnPredict.Text = "🩺 Dự đoán"; _btnPredict.SetBounds(x0, btnY, 140, 34);
            _btnPredict.FlatStyle = FlatStyle.Flat; _btnPredict.BackColor = BLUE; _btnPredict.ForeColor = Color.White;
            _btnPredict.Font = new Font("Segoe UI", 10, FontStyle.Bold);
            _btnPredict.Click += async (s, e) => await PredictAsync();
            pnlInput.Controls.Add(_btnPredict);

            _btnReset.Text = "Đặt lại"; _btnReset.SetBounds(x0 + 152, btnY, 90, 34); _btnReset.FlatStyle = FlatStyle.Flat;
            _btnReset.Click += (s, e) => ResetInputs();
            pnlInput.Controls.Add(_btnReset);

            // ---- panel kết quả (phải) ----
            _pnlResult.Left = 744; _pnlResult.Top = 44; _pnlResult.Size = new Size(420, 540);
            _pnlResult.BackColor = Color.White; _pnlResult.BorderStyle = BorderStyle.FixedSingle;
            _pnlResult.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _pnlResult.Paint += DrawProbabilities;

            _lblLevel.Text = "Chưa dự đoán"; _lblLevel.ForeColor = MUT;
            _lblLevel.Font = new Font("Segoe UI", 20, FontStyle.Bold);
            _lblLevel.SetBounds(20, 52, 380, 44); _lblLevel.TextAlign = ContentAlignment.MiddleLeft;
            _pnlResult.Controls.Add(_lblLevel);

            _lblLatency.Text = ""; _lblLatency.ForeColor = MUT; _lblLatency.AutoSize = true;
            _lblLatency.Location = new Point(22, 100);
            _pnlResult.Controls.Add(_lblLatency);

            _lblDisclaimer.Text = "Kết quả phục vụ mục đích học thuật, không thay thế chẩn đoán y khoa.";
            _lblDisclaimer.ForeColor = MUT; _lblDisclaimer.Font = new Font("Segoe UI", 8, FontStyle.Italic);
            _lblDisclaimer.SetBounds(20, 490, 380, 40);
            _pnlResult.Controls.Add(_lblDisclaimer);

            _lblStatus.Text = "Nhập 23 chỉ số rồi bấm Dự đoán."; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.SetBounds(16, 596, 700, 20); _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, pnlInput, _pnlResult, _lblStatus });
            Resize += (s, e) => { _pnlResult.Width = Math.Max(320, Width - 756); };
        }

        private static void AddLabel(Control parent, string text, int x, int y)
            => parent.Controls.Add(new Label { Text = text, Left = x, Top = y, AutoSize = true, ForeColor = Color.FromArgb(60, 66, 74) });

        private void ResetInputs()
        {
            _txtPatientId.Text = "";
            _numAge.Value = 35;
            _cbGender.SelectedIndex = 0;
            foreach (var num in _inputs.Values) num.Value = 1;
            _result = null;
            _lblLevel.Text = "Chưa dự đoán"; _lblLevel.ForeColor = MUT;
            _lblLatency.Text = "";
            _pnlResult.Invalidate();
            _lblStatus.Text = "Đã đặt lại. Nhập 23 chỉ số rồi bấm Dự đoán."; _lblStatus.ForeColor = MUT;
        }

        /// <summary>Body JSON khớp PredictRequest (extra=forbid): 23 đặc trưng + patient_id tuỳ chọn.</summary>
        private Dictionary<string, object> BuildFeatures()
        {
            var f = new Dictionary<string, object>
            {
                ["age"] = (int)_numAge.Value,
                ["gender"] = _cbGender.SelectedIndex + 1,   // 1=Nam, 2=Nữ
            };
            foreach (var (key, _) in INDICATORS)
                f[key] = (int)_inputs[key].Value;
            if (!string.IsNullOrWhiteSpace(_txtPatientId.Text))
                f["patient_id"] = _txtPatientId.Text.Trim();
            return f;
        }

        private async Task PredictAsync()
        {
            _btnPredict.Enabled = false;
            _lblStatus.Text = "Đang dự đoán... (lần đầu có thể mất ~1 phút do Spark khởi tạo)";
            _lblStatus.ForeColor = MUT;
            try
            {
                _result = await _api.PredictAsync(BuildFeatures());
                string lv = _result.PredictedLevel;
                _lblLevel.Text = lv == "High" ? "Mức độ: CAO (High)"
                               : lv == "Medium" ? "Mức độ: TRUNG BÌNH (Medium)"
                               : "Mức độ: THẤP (Low)";
                _lblLevel.ForeColor = lv == "High" ? HIGH : lv == "Medium" ? MED : LOW;
                _lblLatency.Text = $"prediction_id: {_result.PredictionId}   ·   độ trễ: {_result.LatencyMs:0} ms";
                if (!string.IsNullOrWhiteSpace(_result.Disclaimer))
                    _lblDisclaimer.Text = _result.Disclaimer;
                _pnlResult.Invalidate();
                _lblStatus.Text = "Dự đoán thành công."; _lblStatus.ForeColor = LOW;
            }
            catch (ApiException ex) when (ex.StatusCode == 503)
            {
                _lblStatus.Text = "Model chưa được nạp (503)."; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Model chưa được nạp trên máy chủ.\n" +
                                "Hãy huấn luyện model (spark-submit src/ml/train.py) và khởi động lại API.",
                                "Model chưa sẵn sàng", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            catch (ApiException ex) when (ex.StatusCode == 422)
            {
                _lblStatus.Text = "Dữ liệu nhập không hợp lệ (422)."; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Dữ liệu nhập không hợp lệ:\n" + FormatValidationError(ex.Body),
                                "Lỗi kiểm tra dữ liệu", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi gọi API /predict."; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không gọi được API /predict.\n" + ex.Message, "Lỗi",
                                MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            finally { _btnPredict.Enabled = true; }
        }

        /// <summary>Rút gọn thông báo 422 của FastAPI (detail[].loc + msg) cho dễ đọc.</summary>
        private static string FormatValidationError(string body)
        {
            try
            {
                using var doc = JsonDocument.Parse(body);
                if (doc.RootElement.TryGetProperty("detail", out var detail))
                {
                    if (detail.ValueKind == JsonValueKind.String)
                        return detail.GetString();
                    if (detail.ValueKind == JsonValueKind.Array)
                    {
                        var lines = new List<string>();
                        foreach (var it in detail.EnumerateArray())
                        {
                            string field = "";
                            if (it.TryGetProperty("loc", out var loc) && loc.ValueKind == JsonValueKind.Array)
                            {
                                var parts = new List<string>();
                                foreach (var l in loc.EnumerateArray())
                                    if (l.ValueKind == JsonValueKind.String) parts.Add(l.GetString());
                                field = string.Join(".", parts);
                            }
                            string msg = it.TryGetProperty("msg", out var m) ? m.GetString() : "";
                            lines.Add($"• {field}: {msg}");
                        }
                        if (lines.Count > 0) return string.Join(Environment.NewLine, lines);
                    }
                }
            }
            catch { /* trả nguyên văn */ }
            return body;
        }

        /// <summary>Vẽ 3 thanh xác suất Low/Medium/High bằng GDI+.</summary>
        private void DrawProbabilities(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fTitle = new Font("Segoe UI", 11, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 9);
            g.DrawString("Kết quả dự đoán", fTitle, Brushes.Black, 18, 16);

            if (_result == null)
            {
                g.DrawString("Chưa có kết quả — nhập chỉ số và bấm Dự đoán.", fSmall, new SolidBrush(MUT), 20, 140);
                return;
            }

            string[] order = { "Low", "Medium", "High" };
            string[] labels = { "Thấp (Low)", "Trung bình (Medium)", "Cao (High)" };
            Color[] colors = { LOW, MED, HIGH };
            int x0 = 20, barMax = _pnlResult.Width - x0 - 100, y = 150;
            for (int i = 0; i < order.Length; i++)
            {
                double p = _result.Probabilities.TryGetValue(order[i], out var v) ? v : 0.0;
                g.DrawString(labels[i], fSmall, Brushes.Black, x0, y);
                using var back = new SolidBrush(Color.FromArgb(238, 241, 245));
                g.FillRectangle(back, x0, y + 22, barMax, 22);
                using var br = new SolidBrush(colors[i]);
                g.FillRectangle(br, x0, y + 22, (int)Math.Max(2, p * barMax), 22);
                g.DrawString((p * 100).ToString("0.0") + "%", fSmall, new SolidBrush(colors[i]), x0 + barMax + 8, y + 24);
                y += 74;
            }
        }
    }
}
