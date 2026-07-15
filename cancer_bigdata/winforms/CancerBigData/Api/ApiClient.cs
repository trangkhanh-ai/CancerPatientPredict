using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace CancerBigData.Api
{
    // ===================== DTO =====================
    public class HealthDto
    {
        [JsonPropertyName("status")] public string Status { get; set; } = "";
        [JsonPropertyName("mongodb")] public string Mongodb { get; set; } = "";
        [JsonPropertyName("model_loaded")] public bool ModelLoaded { get; set; }
        [JsonPropertyName("model_run_id")] public string ModelRunId { get; set; }
        [JsonPropertyName("dataset_version")] public string DatasetVersion { get; set; }
    }

    public class StatsDto
    {
        [JsonPropertyName("total")] public int Total { get; set; }
        [JsonPropertyName("level_distribution")] public Dictionary<string, int> LevelDistribution { get; set; } = new();
        [JsonPropertyName("gender_distribution")] public Dictionary<string, int> GenderDistribution { get; set; } = new();
        [JsonPropertyName("age_group_distribution")] public Dictionary<string, int> AgeGroupDistribution { get; set; } = new();
        [JsonPropertyName("avg_indicators_by_level")] public Dictionary<string, Dictionary<string, double>> AvgByLevel { get; set; } = new();
        [JsonPropertyName("chart_indicators")] public List<string> ChartIndicators { get; set; } = new();
    }

    public class CheckItem
    {
        [JsonPropertyName("name")] public string Name { get; set; } = "";
        [JsonPropertyName("count")] public int Count { get; set; }
    }

    public class QualityDto
    {
        [JsonPropertyName("row_count_raw")] public int RowCountRaw { get; set; }
        [JsonPropertyName("row_count_valid")] public int RowCountValid { get; set; }
        [JsonPropertyName("row_count_invalid")] public int RowCountInvalid { get; set; }
        [JsonPropertyName("valid_row_pct")] public double ValidRowPct { get; set; }
        [JsonPropertyName("field_completeness_pct")] public double FieldCompletenessPct { get; set; }
        [JsonPropertyName("unique_feature_signature")] public int UniqueSignature { get; set; }
        [JsonPropertyName("duplicated_feature_rows")] public int DuplicatedFeatureRows { get; set; }
        [JsonPropertyName("checks_table")] public List<CheckItem> Checks { get; set; } = new();
    }

    /// <summary>Một yếu tố nguy cơ đã xếp hạng (Module 2 — tương quan).</summary>
    public class RiskFactorDto
    {
        [JsonPropertyName("rank")] public int Rank { get; set; }
        [JsonPropertyName("indicator")] public string Indicator { get; set; } = "";
        [JsonPropertyName("impact")] public double Impact { get; set; }
        [JsonPropertyName("mean_by_level")] public Dictionary<string, double> MeanByLevel { get; set; } = new();
        [JsonPropertyName("pct_high_when_high_value")] public double PctHighWhenHighValue { get; set; }
    }

    public class CorrelationDto
    {
        [JsonPropertyName("total")] public int Total { get; set; }
        [JsonPropertyName("factors")] public List<RiskFactorDto> Factors { get; set; } = new();
        [JsonPropertyName("top_risk_factors")] public List<string> TopRiskFactors { get; set; } = new();
        [JsonPropertyName("method")] public string Method { get; set; } = "";
    }

    public class PredictResponseDto
    {
        [JsonPropertyName("prediction_id")] public string PredictionId { get; set; } = "";
        [JsonPropertyName("patient_id")] public string PatientId { get; set; }
        [JsonPropertyName("predicted_level")] public string PredictedLevel { get; set; } = "";
        [JsonPropertyName("probabilities")] public Dictionary<string, double> Probabilities { get; set; } = new();
        [JsonPropertyName("latency_ms")] public double LatencyMs { get; set; }
        [JsonPropertyName("disclaimer")] public string Disclaimer { get; set; } = "";
    }

    public class PagedPatientsDto
    {
        [JsonPropertyName("items")] public List<Dictionary<string, object>> Items { get; set; } = new();
        [JsonPropertyName("page")] public int Page { get; set; }
        [JsonPropertyName("page_size")] public int PageSize { get; set; }
        [JsonPropertyName("total")] public int Total { get; set; }
        [JsonPropertyName("total_pages")] public int TotalPages { get; set; }
    }

    /// <summary>Bộ lọc tìm kiếm — khớp whitelist của backend.</summary>
    public class PatientQuery
    {
        public int Page { get; set; } = 1;
        public int PageSize { get; set; } = 20;
        public string Level { get; set; }
        public int? Gender { get; set; }
        public int? AgeMin { get; set; }
        public int? AgeMax { get; set; }
        public string Feature { get; set; }
        public string Operator { get; set; }
        public int? Value { get; set; }
        public int? MinValue { get; set; }
        public int? MaxValue { get; set; }
        public string SortBy { get; set; }
        public string SortDir { get; set; }

        public string ToQueryString(bool includePaging = true)
        {
            var sb = new StringBuilder();
            void Add(string k, object v)
            {
                if (v == null) return;
                sb.Append(sb.Length == 0 ? '?' : '&').Append(k).Append('=').Append(Uri.EscapeDataString(v.ToString()));
            }
            if (includePaging) { Add("page", Page); Add("page_size", PageSize); }
            Add("level", Level); Add("gender", Gender);
            Add("age_min", AgeMin); Add("age_max", AgeMax);
            Add("feature", Feature); Add("operator", Operator); Add("value", Value);
            Add("min_value", MinValue); Add("max_value", MaxValue);
            Add("sort_by", SortBy); Add("sort_dir", SortDir);
            return sb.ToString();
        }
    }

    /// <summary>Lỗi API kèm mã HTTP để UI phân biệt 422 (validate) / 503 (model chưa nạp).</summary>
    public class ApiException : Exception
    {
        public int StatusCode { get; }
        public string Body { get; }
        public ApiException(int statusCode, string body)
            : base($"API {statusCode}: {body}")
        {
            StatusCode = statusCode;
            Body = body;
        }
    }

    // ===================== CLIENT =====================
    public class ApiClient
    {
        // ⚠ Base address PHẢI có /api/v1/ (prefix của FastAPI) — đọc từ appsettings.json
        private static readonly HttpClient _http = new HttpClient
        {
            BaseAddress = new Uri(LoadBaseUrl()),
            Timeout = TimeSpan.FromSeconds(90),   // lần /predict đầu tiên Spark codegen có thể chậm
        };
        private static readonly JsonSerializerOptions _opt = new() { PropertyNameCaseInsensitive = true };

        /// <summary>Đọc ApiBaseUrl từ appsettings.json cạnh file exe; fallback mặc định.</summary>
        private static string LoadBaseUrl()
        {
            const string fallback = "http://localhost:8000/api/v1/";
            try
            {
                string path = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
                if (File.Exists(path))
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(path));
                    if (doc.RootElement.TryGetProperty("ApiBaseUrl", out var el))
                    {
                        string url = (el.GetString() ?? "").Trim();
                        if (url.Length > 0)
                            return url.EndsWith("/") ? url : url + "/";
                    }
                }
            }
            catch { /* dùng fallback */ }
            return fallback;
        }

        public async Task<HealthDto> GetHealthInfoAsync()
            => JsonSerializer.Deserialize<HealthDto>(await _http.GetStringAsync("health"), _opt) ?? new HealthDto();

        public async Task<StatsDto> GetStatsAsync()
            => JsonSerializer.Deserialize<StatsDto>(await _http.GetStringAsync("stats"), _opt) ?? new StatsDto();

        public async Task<QualityDto> GetQualityAsync()
            => JsonSerializer.Deserialize<QualityDto>(await _http.GetStringAsync("quality"), _opt) ?? new QualityDto();

        public async Task<CorrelationDto> GetCorrelationAsync()
            => JsonSerializer.Deserialize<CorrelationDto>(await _http.GetStringAsync("correlation"), _opt) ?? new CorrelationDto();

        public async Task<PagedPatientsDto> SearchPatientsAsync(PatientQuery q, CancellationToken token = default)
        {
            using var resp = await _http.GetAsync("patients" + q.ToQueryString(), token);
            resp.EnsureSuccessStatusCode();
            string json = await resp.Content.ReadAsStringAsync(token);
            return JsonSerializer.Deserialize<PagedPatientsDto>(json, _opt) ?? new PagedPatientsDto();
        }

        /// <summary>Tải CSV đã lọc từ backend và lưu ra file.</summary>
        public async Task ExportPatientsCsvAsync(PatientQuery q, string savePath)
        {
            using var resp = await _http.GetAsync("patients/export" + q.ToQueryString(includePaging: false));
            resp.EnsureSuccessStatusCode();
            await using var fs = File.Create(savePath);
            await resp.Content.CopyToAsync(fs);
        }

        public async Task<PredictResponseDto> PredictAsync(Dictionary<string, object> features)
        {
            string body = JsonSerializer.Serialize(features);
            using var content = new StringContent(body, Encoding.UTF8, "application/json");
            using var resp = await _http.PostAsync("predict", content);
            string json = await resp.Content.ReadAsStringAsync();
            if (!resp.IsSuccessStatusCode)
                throw new ApiException((int)resp.StatusCode, json);
            return JsonSerializer.Deserialize<PredictResponseDto>(json, _opt) ?? new PredictResponseDto();
        }

        public async Task<string> GetHealthAsync() => await _http.GetStringAsync("health");
    }
}
