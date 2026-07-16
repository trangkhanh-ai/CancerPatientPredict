using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 2/5 — Tab "Thống kê": KPI + donut phân bố mức độ + biểu đồ cột trung bình
    /// chỉ số theo mức độ + bảng phân bố nhóm tuổi/giới tính. Nguồn: GET /api/v1/stats.
    /// Biểu đồ vẽ bằng GDI+ (OnPaint), không dùng thư viện ngoài.
    /// </summary>
    public class StatsDashboardControl : UserControl
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color MED = Color.FromArgb(224, 160, 26);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color BLUE = Color.FromArgb(47, 111, 237);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        private readonly ApiClient _api = new ApiClient();
        private StatsDto _data = new StatsDto();

        private readonly Panel _pnlKpi = new Panel();
        private readonly Panel _pnlDonut = new Panel();
        private readonly Panel _pnlBars = new Panel();
        private readonly CheckedListBox _featureSelector = new CheckedListBox();
        private readonly DataGridView _grid = new DataGridView();
        private readonly Button _btnReload = new Button();
        private readonly Label _lblStatus = new Label();

        public StatsDashboardControl()
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
                Text = "Thống kê tổng quan (MapReduce / MongoDB aggregation)",
                Left = 16, Top = 12, AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold)
            };

            _btnReload.Text = "↻ Tải lại"; _btnReload.Size = new Size(100, 30);
            _btnReload.FlatStyle = FlatStyle.Flat; _btnReload.ForeColor = BLUE;
            _btnReload.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnReload.Click += async (s, e) => await LoadAsync();

            _pnlKpi.Left = 12; _pnlKpi.Top = 44; _pnlKpi.Size = new Size(1152, 84);
            _pnlKpi.BackColor = Color.Transparent;
            _pnlKpi.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            _pnlKpi.Paint += DrawKpi;

            _pnlDonut.Left = 12; _pnlDonut.Top = 140; _pnlDonut.Size = new Size(370, 340);
            _pnlDonut.BackColor = Color.White; _pnlDonut.BorderStyle = BorderStyle.FixedSingle;
            _pnlDonut.Paint += DrawDonut;

            _pnlBars.Left = 394; _pnlBars.Top = 140; _pnlBars.Size = new Size(770, 340);
            _pnlBars.BackColor = Color.White; _pnlBars.BorderStyle = BorderStyle.FixedSingle;
            _pnlBars.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            _pnlBars.Paint += DrawBars;

            _featureSelector.Left = 394; _featureSelector.Top = 112; _featureSelector.Width = 770; _featureSelector.Height = 24;
            _featureSelector.CheckOnClick = true;
            _featureSelector.BorderStyle = BorderStyle.FixedSingle;
            _featureSelector.ItemCheck += (s, e) => _pnlBars.Invalidate();

            _grid.Left = 12; _grid.Top = 500; _grid.Size = new Size(1152, 230);
            _grid.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _grid.ReadOnly = true; _grid.AllowUserToAddRows = false; _grid.RowHeadersVisible = false;
            _grid.BackgroundColor = Color.White; _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.AllCells;
            _grid.RowTemplate.Height = 28;
            _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            _grid.ColumnHeadersDefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            _grid.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;

            _lblStatus.Text = "Sẵn sàng"; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.SetBounds(16, 610, 700, 20); _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, _btnReload, _pnlKpi, _pnlDonut, _featureSelector, _pnlBars, _grid, _lblStatus });
            Resize += (s, e) =>
            {
                _btnReload.Left = Width - 124; _btnReload.Top = 12;
                _pnlKpi.Width = Width - 24;
                _pnlDonut.Width = Math.Max(320, (Width - 48) / 3);
                _featureSelector.Width = Width - 420;
                _pnlBars.Left = _pnlDonut.Right + 12;
                _pnlBars.Width = Width - _pnlBars.Left - 12;
                _grid.Width = Width - 24;
                _grid.Height = Math.Max(220, Height - 300);
            };
        }

        private async Task LoadAsync()
        {
            try
            {
                _lblStatus.Text = "Đang tải thống kê...";
                _data = await _api.GetStatsAsync();
                FillGrid();
                PopulateFeatureSelector();
                _pnlKpi.Invalidate(); _pnlDonut.Invalidate(); _pnlBars.Invalidate();
                _lblStatus.Text = $"Đã thống kê {_data.Total} bệnh nhân."; _lblStatus.ForeColor = MUT;
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi gọi API /stats"; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không gọi được API /stats.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void FillGrid()
        {
            _grid.Columns.Clear(); _grid.Rows.Clear();
            _grid.Columns.Add("group", "Phân bố");
            foreach (var k in _data.AgeGroupDistribution.Keys)
                _grid.Columns.Add("ag_" + k, k);

            int r1 = _grid.Rows.Add();
            _grid.Rows[r1].Cells[0].Value = "Nhóm tuổi (số BN)";
            int i = 1;
            foreach (var kv in _data.AgeGroupDistribution)
                _grid.Rows[r1].Cells[i++].Value = kv.Value;

            int r2 = _grid.Rows.Add();
            _grid.Rows[r2].Cells[0].Value = "Giới tính";
            _grid.Rows[r2].Cells[1].Value = string.Join("   ·   ",
                _data.GenderDistribution.Select(kv => $"{kv.Key}: {kv.Value}"));

            _grid.Rows[0].Cells[0].Style.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            _grid.Rows[1].Cells[0].Style.Font = new Font("Segoe UI", 9, FontStyle.Bold);
        }

        private void PopulateFeatureSelector()
        {
            _featureSelector.Items.Clear();
            foreach (var feature in _data.ChartIndicators)
            {
                _featureSelector.Items.Add(feature, true);
            }
        }

        // ---------- KPI cards ----------
        private void DrawKpi(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fBig = new Font("Segoe UI", 16, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 9);

            var cards = new (string Title, string Value, Color Col)[]
            {
                ("Tổng bệnh nhân", _data.Total.ToString(), BLUE),
                ("Mức độ High", Get(_data.LevelDistribution, "High"), HIGH),
                ("Mức độ Medium", Get(_data.LevelDistribution, "Medium"), MED),
                ("Mức độ Low", Get(_data.LevelDistribution, "Low"), LOW),
            };
            int w = (_pnlKpi.Width - 3 * 12) / 4;
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
        }

        private static string Get(System.Collections.Generic.Dictionary<string, int> d, string k)
            => d != null && d.TryGetValue(k, out var v) ? v.ToString() : "0";

        // ---------- Donut phân bố mức độ ----------
        private void DrawDonut(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fTitle = new Font("Segoe UI", 11, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 9);
            g.DrawString("Phân bố mức độ", fTitle, Brushes.Black, 14, 12);

            int total = _data.LevelDistribution.Values.Sum();
            if (total == 0) return;

            var order = new[] { ("Low", LOW), ("Medium", MED), ("High", HIGH) };
            var rect = new Rectangle(60, 60, 180, 180);
            float start = -90f;
            foreach (var (lv, col) in order)
            {
                int n = _data.LevelDistribution.TryGetValue(lv, out var v) ? v : 0;
                float sweep = 360f * n / total;
                using var br = new SolidBrush(col);
                g.FillPie(br, rect, start, sweep);
                start += sweep;
            }
            // lỗ donut
            using (var hole = new SolidBrush(Color.White))
                g.FillEllipse(hole, 105, 105, 90, 90);
            g.DrawString(total.ToString(), fTitle, Brushes.Black, 128, 138);

            // chú giải
            int ly = 66;
            foreach (var (lv, col) in order)
            {
                int n = _data.LevelDistribution.TryGetValue(lv, out var v) ? v : 0;
                using var br = new SolidBrush(col);
                g.FillRectangle(br, 262, ly, 14, 14);
                g.DrawString($"{lv}: {n} ({100.0 * n / total:0.0}%)", fSmall, Brushes.Black, 282, ly - 1);
                ly += 26;
            }
        }

        // ---------- Cột trung bình chỉ số theo mức độ ----------
        private void DrawBars(object sender, PaintEventArgs e)
        {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using var fTitle = new Font("Segoe UI", 11, FontStyle.Bold);
            using var fSmall = new Font("Segoe UI", 8);
            using var fValue = new Font("Segoe UI", 7, FontStyle.Bold);
            g.DrawString("Trung bình chỉ số theo mức độ (thang 1–9)", fTitle, Brushes.Black, 14, 12);

            var inds = _data.ChartIndicators
                .Where(c => _featureSelector.Items.Contains(c) && _featureSelector.GetItemChecked(_featureSelector.Items.IndexOf(c)))
                .Where(c => _data.AvgByLevel.ContainsKey(c))
                .ToList();
            if (inds.Count == 0) return;

            var order = new[] { ("Low", LOW), ("Medium", MED), ("High", HIGH) };
            const double maxVal = 9.0;
            int x0 = 40, y1 = _pnlBars.Height - 46, chartH = y1 - 56;
            int groupW = (_pnlBars.Width - x0 - 20) / inds.Count;
            int barW = Math.Min(26, (groupW - 24) / 3);

            using (var pen = new Pen(Color.FromArgb(220, 224, 230)))
                for (int v = 0; v <= 9; v += 3)
                {
                    int y = y1 - (int)(chartH * v / maxVal);
                    g.DrawLine(pen, x0 - 4, y, _pnlBars.Width - 16, y);
                    g.DrawString(v.ToString(), fSmall, new SolidBrush(MUT), 16, y - 7);
                }
            int lx = _pnlBars.Width - 250;
            foreach (var (lv, col) in order)
            {
                using var br = new SolidBrush(col);
                g.FillRectangle(br, lx, 16, 12, 12);
                g.DrawString(lv, fSmall, Brushes.Black, lx + 16, 15);
                lx += 80;
            }

            for (int i = 0; i < inds.Count; i++)
            {
                int gx = x0 + i * groupW + 8;
                for (int j = 0; j < order.Length; j++)
                {
                    var (lv, col) = order[j];
                    double v = _data.AvgByLevel[inds[i]].TryGetValue(lv, out var mv) ? mv : 0.0;
                    int h = (int)(chartH * v / maxVal);
                    using var br = new SolidBrush(col);
                    int barX = gx + j * (barW + 4);
                    int barY = y1 - h;
                    g.FillRectangle(br, barX, barY, barW, h);
                    g.DrawString(v.ToString("0.0"), fValue, Brushes.Black, barX - 2, Math.Max(18, barY - 18));
                }
                string nm = inds[i].Length > 14 ? inds[i].Substring(0, 13) + "…" : inds[i];
                g.DrawString(nm, fSmall, Brushes.Black, gx - 4, y1 + 6);
            }
        }
    }
}
