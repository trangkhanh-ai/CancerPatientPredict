using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace CancerUI;

/// <summary>Wrapper HttpClient gọi FastAPI (prefix /api/v1). Trả về JsonNode để đọc linh hoạt.</summary>
public class ApiClient
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(300) };
    public string BaseUrl { get; set; }

    public ApiClient(string baseUrl) => BaseUrl = baseUrl.TrimEnd('/');

    public async Task<JsonNode?> GetAsync(string path)
    {
        var resp = await _http.GetAsync(BaseUrl + path);
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode) throw new ApiException((int)resp.StatusCode, text);
        return JsonNode.Parse(text);
    }

    public async Task<JsonNode?> PostAsync(string path, object body)
    {
        var json = JsonSerializer.Serialize(body);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
        var resp = await _http.PostAsync(BaseUrl + path, content);
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode) throw new ApiException((int)resp.StatusCode, text);
        return JsonNode.Parse(text);
    }
}

public class ApiException : Exception
{
    public int StatusCode { get; }
    public ApiException(int code, string body) : base($"HTTP {code}\n{body}") => StatusCode = code;
}
