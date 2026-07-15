using System.Data;
using System.Text.Json.Nodes;

namespace CancerUI;

public class MainForm : Form
{
    // ---- palette (dark theme) ----
    static readonly Color Bg = Color.FromArgb(30, 30, 46);
    static readonly Color Panel = Color.FromArgb(37, 37, 54);
    static readonly Color Card = Color.FromArgb(45, 45, 66);
    static readonly Color Side = Color.FromArgb(24, 24, 37);
    static readonly Color Fg = Color.FromArgb(230, 230, 240);
    static readonly Color Muted = Color.FromArgb(150, 150, 170);
    static readonly Color Accent = Color.FromArgb(116, 122, 255);
    static readonly Color High = Color.FromArgb(229, 57, 53);
    static readonly Color Medium = Color.FromArgb(251, 140, 0);
    static readonly Color Low = Color.FromArgb(67, 160, 71);

    // 23 đặc trưng: key -> nhãn tiếng Việt (đúng thứ tự schema)
    static readonly (string Key, string Label)[] Features =
    {
        ("age","Tuổi"), ("gender","Giới tính (1=Nam,2=Nữ)"),
        ("air_pollution","Ô nhiễm không khí"), ("alcohol_use","Rượu bia"),
        ("dust_allergy","Dị ứng bụi"), ("occupational_hazards","Nguy cơ nghề nghiệp"),
        ("genetic_risk","Yếu tố di truyền"), ("chronic_lung_disease","Bệnh phổi mãn tính"),
        ("balanced_diet","Chế độ ăn cân bằng"), ("obesity","Béo phì"),
        ("smoking","Hút thuốc"), ("passive_smoker","Hút thuốc thụ động"),
        ("chest_pain","Đau ngực"), ("coughing_of_blood","Ho ra máu"),
        ("fatigue","Mệt mỏi"), ("weight_loss","Sụt cân"),
        ("shortness_of_breath","Khó thở"), ("wheezing","Thở khò khè"),
        ("swallowing_difficulty","Khó nuốt"), ("clubbing_of_finger_nails","Ngón tay dùi trống"),
        ("frequent_cold","Cảm lạnh thường xuyên"), ("dry_cough","Ho khan"), ("snoring","Ngáy"),
    };
    static readonly string[] ScaleCols = Features.Select(f => f.Key)
        .Where(k => k != "age" && k != "gender").ToArray();

    ApiClient _api = new("http://localhost:8000/api/v1");
    readonly Panel _content = new() { Dock = DockStyle.Fill, BackColor = Bg, Padding = new Padding(24) };
    readonly Label _status = new() { Dock = DockStyle.Bottom, Height = 26, ForeColor = Muted,
        TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(10, 0, 0, 0), Text = "  ●  chưa kết nối" };
    readonly TextBox _baseUrl;

    public MainForm()
    {
        Text = "Hệ thống dự đoán nguy cơ ung thư — Big Data (WinForms)";
        Size = new Size(1180, 760);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Bg;
        Font = new Font("Segoe UI", 9.5f);

        // ----- sidebar -----
        var side = new Panel { Dock = DockStyle.Left, Width = 200, BackColor = Side };
        var title = new Label { Text = "  🩺  Cancer BigData", Dock = DockStyle.Top, Height = 60,
            ForeColor = Fg, Font = new Font("Segoe UI Semibold", 12f), TextAlign = ContentAlignment.MiddleLeft };

        _baseUrl = new TextBox { Text = _api.BaseUrl, Dock = DockStyle.Bottom,
            BackColor = Card, ForeColor = Fg, BorderStyle = BorderStyle.FixedSingle };
        var lblApi = new Label { Text = "API base URL:", Dock = DockStyle.Bottom, Height = 20, ForeColor = Muted };

        var navButtons = new[]
        {
            MakeNav("📊  Bảng điều khiển", ShowDashboard),
            MakeNav("🔮  Dự đoán", ShowPredict),
            MakeNav("👥  Bệnh nhân", ShowPatients),
            MakeNav("✅  Chất lượng dữ liệu", ShowQuality),
        };
        // add in reverse for Dock=Top stacking order
        side.Controls.Add(_baseUrl);
        side.Controls.Add(lblApi);
        var navHost = new Panel { Dock = DockStyle.Fill, BackColor = Side };
        foreach (var b in navButtons.Reverse()) navHost.Controls.Add(b);
        side.Controls.Add(navHost);
        side.Controls.Add(title);

        Controls.Add(_content);
        Controls.Add(side);
        Controls.Add(_status);

        Load += async (_, _) => { await RefreshStatus(); ShowDashboard(); };
    }

    Button MakeNav(string text, Action onClick)
    {
        var b = new Button { Text = text, Dock = DockStyle.Top, Height = 46, ForeColor = Fg,
            BackColor = Side, FlatStyle = FlatStyle.Flat, TextAlign = ContentAlignment.MiddleLeft,
            Padding = new Padding(14, 0, 0, 0), Font = new Font("Segoe UI", 10.5f) };
        b.FlatAppearance.BorderSize = 0;
        b.FlatAppearance.MouseOverBackColor = Card;
        b.Click += (_, _) =>
        {
            _api.BaseUrl = _baseUrl.Text.TrimEnd('/');
            try { onClick(); } catch (Exception ex) { ShowError(ex); }
        };
        return b;
    }

    // ================= STATUS =================
    async Task RefreshStatus()
    {
        try
        {
            var h = await _api.GetAsync("/health");
            string mongo = h?["mongodb"]?.ToString() ?? "?";
            bool model = h?["model_loaded"]?.GetValue<bool>() ?? false;
            _status.ForeColor = Low;
            _status.Text = $"  ● API OK   |   MongoDB: {mongo}   |   Model: {(model ? "đã nạp" : "CHƯA nạp")}   |   {_api.BaseUrl}";
        }
        catch (Exception ex)
        {
            _status.ForeColor = High;
            _status.Text = $"  ● KHÔNG kết nối được API ({_api.BaseUrl}) — {ex.Message.Split('\n')[0]}";
        }
    }

    // ================= DASHBOARD =================
    async void ShowDashboard()
    {
        _content.Controls.Clear();
        _content.Controls.Add(Header("Bảng điều khiển"));
        var loading = Loading();
        _content.Controls.Add(loading);
        await RefreshStatus();

        JsonNode? stats = null, model = null, quality = null;
        try { stats = await _api.GetAsync("/stats"); } catch { }
        try { model = await _api.GetAsync("/model"); } catch { }
        try { quality = await _api.GetAsync("/quality"); } catch { }
        _content.Controls.Remove(loading);

        int total = stats?["total"]?.GetValue<int>() ?? 0;
        var lvl = stats?["level_distribution"];
        int high = lvl?["High"]?.GetValue<int>() ?? 0;
        int med = lvl?["Medium"]?.GetValue<int>() ?? 0;
        int low = lvl?["Low"]?.GetValue<int>() ?? 0;
        double acc = model?["metrics"]?["accuracy"]?.GetValue<double>() ?? 0;
        string mrAt = stats?["mapreduce_run_at"]?.ToString() ?? "—";

        var cards = new FlowLayoutPanel { Location = new Point(24, 70), Size = new Size(1080, 120), BackColor = Bg };
        cards.Controls.Add(KpiCard("Tổng bệnh nhân", total.ToString("N0"), Accent));
        cards.Controls.Add(KpiCard("Nguy cơ CAO", high.ToString("N0"), High));
        cards.Controls.Add(KpiCard("Độ chính xác model", acc > 0 ? acc.ToString("P1") : "—", Low));
        cards.Controls.Add(KpiCard("Thuật toán", (model?["algorithm"]?.ToString() ?? "chưa nạp").Split('(')[0].Trim(), Medium, 260));
        _content.Controls.Add(cards);

        var distTitle = new Label { Text = "Phân bố mức nguy cơ (MapReduce / MongoDB)", Location = new Point(26, 210),
            AutoSize = true, ForeColor = Fg, Font = new Font("Segoe UI Semibold", 11f) };
        _content.Controls.Add(distTitle);
        int max = Math.Max(1, Math.Max(high, Math.Max(med, low)));
        _content.Controls.Add(DistBar("Thấp", low, max, Low, 245));
        _content.Controls.Add(DistBar("Trung bình", med, max, Medium, 285));
        _content.Controls.Add(DistBar("Cao", high, max, High, 325));

        var qTxt = quality is null ? "" :
            $"Chất lượng: hợp lệ {quality["valid_row_pct"]}%  ·  đầy đủ ô {quality["field_completeness_pct"]}%  ·  " +
            $"vector duy nhất {quality["unique_feature_signature"]}  ·  dòng trùng {quality["duplicated_feature_rows"]}  ·  xung đột nhãn {quality["signature_label_conflicts"]}";
        _content.Controls.Add(new Label { Text = qTxt, Location = new Point(26, 380), AutoSize = true, ForeColor = Muted });
        _content.Controls.Add(new Label { Text = $"MapReduce chạy lúc: {mrAt}", Location = new Point(26, 405), AutoSize = true, ForeColor = Muted });
    }

    // ================= PREDICT =================
    readonly Dictionary<string, NumericUpDown> _inputs = new();
    async void ShowPredict()
    {
        _content.Controls.Clear();
        _inputs.Clear();
        _content.Controls.Add(Header("Dự đoán nguy cơ (23 chỉ số)"));

        var flow = new FlowLayoutPanel { Location = new Point(24, 70), Size = new Size(560, 560),
            AutoScroll = true, BackColor = Bg };
        foreach (var (key, label) in Features)
        {
            var row = new Panel { Size = new Size(520, 34), BackColor = Bg };
            row.Controls.Add(new Label { Text = label, Location = new Point(0, 6), Size = new Size(260, 24), ForeColor = Fg });
            decimal min = key == "age" ? 0 : 1, max = key == "age" ? 120 : (key == "gender" ? 2 : 9);
            decimal def = key == "age" ? 50 : (key == "gender" ? 1 : 5);
            var num = new NumericUpDown { Location = new Point(270, 4), Size = new Size(90, 26),
                Minimum = min, Maximum = max, Value = def, BackColor = Card, ForeColor = Fg,
                BorderStyle = BorderStyle.FixedSingle };
            _inputs[key] = num;
            row.Controls.Add(num);
            flow.Controls.Add(row);
        }
        _content.Controls.Add(flow);

        var pidLabel = new Label { Text = "Mã BN (tuỳ chọn):", Location = new Point(610, 74), AutoSize = true, ForeColor = Fg };
        var pid = new TextBox { Location = new Point(610, 96), Size = new Size(200, 26), Text = "BN-DEMO",
            BackColor = Card, ForeColor = Fg, BorderStyle = BorderStyle.FixedSingle };
        var btn = new Button { Text = "🔮  Dự đoán", Location = new Point(610, 132), Size = new Size(200, 40),
            BackColor = Accent, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI Semibold", 11f) };
        btn.FlatAppearance.BorderSize = 0;
        var resultHost = new Panel { Location = new Point(610, 190), Size = new Size(460, 380), BackColor = Bg };
        _content.Controls.Add(pidLabel);
        _content.Controls.Add(pid);
        _content.Controls.Add(btn);
        _content.Controls.Add(resultHost);

        btn.Click += async (_, _) =>
        {
            btn.Enabled = false; btn.Text = "⏳ Đang dự đoán…";
            resultHost.Controls.Clear();
            try
            {
                var body = new Dictionary<string, object>();
                if (!string.IsNullOrWhiteSpace(pid.Text)) body["patient_id"] = pid.Text.Trim();
                foreach (var (key, _) in Features) body[key] = (int)_inputs[key].Value;
                var res = await _api.PostAsync("/predict", body);
                RenderPredict(resultHost, res!);
            }
            catch (ApiException ex) { RenderApiError(resultHost, ex); }
            catch (Exception ex) { ShowError(ex); }
            finally { btn.Enabled = true; btn.Text = "🔮  Dự đoán"; }
        };
    }

    void RenderPredict(Panel host, JsonNode res)
    {
        string level = res["predicted_level"]?.ToString() ?? "?";
        var col = level == "High" ? High : level == "Medium" ? Medium : Low;
        string viet = level == "High" ? "CAO" : level == "Medium" ? "TRUNG BÌNH" : "THẤP";
        host.Controls.Add(new Label { Text = "Kết quả:", Location = new Point(0, 0), AutoSize = true, ForeColor = Muted });
        host.Controls.Add(new Label { Text = viet, Location = new Point(0, 20), AutoSize = true,
            ForeColor = col, Font = new Font("Segoe UI Black", 26f) });

        var probs = res["probabilities"];
        int y = 90;
        foreach (var (lab, key, c) in new[] { ("Thấp", "Low", Low), ("Trung bình", "Medium", Medium), ("Cao", "High", High) })
        {
            double p = probs?[key]?.GetValue<double>() ?? 0;
            host.Controls.Add(new Label { Text = $"{lab}: {p:P1}", Location = new Point(0, y), Size = new Size(430, 18), ForeColor = Fg });
            var bar = new Panel { Location = new Point(0, y + 20), Size = new Size((int)(420 * Math.Clamp(p, 0, 1)) + 2, 16), BackColor = c };
            var track = new Panel { Location = new Point(0, y + 20), Size = new Size(422, 16), BackColor = Card };
            host.Controls.Add(bar); host.Controls.Add(track); bar.BringToFront();
            y += 52;
        }
        double lat = res["latency_ms"]?.GetValue<double>() ?? 0;
        host.Controls.Add(new Label { Text = $"Thời gian phản hồi: {lat:N0} ms   ·   model: {res["model_run_id"]}",
            Location = new Point(0, y + 4), AutoSize = true, ForeColor = Muted });
        host.Controls.Add(new Label { Text = res["disclaimer"]?.ToString() ?? "", Location = new Point(0, y + 28),
            Size = new Size(440, 40), ForeColor = Muted, Font = new Font("Segoe UI Italic", 8.5f) });
    }

    void RenderApiError(Panel host, ApiException ex)
    {
        string msg = ex.StatusCode == 503 ? "Model chưa được nạp trên server (503)."
                   : ex.StatusCode == 422 ? "Dữ liệu nhập không hợp lệ (422) — kiểm tra miền giá trị."
                   : $"Lỗi API ({ex.StatusCode}).";
        host.Controls.Add(new Label { Text = "⚠ " + msg, Location = new Point(0, 20), Size = new Size(440, 60),
            ForeColor = High, Font = new Font("Segoe UI Semibold", 11f) });
    }

    // ================= PATIENTS =================
    int _page = 1;
    async void ShowPatients()
    {
        _content.Controls.Clear();
        _content.Controls.Add(Header("Danh sách bệnh nhân"));

        var levelCb = new ComboBox { Location = new Point(24, 70), Size = new Size(120, 26), DropDownStyle = ComboBoxStyle.DropDownList, BackColor = Card, ForeColor = Fg };
        levelCb.Items.AddRange(new object[] { "Tất cả mức", "Low", "Medium", "High" }); levelCb.SelectedIndex = 0;
        var genderCb = new ComboBox { Location = new Point(154, 70), Size = new Size(110, 26), DropDownStyle = ComboBoxStyle.DropDownList, BackColor = Card, ForeColor = Fg };
        genderCb.Items.AddRange(new object[] { "Giới tính", "1 (Nam)", "2 (Nữ)" }); genderCb.SelectedIndex = 0;
        var featCb = new ComboBox { Location = new Point(274, 70), Size = new Size(170, 26), DropDownStyle = ComboBoxStyle.DropDownList, BackColor = Card, ForeColor = Fg };
        featCb.Items.Add("— chỉ số —"); foreach (var s in ScaleCols) featCb.Items.Add(s); featCb.SelectedIndex = 0;
        var opCb = new ComboBox { Location = new Point(454, 70), Size = new Size(70, 26), DropDownStyle = ComboBoxStyle.DropDownList, BackColor = Card, ForeColor = Fg };
        opCb.Items.AddRange(new object[] { "gte", "lte", "eq" }); opCb.SelectedIndex = 0;
        var valNum = new NumericUpDown { Location = new Point(534, 70), Size = new Size(60, 26), Minimum = 1, Maximum = 9, Value = 7, BackColor = Card, ForeColor = Fg };
        var loadBtn = new Button { Text = "Tải", Location = new Point(604, 69), Size = new Size(80, 28), BackColor = Accent, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        loadBtn.FlatAppearance.BorderSize = 0;

        var grid = new DataGridView { Location = new Point(24, 110), Size = new Size(1080, 480),
            BackgroundColor = Panel, ForeColor = Fg, GridColor = Card, BorderStyle = BorderStyle.None,
            AllowUserToAddRows = false, ReadOnly = true, RowHeadersVisible = false,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill, SelectionMode = DataGridViewSelectionMode.FullRowSelect };
        grid.EnableHeadersVisualStyles = false;
        grid.ColumnHeadersDefaultCellStyle.BackColor = Side;
        grid.ColumnHeadersDefaultCellStyle.ForeColor = Fg;
        grid.DefaultCellStyle.BackColor = Panel;
        grid.DefaultCellStyle.ForeColor = Fg;
        grid.DefaultCellStyle.SelectionBackColor = Accent;

        var prev = new Button { Text = "‹ Trước", Location = new Point(24, 600), Size = new Size(90, 28), BackColor = Card, ForeColor = Fg, FlatStyle = FlatStyle.Flat };
        var next = new Button { Text = "Sau ›", Location = new Point(120, 600), Size = new Size(90, 28), BackColor = Card, ForeColor = Fg, FlatStyle = FlatStyle.Flat };
        var pageLbl = new Label { Location = new Point(220, 605), AutoSize = true, ForeColor = Muted };

        _content.Controls.AddRange(new Control[] { levelCb, genderCb, featCb, opCb, valNum, loadBtn, grid, prev, next, pageLbl });

        async Task Load()
        {
            try
            {
                var qs = new List<string> { $"page={_page}", "page_size=25" };
                if (levelCb.SelectedIndex > 0) qs.Add("level=" + levelCb.Text);
                if (genderCb.SelectedIndex > 0) qs.Add("gender=" + genderCb.Text[0]);
                if (featCb.SelectedIndex > 0) { qs.Add("feature=" + featCb.Text); qs.Add("operator=" + opCb.Text); qs.Add("value=" + (int)valNum.Value); }
                var res = await _api.GetAsync("/patients?" + string.Join("&", qs));
                var items = res?["items"]?.AsArray();
                var dt = new DataTable();
                foreach (var c in new[] { "patient_id", "age", "gender", "level", "age_group", "smoking", "coughing_of_blood", "obesity", "genetic_risk" })
                    dt.Columns.Add(c);
                if (items != null)
                    foreach (var it in items)
                    {
                        dt.Rows.Add(dt.Columns.Cast<DataColumn>().Select(c => it?[c.ColumnName]?.ToString() ?? "").ToArray());
                    }
                grid.DataSource = dt;
                int total = res?["total"]?.GetValue<int>() ?? 0;
                int pages = res?["total_pages"]?.GetValue<int>() ?? 1;
                pageLbl.Text = $"Trang {_page}/{pages}  ·  tổng {total} bệnh nhân";
            }
            catch (ApiException ex) { MessageBox.Show(ex.Message, ex.StatusCode == 422 ? "Bộ lọc không hợp lệ (422)" : "Lỗi API"); }
            catch (Exception ex) { ShowError(ex); }
        }

        loadBtn.Click += async (_, _) => { _page = 1; await Load(); };
        prev.Click += async (_, _) => { if (_page > 1) { _page--; await Load(); } };
        next.Click += async (_, _) => { _page++; await Load(); };
        _page = 1;
        await Load();
    }

    // ================= QUALITY =================
    async void ShowQuality()
    {
        _content.Controls.Clear();
        _content.Controls.Add(Header("Chất lượng dữ liệu"));
        var loading = Loading(); _content.Controls.Add(loading);
        JsonNode? q;
        try { q = await _api.GetAsync("/quality"); }
        catch (Exception ex) { _content.Controls.Remove(loading); ShowError(ex); return; }
        _content.Controls.Remove(loading);

        var cards = new FlowLayoutPanel { Location = new Point(24, 70), Size = new Size(1080, 130), BackColor = Bg };
        cards.Controls.Add(KpiCard("Dòng hợp lệ", q?["valid_row_pct"] + "%", Low));
        cards.Controls.Add(KpiCard("Đầy đủ ô", q?["field_completeness_pct"] + "%", Accent));
        cards.Controls.Add(KpiCard("Vector duy nhất", q?["unique_feature_signature"]?.ToString() ?? "—", Medium));
        cards.Controls.Add(KpiCard("Dòng đặc trưng trùng", q?["duplicated_feature_rows"]?.ToString() ?? "—", High));
        _content.Controls.Add(cards);

        var grid = new DataGridView { Location = new Point(24, 210), Size = new Size(700, 380),
            BackgroundColor = Panel, ForeColor = Fg, BorderStyle = BorderStyle.None, RowHeadersVisible = false,
            ReadOnly = true, AllowUserToAddRows = false, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill };
        grid.EnableHeadersVisualStyles = false;
        grid.ColumnHeadersDefaultCellStyle.BackColor = Side; grid.ColumnHeadersDefaultCellStyle.ForeColor = Fg;
        grid.DefaultCellStyle.BackColor = Panel; grid.DefaultCellStyle.ForeColor = Fg;
        var dt = new DataTable(); dt.Columns.Add("Kiểm tra"); dt.Columns.Add("Số lượng");
        foreach (var c in q?["checks_table"]?.AsArray() ?? new JsonArray())
            dt.Rows.Add(c?["name"]?.ToString(), c?["count"]?.ToString());
        grid.DataSource = dt;
        _content.Controls.Add(grid);
    }

    // ================= widgets =================
    static Label Header(string text) => new()
    { Text = text, Location = new Point(24, 20), AutoSize = true, ForeColor = Fg, Font = new Font("Segoe UI Semibold", 16f) };

    static Label Loading() => new()
    { Text = "⏳ Đang tải…", Location = new Point(28, 70), AutoSize = true, ForeColor = Muted, Font = new Font("Segoe UI", 11f) };

    static Panel KpiCard(string title, string value, Color accent, int w = 250)
    {
        var p = new Panel { Size = new Size(w, 100), BackColor = Card, Margin = new Padding(0, 0, 16, 0) };
        p.Controls.Add(new Label { Text = title, Location = new Point(16, 14), AutoSize = true, ForeColor = Muted });
        p.Controls.Add(new Label { Text = value, Location = new Point(16, 40), Size = new Size(w - 32, 46),
            ForeColor = accent, Font = new Font("Segoe UI Semibold", 20f), AutoEllipsis = true });
        var strip = new Panel { Location = new Point(0, 0), Size = new Size(6, 100), BackColor = accent };
        p.Controls.Add(strip);
        return p;
    }

    static Panel DistBar(string label, int count, int max, Color color, int y)
    {
        var host = new Panel { Location = new Point(26, y), Size = new Size(900, 30), BackColor = Bg };
        host.Controls.Add(new Label { Text = label, Location = new Point(0, 4), Size = new Size(90, 22), ForeColor = Fg });
        host.Controls.Add(new Panel { Location = new Point(100, 2), Size = new Size((int)(700.0 * count / max) + 2, 24), BackColor = color });
        host.Controls.Add(new Label { Text = count.ToString("N0"), Location = new Point(810, 4), AutoSize = true, ForeColor = Fg });
        return host;
    }

    void ShowError(Exception ex) =>
        MessageBox.Show(ex.Message, "Lỗi", MessageBoxButtons.OK, MessageBoxIcon.Error);
}
