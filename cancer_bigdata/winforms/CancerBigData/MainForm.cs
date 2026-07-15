using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using CancerBigData.Api;

namespace CancerBigData.UI
{
    /// <summary>
    /// Module 5 — Cửa sổ chính: TabControl 5 tab (Dự đoán · Danh sách bệnh nhân · Thống kê ·
    /// Yếu tố nguy cơ · Chất lượng dữ liệu) + thanh trạng thái gọi GET /api/v1/health
    /// hiển thị trạng thái API · model_run_id · dataset_version.
    /// </summary>
    public class MainForm : Form
    {
        private static readonly Color LOW = Color.FromArgb(46, 158, 106);
        private static readonly Color HIGH = Color.FromArgb(225, 91, 100);
        private static readonly Color MUT = Color.FromArgb(107, 116, 128);

        private readonly ApiClient _api = new ApiClient();
        private readonly TabControl _tabs = new TabControl();
        private readonly StatusStrip _status = new StatusStrip();
        private readonly ToolStripStatusLabel _lblApi = new ToolStripStatusLabel("API: đang kiểm tra...");
        private readonly ToolStripStatusLabel _lblModel = new ToolStripStatusLabel("model_run_id: —");
        private readonly ToolStripStatusLabel _lblDataset = new ToolStripStatusLabel("dataset_version: —");
        private readonly ToolStripStatusLabel _lblDisclaimer = new ToolStripStatusLabel(
            "Kết quả phục vụ mục đích học thuật, không thay thế chẩn đoán y khoa.")
        { Spring = true, TextAlign = ContentAlignment.MiddleRight, ForeColor = Color.FromArgb(107, 116, 128) };
        private readonly System.Windows.Forms.Timer _healthTimer = new System.Windows.Forms.Timer();

        public MainForm()
        {
            Text = "Hệ thống dự đoán mức độ mắc bệnh ung thư — Big Data (HUFLIT)";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1024, 640);
            Size = new Size(1200, 700);
            Font = new Font("Segoe UI", 9);

            BuildTabs();
            BuildStatusBar();

            Load += async (s, e) => await RefreshHealthAsync();
            _healthTimer.Interval = 30_000;   // 30 giây / lần
            _healthTimer.Tick += async (s, e) => await RefreshHealthAsync();
            _healthTimer.Start();
        }

        private void BuildTabs()
        {
            _tabs.Dock = DockStyle.Fill;

            AddTab("🩺 Dự đoán", new PredictionControl());
            AddTab("👥 Danh sách bệnh nhân", new PatientSearchControl());
            AddTab("📊 Thống kê", new StatsDashboardControl());
            AddTab("⚠ Yếu tố nguy cơ", new RiskCorrelationControl());
            AddTab("✔ Chất lượng dữ liệu", new DataQualityControl());

            Controls.Add(_tabs);
        }

        private void AddTab(string title, Control content)
        {
            var page = new TabPage(title) { BackColor = Color.FromArgb(238, 241, 245) };
            content.Dock = DockStyle.Fill;
            page.Controls.Add(content);
            _tabs.TabPages.Add(page);
        }

        private void BuildStatusBar()
        {
            _lblApi.BorderSides = ToolStripStatusLabelBorderSides.Right;
            _lblModel.BorderSides = ToolStripStatusLabelBorderSides.Right;
            _lblDataset.BorderSides = ToolStripStatusLabelBorderSides.Right;
            _status.Items.AddRange(new ToolStripItem[] { _lblApi, _lblModel, _lblDataset, _lblDisclaimer });
            _status.SizingGrip = false;
            Controls.Add(_status);
        }

        private async Task RefreshHealthAsync()
        {
            try
            {
                var h = await _api.GetHealthInfoAsync();
                bool ok = h.Status == "ok" && h.Mongodb == "ok";
                _lblApi.Text = ok
                    ? (h.ModelLoaded ? "API: hoạt động · model đã nạp" : "API: hoạt động · model CHƯA nạp")
                    : $"API: {h.Status} · MongoDB: {h.Mongodb}";
                _lblApi.ForeColor = ok && h.ModelLoaded ? LOW : ok ? Color.FromArgb(224, 160, 26) : HIGH;
                _lblModel.Text = "model_run_id: " + (string.IsNullOrEmpty(h.ModelRunId) ? "—" : h.ModelRunId);
                _lblDataset.Text = "dataset_version: " + (string.IsNullOrEmpty(h.DatasetVersion) ? "—" : h.DatasetVersion);
            }
            catch (Exception)
            {
                _lblApi.Text = "API: KHÔNG kết nối được (http://localhost:8000)";
                _lblApi.ForeColor = HIGH;
                _lblModel.Text = "model_run_id: —";
                _lblDataset.Text = "dataset_version: —";
            }
        }
    }
}
