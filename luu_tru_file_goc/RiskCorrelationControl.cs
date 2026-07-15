using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 2 — Tab "Yếu tố nguy cơ": xếp hạng mức ảnh hưởng của từng chỉ số tới mức độ bệnh.
    /// Nguồn: GET /api/v1/correlation (aggregation MapReduce/Spark — KHÔNG dùng ML).
    /// impact = mean(High) − mean(Low). Vẽ thanh ngang xếp hạng + bảng chi tiết + xuất CSV.
    /// </summary>
    public class RiskCorrelationControl : UserControl
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color MED = Color.FromArgb(224, 160, 26);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color BLUE = Color.FromArgb(47, 111, 237);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        private readonly ApiClient _api = new ApiClient();
        private CorrelationDto _data = new CorrelationDto();

        private readonly Panel _pnlChart = new Panel();
        private readonly DataGridView _grid = new DataGridView();
        private readonly Button _btnReload = new Button();
        private readonly Button _btnExport = new Button();
        private readonly Label _lblStatus = new Label();
        private readonly Label _lblTop = new Label();

        public RiskCorrelationControl()
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
                Text = "Xếp hạng yếu tố nguy cơ (phân tích tương quan — không dùng ML)",
                Left = 16, Top = 12, AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold)
            };
            _lblTop.Left = 16; _lblTop.Top = 36; _lblTop.AutoSize = true; _lblTop.ForeColor = MUT;
            _lblTop.Font = new Font("Segoe UI", 9);

            _btnReload.Text = "↻ Tính lại"; _btnReload.Size = new Size(110, 30);
            _btnReload.FlatStyle = FlatStyle.Flat; _btnReload.ForeColor = BLUE;
            _btnReload.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnReload.Click += async (s, e) => await LoadAsync();

            _btnExport.Text = "⭳ Xuất CSV"; _btnExport.Size = new Size(110, 30);
            _btnExport.FlatStyle = FlatStyle.Flat; _btnExport.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnExport.Click += (s, e) => ExportCsv();

            _pnlChart.Left = 12; _pnlChart.Top = 66; _pnlChart.Size = new Size(560, 520);
            _pnlChart.BackColor = Color.White; _pnlChart.BorderStyle = BorderStyle.FixedSingle;
            _pnlChart.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Bottom;
            _pnlChart.Paint += DrawRanking;

            _grid.Left = 584; _grid.Top = 66; _grid.Size = new Size(580, 520);
            _grid.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _grid.ReadOnly = true; _grid.AllowUserToAddRows = false; _grid.RowHeadersVisible = false;
            _grid.BackgroundColor = Color.White; _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);

            _lblStatus.Text = "Sẵn sàng"; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.Left = 16; _lblStatus.Top = 596; _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, _lblTop, _btnReload, _btnExport, _pnlChart, _grid, _lblStatus });
            Resize += (s, e) =>
            {
                _btnReload.Left = Width - 240; _btnExport.Left = Width - 124;
                _btnReload.Top = _btnExport.Top = 12;
                _grid.Width = Width - 596;
            };
        }

        private async System.Threading.Tasks.Task LoadAsync()
        {
            try
            {
                _lblStatus.Text = "Đang tính tương quan...";
                _data = await _api.GetCorrelationAsync();
                _lblTop.Text = "Top 5 yếu tố ảnh hưởng mạnh nhất: " + string.Join(" · ", _data.TopRiskFactors);
                FillGrid();
                _pnlChart.Invalidate();
                _lblStatus.Text = $"Đã phân tích {_data.Total} bệnh nhân · {_data.Method}";
                _lblStatus.ForeColor = MUT;
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi gọi API /correlation"; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không gọi được API /correlation.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void FillGrid()
        {
            _grid.Columns.Clear(); _grid.Rows.Clear();
            _grid.Columns.Add("rank", "#");
            _grid.Columns.Add("ind", "Chỉ số");
            _grid.Columns.Add("low", "TB Low");
            _grid.Columns.Add("med", "TB Medium");
            _grid.Columns.Add("high", "TB High");
            _grid.Columns.Add("impact", "Δ (High−Low)");
            _grid.Columns.Add("pct", "% High khi chỉ số 7–9");
            _grid.Columns[0].FillWeight = 25;

            foreach (var f in _data.Factors)
            {
                int r = _grid.Rows.Add(f.Rank, f.Indicator,
                    f.MeanByLevel.GetValueOrDefault("Low").ToString("0.00"),
                    f.MeanByLevel.GetValueOrDefault("Medium").ToString("0.00"),
                    f.MeanByLevel.GetValueOrDefault("High").ToString("0.00"),
                    "+" + f.Impact.ToString("0.00"),
                    f.PctHighWhenHighValue.ToString("0.0") + "%");
                _grid.Rows[r].Cells[2].Style.ForeColor = LOW;
                _grid.Rows[r].Cells[3].Style.ForeColor = MED;
                _grid.Rows[r].Cells[4].Style.ForeColor = HIGH;
                _grid.Rows[r].Cells[5].Style.Font = new Font("Segoe UI", 9, FontStyle.Bold);
                if (f.Rank <= 5) _grid.Rows[r].Cells[1].Style.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            }
        }

        /// <summary>Thanh ngang xếp hạng theo impact = mean(High) − mean(Low).</summary>
        private void DrawRanking(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fTitle = new Font("Segoe UI", 11, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 8);
            g.DrawString("Mức ảnh hưởng: Δ = TB(High) − TB(Low)", fTitle, Brushes.Black, 14, 12);

            var top = _data.Factors.Take(12).ToList();
            if (top.Count == 0) return;
            double max = top.Max(f => f.Impact);
            if (max <= 0) return;

            int x0 = 150, barMax = _pnlChart.Width - x0 - 60, y = 46, step = (_pnlChart.Height - 70) / top.Count;
            step = Math.Min(step, 38);
            foreach (var f in top)
            {
                int w = (int)(f.Impact / max * barMax);
                Color col = f.Rank <= 3 ? HIGH : f.Rank <= 6 ? MED : BLUE;
                using var br = new SolidBrush(col);
                g.FillRectangle(br, x0, y, Math.Max(2, w), step - 12);
                // tên chỉ số (rút gọn nếu dài)
                string nm = f.Indicator.Length > 18 ? f.Indicator.Substring(0, 17) + "…" : f.Indicator;
                var sz = g.MeasureString(nm, fSmall);
                g.DrawString(nm, fSmall, Brushes.Black, x0 - 8 - sz.Width, y + 1);
                g.DrawString("+" + f.Impact.ToString("0.00"), fSmall, new SolidBrush(col), x0 + w + 6, y + 1);
                y += step;
            }
        }

        private void ExportCsv()
        {
            if (_data.Factors.Count == 0) { MessageBox.Show("Chưa có dữ liệu."); return; }
            using var dlg = new SaveFileDialog
            {
                Filter = "CSV file (*.csv)|*.csv",
                FileName = $"risk_factors_{DateTime.Now:yyyyMMdd_HHmmss}.csv"
            };
            if (dlg.ShowDialog() != DialogResult.OK) return;
            try
            {
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("rank,indicator,mean_low,mean_medium,mean_high,impact,pct_high_when_7_9");
                foreach (var f in _data.Factors)
                {
                    sb.AppendLine(string.Join(",", f.Rank, f.Indicator,
                        f.MeanByLevel.GetValueOrDefault("Low").ToString("0.00"),
                        f.MeanByLevel.GetValueOrDefault("Medium").ToString("0.00"),
                        f.MeanByLevel.GetValueOrDefault("High").ToString("0.00"),
                        f.Impact.ToString("0.00"),
                        f.PctHighWhenHighValue.ToString("0.0")));
                }
                System.IO.File.WriteAllText(dlg.FileName, sb.ToString(), System.Text.Encoding.UTF8);
                _lblStatus.Text = "Đã xuất: " + dlg.FileName; _lblStatus.ForeColor = LOW;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Không xuất được CSV.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
    }
}
