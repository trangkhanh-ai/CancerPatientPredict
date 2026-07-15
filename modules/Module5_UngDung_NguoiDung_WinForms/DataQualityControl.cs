using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Threading.Tasks;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 1/5 — Tab "Chất lượng dữ liệu": KPI (raw / valid / invalid / % dòng hợp lệ /
    /// % ô đầy đủ) + bảng kiểm định chi tiết. Nguồn: GET /api/v1/quality.
    /// Lưu ý: valid_row_pct (% DÒNG hợp lệ) KHÁC field_completeness_pct (% Ô không thiếu).
    /// </summary>
    /// <remarks>
    /// ===================== MỤC LỤC FILE =====================
    /// [QUAN TRỌNG] Hai chỉ số dễ nhầm (bẫy #7 của đồ án):
    ///              valid_row_pct        = % DÒNG đạt mọi ràng buộc
    ///              field_completeness_pct = % Ô dữ liệu không bị thiếu
    /// [QUAN TRỌNG] FillGrid() — đổ checks_table từ API; count = 0 → "ĐẠT" (xanh),
    ///              ngược lại "VI PHẠM" (đỏ); dòng cuối 152/848 chỉ là THAM KHẢO
    ///              (trùng vector không phải lỗi dữ liệu — nó là lý do phải group-aware split)
    /// Phần còn lại:
    ///   CHECK_LABELS — dịch mã kiểm định sang tiếng Việt
    ///   DrawKpi()    — 5 thẻ KPI hàng trên + 2 thẻ thông tin hàng dưới (GDI+)
    ///   LoadAsync()/BuildUi() — gọi /quality + layout (khung sườn)
    /// =========================================================
    /// </remarks>
    public class DataQualityControl : UserControl
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color BLUE = Color.FromArgb(47, 111, 237);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        private static readonly System.Collections.Generic.Dictionary<string, string> CHECK_LABELS = new()
        {
            ["invalid_age"] = "Tuổi ngoài [0..120]",
            ["invalid_gender"] = "Giới tính ngoài {1, 2}",
            ["invalid_risk_scale"] = "Chỉ số ngoài thang [1..9]",
            ["invalid_level"] = "Nhãn level không hợp lệ",
            ["duplicate_patient_id"] = "Trùng patient_id",
            ["duplicate_full_row"] = "Trùng nguyên dòng",
            ["signature_label_conflicts"] = "Cùng vector đặc trưng nhưng khác nhãn",
        };

        private readonly ApiClient _api = new ApiClient();
        private QualityDto _data = new QualityDto();

        private readonly Panel _pnlKpi = new Panel();
        private readonly DataGridView _grid = new DataGridView();
        private readonly Button _btnReload = new Button();
        private readonly Label _lblStatus = new Label();
        private readonly Label _lblNote = new Label();

        public DataQualityControl()
        {
            BackColor = Color.FromArgb(238, 241, 245);
            Dock = DockStyle.Fill;
            BuildUi();
            Load += async (s, e) => await LoadAsync();
        }

        private void BuildUi()
        {
            var title = new Label
            {
                Text = "Chất lượng dữ liệu (kiểm định sau làm sạch)",
                Left = 16, Top = 12, AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold)
            };

            _btnReload.Text = "↻ Tải lại"; _btnReload.Size = new Size(100, 30);
            _btnReload.FlatStyle = FlatStyle.Flat; _btnReload.ForeColor = BLUE;
            _btnReload.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnReload.Click += async (s, e) => await LoadAsync();

            _pnlKpi.Left = 12; _pnlKpi.Top = 44; _pnlKpi.Size = new Size(1152, 180);
            _pnlKpi.BackColor = Color.Transparent;
            _pnlKpi.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            _pnlKpi.Paint += DrawKpi;

            _lblNote.Text = "Lưu ý: \"% dòng hợp lệ\" tính theo DÒNG đạt mọi ràng buộc; " +
                            "\"% ô đầy đủ\" tính theo Ô dữ liệu không bị thiếu — hai chỉ số khác nhau.";
            _lblNote.ForeColor = MUT; _lblNote.AutoSize = true;
            _lblNote.SetBounds(16, 232, 900, 18);

            _grid.Left = 12; _grid.Top = 258; _grid.Size = new Size(1152, 330);
            _grid.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _grid.ReadOnly = true; _grid.AllowUserToAddRows = false; _grid.RowHeadersVisible = false;
            _grid.BackgroundColor = Color.White; _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);

            _lblStatus.Text = "Sẵn sàng"; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.SetBounds(16, 598, 700, 20); _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, _btnReload, _pnlKpi, _lblNote, _grid, _lblStatus });
            Resize += (s, e) =>
            {
                _btnReload.Left = Width - 124; _btnReload.Top = 12;
                _pnlKpi.Width = Width - 24; _grid.Width = Width - 24;
            };
        }

        private async Task LoadAsync()
        {
            try
            {
                _lblStatus.Text = "Đang tải chỉ số chất lượng...";
                _data = await _api.GetQualityAsync();
                FillGrid();
                _pnlKpi.Invalidate();
                _lblStatus.Text = $"Đã kiểm {_data.RowCountRaw} dòng."; _lblStatus.ForeColor = MUT;
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi gọi API /quality"; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không gọi được API /quality.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void FillGrid()
        {
            _grid.Columns.Clear(); _grid.Rows.Clear();
            _grid.Columns.Add("name", "Hạng mục kiểm định");
            _grid.Columns.Add("code", "Mã kiểm định");
            _grid.Columns.Add("count", "Số vi phạm");
            _grid.Columns.Add("state", "Kết quả");
            _grid.Columns[2].FillWeight = 40; _grid.Columns[3].FillWeight = 40;

            foreach (var c in _data.Checks)
            {
                string label = CHECK_LABELS.TryGetValue(c.Name, out var vn) ? vn : c.Name;
                int r = _grid.Rows.Add(label, c.Name, c.Count, c.Count == 0 ? "ĐẠT" : "VI PHẠM");
                _grid.Rows[r].Cells[3].Style.ForeColor = c.Count == 0 ? LOW : HIGH;
                _grid.Rows[r].Cells[3].Style.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            }

            // dòng thông tin trùng vector đặc trưng (không phải lỗi — quan trọng cho ML split)
            int ri = _grid.Rows.Add("Vector 23 đặc trưng duy nhất / dòng trùng vector",
                "unique_feature_signature", $"{_data.UniqueSignature} / {_data.DuplicatedFeatureRows}", "THAM KHẢO");
            _grid.Rows[ri].Cells[3].Style.ForeColor = MUT;
        }

        private void DrawKpi(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fBig = new Font("Segoe UI", 16, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 9);

            var cards = new (string Title, string Value, Color Col)[]
            {
                ("Dòng thô (raw)", _data.RowCountRaw.ToString(), BLUE),
                ("Dòng hợp lệ (valid)", _data.RowCountValid.ToString(), LOW),
                ("Dòng không hợp lệ", _data.RowCountInvalid.ToString(), _data.RowCountInvalid == 0 ? LOW : HIGH),
                ("% dòng hợp lệ", _data.ValidRowPct.ToString("0.00") + "%", LOW),
                ("% ô đầy đủ", _data.FieldCompletenessPct.ToString("0.00") + "%", BLUE),
            };
            int w = (_pnlKpi.Width - 4 * 12) / 5;
            for (int i = 0; i < cards.Length; i++)
            {
                int x = i * (w + 12);
                var rect = new Rectangle(x, 0, w, 80);
                using var back = new SolidBrush(Color.White);
                g.FillRectangle(back, rect);
                using var pen = new Pen(Color.FromArgb(220, 224, 230));
                g.DrawRectangle(pen, rect);
                using var accent = new SolidBrush(cards[i].Col);
                g.FillRectangle(accent, x, 0, 5, 80);
                g.DrawString(cards[i].Title, fSmall, new SolidBrush(MUT), x + 14, 12);
                g.DrawString(cards[i].Value, fBig, new SolidBrush(cards[i].Col), x + 12, 34);
            }

            // hàng 2: chữ ký đặc trưng
            var info = new (string Title, string Value)[]
            {
                ("Vector đặc trưng duy nhất", _data.UniqueSignature.ToString()),
                ("Dòng trùng vector đặc trưng", _data.DuplicatedFeatureRows.ToString()),
            };
            for (int i = 0; i < info.Length; i++)
            {
                int x = i * (w + 12);
                var rect = new Rectangle(x, 92, w, 80);
                using var back = new SolidBrush(Color.White);
                g.FillRectangle(back, rect);
                using var pen = new Pen(Color.FromArgb(220, 224, 230));
                g.DrawRectangle(pen, rect);
                using var accent = new SolidBrush(MUT);
                g.FillRectangle(accent, x, 92, 5, 80);
                g.DrawString(info[i].Title, fSmall, new SolidBrush(MUT), x + 14, 104);
                g.DrawString(info[i].Value, fBig, Brushes.Black, x + 12, 126);
            }
        }
    }
}
