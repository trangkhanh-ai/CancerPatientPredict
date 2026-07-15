using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 2/5 — Tab "Danh sách bệnh nhân": tìm kiếm + lọc + sắp xếp + phân trang + xuất CSV.
    /// Đáp ứng yêu cầu đề bài: "thống kê và tìm kiếm bệnh nhân dựa trên bộ lọc là từng chỉ số".
    /// Gọi GET /api/v1/patients (whitelist ở backend) và GET /api/v1/patients/export.
    /// </summary>
    public class PatientSearchControl : UserControl
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color MED = Color.FromArgb(224, 160, 26);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color BLUE = Color.FromArgb(47, 111, 237);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        // 21 chỉ số có thể lọc (khớp whitelist backend)
        private static readonly string[] INDICATORS = {
            "air_pollution","alcohol_use","dust_allergy","occupational_hazards","genetic_risk",
            "chronic_lung_disease","balanced_diet","obesity","smoking","passive_smoker","chest_pain",
            "coughing_of_blood","fatigue","weight_loss","shortness_of_breath","wheezing",
            "swallowing_difficulty","clubbing_of_finger_nails","frequent_cold","dry_cough","snoring" };

        private readonly ApiClient _api = new ApiClient();

        private readonly ComboBox _cbLevel = new ComboBox();
        private readonly ComboBox _cbGender = new ComboBox();
        private readonly NumericUpDown _numAgeMin = new NumericUpDown();
        private readonly NumericUpDown _numAgeMax = new NumericUpDown();
        private readonly ComboBox _cbFeature = new ComboBox();
        private readonly ComboBox _cbOperator = new ComboBox();
        private readonly NumericUpDown _numValue = new NumericUpDown();
        private readonly NumericUpDown _numValue2 = new NumericUpDown();
        private readonly ComboBox _cbSort = new ComboBox();
        private readonly ComboBox _cbSortDir = new ComboBox();
        private readonly Button _btnSearch = new Button();
        private readonly Button _btnReset = new Button();
        private readonly Button _btnExport = new Button();

        private readonly DataGridView _grid = new DataGridView();
        private readonly Button _btnPrev = new Button();
        private readonly Button _btnNext = new Button();
        private readonly Label _lblPage = new Label();
        private readonly Label _lblStatus = new Label();

        private int _page = 1;
        private int _pageSize = 20;
        private int _totalPages = 1;
        private CancellationTokenSource _cts;   // huỷ request cũ khi bấm liên tục

        public PatientSearchControl()
        {
            BackColor = Color.FromArgb(238, 241, 245);
            Dock = DockStyle.Fill;
            BuildUi();
            Load += async (s, e) => await SearchAsync(resetPage: true);
        }

        private void BuildUi()
        {
            var title = new Label { Text = "Tìm kiếm & lọc bệnh nhân", Left = 16, Top = 12, AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold) };

            // ---- hàng 1: level / gender / tuổi ----
            var pnl = new Panel { Left = 12, Top = 44, Height = 96, BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle,
                                  Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };

            AddLabel(pnl, "Mức độ:", 12, 12);
            _cbLevel.Items.AddRange(new object[] { "(Tất cả)", "Low", "Medium", "High" });
            _cbLevel.SelectedIndex = 0; _cbLevel.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbLevel.SetBounds(70, 8, 110, 24); pnl.Controls.Add(_cbLevel);

            AddLabel(pnl, "Giới tính:", 196, 12);
            _cbGender.Items.AddRange(new object[] { "(Tất cả)", "Nam", "Nữ" });
            _cbGender.SelectedIndex = 0; _cbGender.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbGender.SetBounds(260, 8, 100, 24); pnl.Controls.Add(_cbGender);

            AddLabel(pnl, "Tuổi từ:", 376, 12);
            _numAgeMin.SetBounds(432, 8, 60, 24); _numAgeMin.Minimum = 0; _numAgeMin.Maximum = 120; _numAgeMin.Value = 0;
            pnl.Controls.Add(_numAgeMin);
            AddLabel(pnl, "đến:", 500, 12);
            _numAgeMax.SetBounds(538, 8, 60, 24); _numAgeMax.Minimum = 0; _numAgeMax.Maximum = 120; _numAgeMax.Value = 120;
            pnl.Controls.Add(_numAgeMax);

            AddLabel(pnl, "Sắp xếp:", 616, 12);
            _cbSort.Items.Add("(mặc định)");
            _cbSort.Items.AddRange(new object[] { "patient_id", "age", "level", "gender" });
            _cbSort.Items.AddRange(INDICATORS);
            _cbSort.SelectedIndex = 0; _cbSort.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbSort.SetBounds(676, 8, 150, 24); pnl.Controls.Add(_cbSort);
            _cbSortDir.Items.AddRange(new object[] { "Tăng dần", "Giảm dần" });
            _cbSortDir.SelectedIndex = 0; _cbSortDir.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbSortDir.SetBounds(834, 8, 100, 24); pnl.Controls.Add(_cbSortDir);

            // ---- hàng 2: lọc theo TỪNG CHỈ SỐ ----
            AddLabel(pnl, "Lọc theo chỉ số:", 12, 56);
            _cbFeature.Items.Add("(không lọc)");
            _cbFeature.Items.AddRange(INDICATORS);
            _cbFeature.SelectedIndex = 0; _cbFeature.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbFeature.SetBounds(110, 52, 170, 24); pnl.Controls.Add(_cbFeature);

            _cbOperator.Items.AddRange(new object[] { "=", "≥", "≤", "trong khoảng" });
            _cbOperator.SelectedIndex = 1; _cbOperator.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbOperator.SetBounds(288, 52, 120, 24); pnl.Controls.Add(_cbOperator);
            _cbOperator.SelectedIndexChanged += (s, e) => _numValue2.Visible = _cbOperator.SelectedIndex == 3;

            _numValue.SetBounds(416, 52, 60, 24); _numValue.Minimum = 1; _numValue.Maximum = 9; _numValue.Value = 7;
            pnl.Controls.Add(_numValue);
            _numValue2.SetBounds(484, 52, 60, 24); _numValue2.Minimum = 1; _numValue2.Maximum = 9; _numValue2.Value = 9;
            _numValue2.Visible = false; pnl.Controls.Add(_numValue2);

            _btnSearch.Text = "🔍 Tìm kiếm"; _btnSearch.SetBounds(568, 50, 110, 28);
            _btnSearch.FlatStyle = FlatStyle.Flat; _btnSearch.BackColor = BLUE; _btnSearch.ForeColor = Color.White;
            _btnSearch.Click += async (s, e) => await SearchAsync(resetPage: true);
            pnl.Controls.Add(_btnSearch);

            _btnReset.Text = "Xoá lọc"; _btnReset.SetBounds(686, 50, 90, 28); _btnReset.FlatStyle = FlatStyle.Flat;
            _btnReset.Click += async (s, e) => { ResetFilters(); await SearchAsync(resetPage: true); };
            pnl.Controls.Add(_btnReset);

            _btnExport.Text = "⭳ Xuất CSV"; _btnExport.SetBounds(784, 50, 110, 28); _btnExport.FlatStyle = FlatStyle.Flat;
            _btnExport.ForeColor = BLUE;
            _btnExport.Click += async (s, e) => await ExportAsync();
            pnl.Controls.Add(_btnExport);

            // ---- bảng kết quả ----
            _grid.Left = 12; _grid.Top = 150; _grid.Size = new Size(1152, 400);
            _grid.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _grid.ReadOnly = true; _grid.AllowUserToAddRows = false; _grid.RowHeadersVisible = false;
            _grid.BackgroundColor = Color.White; _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            _grid.CellDoubleClick += (s, e) => ShowDetail(e.RowIndex);

            // ---- phân trang ----
            _btnPrev.Text = "◀ Trang trước"; _btnPrev.SetBounds(12, 560, 110, 28); _btnPrev.FlatStyle = FlatStyle.Flat;
            _btnPrev.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            _btnPrev.Click += async (s, e) => { if (_page > 1) { _page--; await SearchAsync(false); } };

            _lblPage.Text = "Trang 1 / 1"; _lblPage.SetBounds(132, 566, 120, 20); _lblPage.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            _lblPage.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            _btnNext.Text = "Trang sau ▶"; _btnNext.SetBounds(256, 560, 110, 28); _btnNext.FlatStyle = FlatStyle.Flat;
            _btnNext.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            _btnNext.Click += async (s, e) => { if (_page < _totalPages) { _page++; await SearchAsync(false); } };

            _lblStatus.Text = "Sẵn sàng"; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.SetBounds(390, 566, 400, 20); _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, pnl, _grid, _btnPrev, _lblPage, _btnNext, _lblStatus });
            Resize += (s, e) => { pnl.Width = Width - 24; _grid.Width = Width - 24; };
        }

        private static void AddLabel(Control parent, string text, int x, int y)
            => parent.Controls.Add(new Label { Text = text, Left = x, Top = y, AutoSize = true, ForeColor = Color.FromArgb(60, 66, 74) });

        private void ResetFilters()
        {
            _cbLevel.SelectedIndex = 0; _cbGender.SelectedIndex = 0;
            _numAgeMin.Value = 0; _numAgeMax.Value = 120;
            _cbFeature.SelectedIndex = 0; _cbOperator.SelectedIndex = 1;
            _numValue.Value = 7; _cbSort.SelectedIndex = 0; _cbSortDir.SelectedIndex = 0;
        }

        /// <summary>Dựng query string khớp whitelist của backend.</summary>
        private PatientQuery BuildQuery()
        {
            var q = new PatientQuery { Page = _page, PageSize = _pageSize };
            if (_cbLevel.SelectedIndex > 0) q.Level = _cbLevel.SelectedItem.ToString();
            if (_cbGender.SelectedIndex > 0) q.Gender = _cbGender.SelectedIndex;   // 1=Nam, 2=Nữ
            if (_numAgeMin.Value > 0) q.AgeMin = (int)_numAgeMin.Value;
            if (_numAgeMax.Value < 120) q.AgeMax = (int)_numAgeMax.Value;
            if (_cbFeature.SelectedIndex > 0)
            {
                q.Feature = _cbFeature.SelectedItem.ToString();
                switch (_cbOperator.SelectedIndex)
                {
                    case 0: q.Operator = "eq"; q.Value = (int)_numValue.Value; break;
                    case 1: q.Operator = "gte"; q.Value = (int)_numValue.Value; break;
                    case 2: q.Operator = "lte"; q.Value = (int)_numValue.Value; break;
                    case 3:
                        q.Operator = "between";
                        q.MinValue = (int)Math.Min(_numValue.Value, _numValue2.Value);
                        q.MaxValue = (int)Math.Max(_numValue.Value, _numValue2.Value);
                        break;
                }
            }
            if (_cbSort.SelectedIndex > 0)
            {
                q.SortBy = _cbSort.SelectedItem.ToString();
                q.SortDir = _cbSortDir.SelectedIndex == 1 ? "desc" : "asc";
            }
            return q;
        }

        private async Task SearchAsync(bool resetPage)
        {
            if (resetPage) _page = 1;
            _cts?.Cancel();
            _cts = new CancellationTokenSource();
            var token = _cts.Token;
            try
            {
                _lblStatus.Text = "Đang tìm..."; _lblStatus.ForeColor = MUT;
                _btnSearch.Enabled = false;
                var res = await _api.SearchPatientsAsync(BuildQuery(), token);
                if (token.IsCancellationRequested) return;

                FillGrid(res.Items);
                _totalPages = Math.Max(1, res.TotalPages);
                _lblPage.Text = $"Trang {res.Page} / {_totalPages}";
                _btnPrev.Enabled = res.Page > 1;
                _btnNext.Enabled = res.Page < _totalPages;
                _lblStatus.Text = $"Tìm thấy {res.Total} bệnh nhân ({_pageSize}/trang). Nhấn đúp một hàng để xem chi tiết.";
            }
            catch (OperationCanceledException) { /* bỏ qua request cũ */ }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi gọi API"; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không gọi được API /patients.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            finally { _btnSearch.Enabled = true; }
        }

        private void FillGrid(List<Dictionary<string, object>> items)
        {
            _grid.Columns.Clear(); _grid.Rows.Clear();
            _grid.Columns.Add("patient_id", "Mã BN");
            _grid.Columns.Add("age", "Tuổi");
            _grid.Columns.Add("gender", "Giới tính");
            _grid.Columns.Add("level", "Mức độ");
            // thêm cột chỉ số đang lọc để người dùng thấy giá trị
            string extra = _cbFeature.SelectedIndex > 0 ? _cbFeature.SelectedItem.ToString() : null;
            if (extra != null) _grid.Columns.Add(extra, extra);

            foreach (var it in items)
            {
                string lv = Get(it, "level");
                string gd = Get(it, "gender") == "1" ? "Nam" : "Nữ";
                int row = extra != null
                    ? _grid.Rows.Add(Get(it, "patient_id"), Get(it, "age"), gd, lv, Get(it, extra))
                    : _grid.Rows.Add(Get(it, "patient_id"), Get(it, "age"), gd, lv);
                _grid.Rows[row].Cells[3].Style.ForeColor = lv == "High" ? HIGH : lv == "Medium" ? MED : LOW;
                _grid.Rows[row].Tag = it;
            }
        }

        private static string Get(Dictionary<string, object> d, string k)
            => d != null && d.TryGetValue(k, out var v) && v != null ? v.ToString() : "";

        private void ShowDetail(int rowIndex)
        {
            if (rowIndex < 0 || rowIndex >= _grid.Rows.Count) return;
            if (_grid.Rows[rowIndex].Tag is not Dictionary<string, object> p) return;
            var lines = p.Where(kv => kv.Key != "_id")
                         .Select(kv => $"{kv.Key}: {kv.Value}");
            MessageBox.Show(string.Join(Environment.NewLine, lines),
                $"Chi tiết bệnh nhân {Get(p, "patient_id")}", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private async Task ExportAsync()
        {
            using var dlg = new SaveFileDialog
            {
                Filter = "CSV file (*.csv)|*.csv",
                FileName = $"patients_{DateTime.Now:yyyyMMdd_HHmmss}.csv"
            };
            if (dlg.ShowDialog() != DialogResult.OK) return;
            try
            {
                _lblStatus.Text = "Đang xuất CSV...";
                await _api.ExportPatientsCsvAsync(BuildQuery(), dlg.FileName);
                _lblStatus.Text = "Đã xuất: " + dlg.FileName;
                _lblStatus.ForeColor = LOW;
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Lỗi xuất CSV"; _lblStatus.ForeColor = HIGH;
                MessageBox.Show("Không xuất được CSV.\n" + ex.Message, "Lỗi",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
    }
}
