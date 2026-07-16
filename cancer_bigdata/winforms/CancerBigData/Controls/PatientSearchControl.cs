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
        private readonly Button _btnToggleColumns = new Button();

        private readonly DataGridView _grid = new DataGridView();
        private readonly Button _btnFirst = new Button();
        private readonly Button _btnPrev = new Button();
        private readonly Button _btnNext = new Button();
        private readonly Button _btnLast = new Button();
        private readonly FlowLayoutPanel _pageButtons = new FlowLayoutPanel();
        private readonly FlowLayoutPanel _pagerStrip = new FlowLayoutPanel();
        private readonly Label _lblPage = new Label();
        private readonly Label _lblStatus = new Label();
        private readonly ComboBox _cbPageSize = new ComboBox();

        private int _page = 1;
        private int _pageSize = 20;
        private int _totalPages = 1;
        private bool _showAllFields;
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
            var pnl = new Panel { Left = 12, Top = 44, Width = 1130, Height = 96, BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle,
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

            _btnToggleColumns.Text = "Hiện tất cả"; _btnToggleColumns.SetBounds(892, 50, 100, 28); _btnToggleColumns.FlatStyle = FlatStyle.Flat;
            _btnToggleColumns.ForeColor = BLUE;
            _btnToggleColumns.Click += async (s, e) =>
            {
                _showAllFields = !_showAllFields;
                _btnToggleColumns.Text = _showAllFields ? "Thu gọn" : "Hiện tất cả";
                await SearchAsync(resetPage: true);
            };
            pnl.Controls.Add(_btnToggleColumns);

            _pagerStrip.FlowDirection = FlowDirection.LeftToRight;
            _pagerStrip.WrapContents = false;
            _pagerStrip.AutoSize = true;
            _pagerStrip.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            _pagerStrip.Margin = Padding.Empty;
            _pagerStrip.SetBounds(1000, 50, 170, 28);
            pnl.Controls.Add(_pagerStrip);

            _btnFirst.Text = "⏮"; _btnFirst.Width = 38; _btnFirst.Height = 28; _btnFirst.FlatStyle = FlatStyle.Flat;
            _btnFirst.Click += async (s, e) => { if (_page > 1) { _page = 1; await SearchAsync(false); } };
            _pagerStrip.Controls.Add(_btnFirst);

            _btnPrev.Text = "◀"; _btnPrev.Width = 38; _btnPrev.Height = 28; _btnPrev.FlatStyle = FlatStyle.Flat;
            _btnPrev.Click += async (s, e) => { if (_page > 1) { _page--; await SearchAsync(false); } };
            _pagerStrip.Controls.Add(_btnPrev);

            _btnNext.Text = "▶"; _btnNext.Width = 38; _btnNext.Height = 28; _btnNext.FlatStyle = FlatStyle.Flat;
            _btnNext.Click += async (s, e) => { if (_page < _totalPages) { _page++; await SearchAsync(false); } };
            _pagerStrip.Controls.Add(_btnNext);

            _btnLast.Text = "⏭"; _btnLast.Width = 38; _btnLast.Height = 28; _btnLast.FlatStyle = FlatStyle.Flat;
            _btnLast.Click += async (s, e) => { if (_page < _totalPages) { _page = _totalPages; await SearchAsync(false); } };
            _pagerStrip.Controls.Add(_btnLast);

            // ---- bảng kết quả ----
            _grid.Left = 12; _grid.Top = 150; _grid.Size = new Size(1152, 400);
            _grid.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            _grid.ReadOnly = true; _grid.AllowUserToAddRows = false; _grid.RowHeadersVisible = false;
            _grid.BackgroundColor = Color.White; _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.AllCells;
            _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            _grid.ColumnHeadersDefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            _grid.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            _grid.DefaultCellStyle.Font = new Font("Segoe UI", 10, FontStyle.Regular);
            _grid.AllowUserToOrderColumns = true;
            _grid.RowTemplate.Height = 28;
            _grid.CellDoubleClick += (s, e) => ShowDetail(e.RowIndex);

            // ---- phân trang: hiển thị số trang ở dưới cùng ----
            _pageButtons.SetBounds(12, 560, 250, 32);
            _pageButtons.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            _pageButtons.WrapContents = false;
            _pageButtons.Margin = Padding.Empty;

            _lblPage.Text = "Trang 1 / 1"; _lblPage.SetBounds(278, 566, 130, 20); _lblPage.Font = new Font("Segoe UI", 12, FontStyle.Bold);
            _lblPage.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            var lblPageSize = new Label { Text = "Số dòng:", AutoSize = true, ForeColor = MUT };
            lblPageSize.SetBounds(720, 567, 58, 20);
            lblPageSize.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            _cbPageSize.Items.AddRange(new object[] { 20, 50, 100 });
            _cbPageSize.SelectedItem = _pageSize;
            _cbPageSize.DropDownStyle = ComboBoxStyle.DropDownList;
            _cbPageSize.SetBounds(780, 562, 62, 28);
            _cbPageSize.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            _cbPageSize.SelectedIndexChanged += async (s, e) =>
            {
                if (_cbPageSize.SelectedItem is int size && size != _pageSize)
                {
                    _pageSize = size;
                    await SearchAsync(resetPage: true);
                }
            };

            _lblStatus.Text = "Sẵn sàng"; _lblStatus.ForeColor = MUT; _lblStatus.AutoSize = true;
            _lblStatus.SetBounds(12, 600, 900, 20); _lblStatus.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;

            Controls.AddRange(new Control[] { title, pnl, _grid, _pageButtons, _lblPage, lblPageSize, _cbPageSize, _lblStatus });
            Resize += async (s, e) =>
            {
                pnl.Width = Width - 24;
                _grid.Width = Width - 24;
                _grid.Height = Math.Max(300, Height - 220);

                int estimated = EstimatePageSizeFromGrid();
                if (estimated != _pageSize)
                {
                    _pageSize = estimated;
                    _cbPageSize.SelectedItem = _pageSize;
                    await SearchAsync(resetPage: true);
                }
            };
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
                _page = Math.Max(1, Math.Min(res.Page, _totalPages));
                _lblPage.Text = $"Trang {res.Page} / {_totalPages}";
                _btnFirst.Enabled = res.Page > 1;
                _btnPrev.Enabled = res.Page > 1;
                _btnNext.Enabled = res.Page < _totalPages;
                _btnLast.Enabled = res.Page < _totalPages;
                RenderPageButtons();

                int first = res.Total == 0 ? 0 : ((res.Page - 1) * res.PageSize) + 1;
                int last = Math.Min(res.Page * res.PageSize, res.Total);
                string scope = HasActiveFilters() ? "phù hợp bộ lọc" : "trong toàn bộ dữ liệu";
                _lblStatus.Text = $"Hiển thị {first}–{last} / {res.Total} bệnh nhân {scope}. Nhấn đúp một hàng để xem chi tiết.";
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

        /// <summary>Hiển thị tối đa 5 nút số trang quanh trang hiện tại.</summary>
        private void RenderPageButtons()
        {
            _pageButtons.Controls.Clear();
            int start = Math.Max(1, _page - 2);
            int end = Math.Min(_totalPages, start + 4);
            start = Math.Max(1, end - 4);

            for (int pageNumber = start; pageNumber <= end; pageNumber++)
            {
                int targetPage = pageNumber;
                var button = new Button
                {
                    Text = targetPage.ToString(),
                    Width = 42,
                    Height = 30,
                    Margin = new Padding(0, 0, 6, 0),
                    FlatStyle = FlatStyle.Flat,
                    BackColor = targetPage == _page ? BLUE : Color.White,
                    ForeColor = targetPage == _page ? Color.White : Color.FromArgb(45, 52, 61),
                    Enabled = targetPage != _page
                };
                button.Click += async (s, e) =>
                {
                    _page = targetPage;
                    await SearchAsync(resetPage: false);
                };
                _pageButtons.Controls.Add(button);
            }
        }

        private bool HasActiveFilters()
            => _cbLevel.SelectedIndex > 0
               || _cbGender.SelectedIndex > 0
               || _numAgeMin.Value > 0
               || _numAgeMax.Value < 120
               || _cbFeature.SelectedIndex > 0;

        private void FillGrid(List<Dictionary<string, object>> items)
        {
            _grid.Columns.Clear();
            _grid.Rows.Clear();

            var visibleColumns = _showAllFields
                ? GetVisibleColumns(items)
                : GetCompactColumns(items);

            foreach (var key in visibleColumns)
            {
                _grid.Columns.Add(key, FormatColumnHeader(key));
            }

            foreach (var it in items)
            {
                var rowValues = new object[visibleColumns.Length];
                for (int i = 0; i < visibleColumns.Length; i++)
                {
                    rowValues[i] = Get(it, visibleColumns[i]);
                }

                int row = _grid.Rows.Add(rowValues);
                _grid.Rows[row].Tag = it;

                int levelIndex = Array.IndexOf(visibleColumns, "level");
                if (levelIndex >= 0)
                {
                    var lv = Get(it, "level");
                    _grid.Rows[row].Cells[levelIndex].Style.ForeColor = lv == "High" ? HIGH : lv == "Medium" ? MED : LOW;
                }
            }
        }

        private string[] GetCompactColumns(List<Dictionary<string, object>> items)
        {
            var baseColumns = new[] { "patient_id", "age", "gender", "level" };
            var selectedFeature = _cbFeature.SelectedIndex > 0 ? _cbFeature.SelectedItem?.ToString() : null;
            var visible = new List<string>(baseColumns);
            if (!string.IsNullOrWhiteSpace(selectedFeature) && !visible.Contains(selectedFeature))
                visible.Add(selectedFeature);
            return visible.ToArray();
        }

        private static string[] GetVisibleColumns(List<Dictionary<string, object>> items)
        {
            var orderedKeys = new List<string>();
            foreach (var it in items)
            {
                foreach (var key in it.Keys)
                {
                    if (ShouldHideColumn(key) || orderedKeys.Contains(key)) continue;
                    orderedKeys.Add(key);
                }
            }

            var preferredOrder = new[] { "patient_id", "age", "gender", "level" };
            foreach (var key in preferredOrder)
            {
                if (orderedKeys.Contains(key))
                {
                    orderedKeys.Remove(key);
                    orderedKeys.Insert(0, key);
                }
            }

            return orderedKeys.ToArray();
        }

        private static bool ShouldHideColumn(string key)
            => key == "created_at" || key == "updated_at" || key == "dataset_version" || key == "feature_signature";

        private static string FormatColumnHeader(string key)
        {
            if (string.IsNullOrWhiteSpace(key)) return "Value";
            return key
                .Replace("_", " ")
                .Split(' ')
                .Select(word => word.Length == 0 ? word : char.ToUpperInvariant(word[0]) + word.Substring(1))
                .Aggregate(string.Empty, (current, word) => current + (current.Length == 0 ? word : " " + word));
        }

        private int EstimatePageSizeFromGrid()
        {
            int usableHeight = Math.Max(250, _grid.Height - 18);
            int rowHeight = Math.Max(24, _grid.RowTemplate.Height);
            return Math.Max(20, usableHeight / rowHeight);
        }

        private static string Get(Dictionary<string, object> d, string k)
            => d != null && d.TryGetValue(k, out var v) && v != null ? v.ToString() : "";

        private void ShowDetail(int rowIndex)
        {
            if (rowIndex < 0 || rowIndex >= _grid.Rows.Count) return;
            if (!(_grid.Rows[rowIndex].Tag is Dictionary<string, object> p)) return;
            var lines = p.Where(kv => kv.Key != "_id" && !ShouldHideColumn(kv.Key))
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