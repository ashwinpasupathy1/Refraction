// APIClient.swift — Async HTTP client for the Python analysis engine.
// Communicates with the FastAPI server on 127.0.0.1:7331.

import Foundation
import RefractionRenderer

actor APIClient {

    static let shared = APIClient()

    private let baseURL = "http://127.0.0.1:7331"
    private let session: URLSession

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        session = URLSession(configuration: config)
    }

    // MARK: - Public API

    /// Send a render request and decode the ChartSpec response.
    func analyze(chartType: ChartType, config: ChartConfig) async throws -> ChartSpec {
        let body: [String: Any] = [
            "chart_type": chartType.key,
            "kw": config.toDict()
        ]

        let data = try await post(path: "/render", body: body)

        // Decode the envelope
        let response = try JSONDecoder().decode(RenderResponse.self, from: data)

        guard response.ok, let spec = response.spec else {
            throw APIError.serverError(response.error ?? "Unknown server error")
        }

        return spec
    }

    /// Send a render request and return both the decoded ChartSpec and pretty-printed raw JSON.
    func analyzeWithRawJSON(chartType: ChartType, config: ChartConfig, inlineData: [String: Any]? = nil, debug: Bool = false) async throws -> (ChartSpec, String) {
        var kw = config.toDict()
        if debug { kw["_debug"] = true }
        if let data = inlineData {
            kw["data"] = data
        }
        let body: [String: Any] = [
            "chart_type": chartType.key,
            "kw": kw
        ]

        let data = try await post(path: "/render", body: body)

        // Pretty-print the raw JSON
        let rawJSON: String
        if let jsonObj = try? JSONSerialization.jsonObject(with: data),
           let prettyData = try? JSONSerialization.data(withJSONObject: jsonObj, options: [.prettyPrinted, .sortedKeys]),
           let prettyString = String(data: prettyData, encoding: .utf8) {
            rawJSON = prettyString
        } else {
            rawJSON = String(data: data, encoding: .utf8) ?? "(unable to decode)"
        }

        let response = try JSONDecoder().decode(RenderResponse.self, from: data)
        guard response.ok, let spec = response.spec else {
            throw APIError.serverError(response.error ?? "Unknown server error")
        }

        return (spec, rawJSON)
    }

    /// Check if the Python server is healthy.
    func health() async throws -> Bool {
        let url = URL(string: "\(baseURL)/health")!
        let (data, response) = try await session.data(from: url)

        guard let http = response as? HTTPURLResponse,
              http.statusCode == 200 else {
            return false
        }

        struct HealthResponse: Decodable {
            let status: String
        }

        let health = try JSONDecoder().decode(HealthResponse.self, from: data)
        return health.status == "ok"
    }

    /// Upload a file to the Python server and return the server-side path.
    func upload(fileURL: URL) async throws -> String {
        let url = URL(string: "\(baseURL)/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileData = try Data(contentsOf: fileURL)
        let filename = fileURL.lastPathComponent

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let http = response as? HTTPURLResponse,
              http.statusCode == 200 else {
            throw APIError.httpError(statusCode: (response as? HTTPURLResponse)?.statusCode ?? 0)
        }

        struct UploadResponse: Decodable {
            let ok: Bool
            let path: String?
            let error: String?
        }

        let uploadResp = try JSONDecoder().decode(UploadResponse.self, from: data)
        guard uploadResp.ok, let path = uploadResp.path else {
            throw APIError.serverError(uploadResp.error ?? "Upload failed")
        }

        return path
    }

    /// List sheet names in an Excel file (CSV returns ["Sheet1"]).
    func listSheets(excelPath: String) async throws -> [String] {
        let body: [String: Any] = ["excel_path": excelPath]
        let data = try await post(path: "/sheet-list", body: body)

        struct SheetListResponse: Decodable {
            let ok: Bool
            let sheets: [String]?
            let error: String?
        }

        let resp = try JSONDecoder().decode(SheetListResponse.self, from: data)
        guard resp.ok, let sheets = resp.sheets else {
            throw APIError.serverError(resp.error ?? "Failed to list sheets")
        }
        return sheets
    }

    /// Validate data against a table type. Returns (valid, errors, warnings).
    /// sheet can be an index (Int) or a name (String).
    func validateTable(excelPath: String, tableType: String, sheetIndex: Int = 0, sheetName: String? = nil) async throws -> ValidationResponse {
        var body: [String: Any] = [
            "excel_path": excelPath,
            "table_type": tableType,
        ]
        if let name = sheetName {
            body["sheet"] = name
        } else {
            body["sheet"] = sheetIndex
        }
        let data = try await post(path: "/validate-table", body: body)
        return try JSONDecoder().decode(ValidationResponse.self, from: data)
    }

    /// Render a LaTeX formula to PNG. Returns base64-encoded PNG data.
    func renderLatex(latex: String, dpi: Int = 150, fontsize: Int = 14) async throws -> Data {
        let body: [String: Any] = [
            "latex": latex,
            "dpi": dpi,
            "fontsize": fontsize,
        ]
        let data = try await post(path: "/render-latex", body: body)

        struct LatexResponse: Decodable {
            let ok: Bool
            let png_base64: String?
            let error: String?
        }

        let resp = try JSONDecoder().decode(LatexResponse.self, from: data)
        guard resp.ok, let b64 = resp.png_base64,
              let pngData = Data(base64Encoded: b64) else {
            throw APIError.serverError(resp.error ?? "LaTeX render failed")
        }
        return pngData
    }

    /// Fetch a read-only preview of the data in an Excel/CSV file.
    func dataPreview(excelPath: String = "", sheet: Int = 0, inlineData: [String: Any]? = nil) async throws -> DataPreviewResponse {
        var body: [String: Any] = ["sheet": sheet]
        if let inlineData { body["data"] = inlineData }
        if !excelPath.isEmpty { body["excel_path"] = excelPath }
        let data = try await post(path: "/data-preview", body: body)
        return try JSONDecoder().decode(DataPreviewResponse.self, from: data)
    }

    /// Recommend the best statistical test for the data.
    func recommendTest(inlineData: [String: Any]? = nil, excelPath: String = "", paired: Bool = false, tableType: String = "column") async throws -> RecommendTestResponse {
        var body: [String: Any] = ["paired": paired, "table_type": tableType]
        if let inlineData { body["data"] = inlineData }
        if !excelPath.isEmpty { body["excel_path"] = excelPath }
        let data = try await post(path: "/recommend-test", body: body)
        return try JSONDecoder().decode(RecommendTestResponse.self, from: data)
    }

    /// Run a standalone statistical analysis and return comprehensive results.
    func analyzeStats(
        inlineData: [String: Any]? = nil,
        excelPath: String = "",
        analysisType: String,
        paired: Bool = false,
        posthoc: String = "Tukey HSD",
        mcCorrection: String = "Holm-Bonferroni",
        control: String? = nil
    ) async throws -> AnalyzeStatsResponse {
        var body: [String: Any] = [
            "analysis_type": analysisType,
            "paired": paired,
            "posthoc": posthoc,
            "mc_correction": mcCorrection,
        ]
        if let inlineData { body["data"] = inlineData }
        if !excelPath.isEmpty { body["excel_path"] = excelPath }
        if let control { body["control"] = control }
        let data = try await post(path: "/analyze-stats", body: body)
        let response = try JSONDecoder().decode(AnalyzeStatsResponse.self, from: data)

        // Attach the raw JSON for developer mode display
        if let jsonObj = try? JSONSerialization.jsonObject(with: data),
           let prettyData = try? JSONSerialization.data(withJSONObject: jsonObj, options: [.prettyPrinted, .sortedKeys]),
           let prettyString = String(data: prettyData, encoding: .utf8) {
            response.rawJSON = prettyString
        }

        return response
    }

    // MARK: - Private helpers

    private func post(path: String, body: [String: Any]) async throws -> Data {
        let url = URL(string: "\(baseURL)\(path)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let jsonData = try JSONSerialization.data(withJSONObject: body)
        request.httpBody = jsonData

        // Log request
        let requestBody = String(data: jsonData, encoding: .utf8) ?? "{}"
        let start = Date()
        await DebugLog.shared.logRequest(method: "POST", path: path, body: requestBody)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            await DebugLog.shared.logError(method: "POST", path: path, error: error.localizedDescription)
            throw error
        }

        let durationMs = Int(Date().timeIntervalSince(start) * 1000)
        let responseBody = String(data: data, encoding: .utf8) ?? ""

        guard let http = response as? HTTPURLResponse else {
            await DebugLog.shared.logError(method: "POST", path: path, error: "Invalid response")
            throw APIError.invalidResponse
        }

        // Log response
        let prettyResponse: String
        if let jsonObj = try? JSONSerialization.jsonObject(with: data),
           let prettyData = try? JSONSerialization.data(withJSONObject: jsonObj, options: .prettyPrinted) {
            prettyResponse = String(data: prettyData, encoding: .utf8) ?? responseBody
        } else {
            prettyResponse = responseBody
        }
        await DebugLog.shared.logResponse(method: "POST", path: path, statusCode: http.statusCode, body: prettyResponse, durationMs: durationMs)

        // Extract engine trace if present in the response
        if let jsonObj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let trace = jsonObj["_trace"] as? [String], !trace.isEmpty {
            await DebugLog.shared.logEngineTrace(trace, forPath: path)
        }

        guard http.statusCode == 200 else {
            if let errorObj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                let errorMsg = errorObj["error"] as? String ?? "Unknown error"
                // Log full Python traceback if present
                if let tb = errorObj["traceback"] as? String, !tb.isEmpty {
                    await DebugLog.shared.logTraceback(method: "POST", path: path, traceback: tb)
                }
                throw APIError.serverError(errorMsg)
            }
            throw APIError.httpError(statusCode: http.statusCode)
        }

        return data
    }
}

// MARK: - Errors

enum APIError: LocalizedError {
    case serverError(String)
    case httpError(statusCode: Int)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .serverError(let msg):
            return "Server error: \(msg)"
        case .httpError(let code):
            return "HTTP error \(code)"
        case .invalidResponse:
            return "Invalid response from server"
        }
    }
}

// MARK: - Validation Response

struct ValidationResponse: Decodable {
    let ok: Bool
    let valid: Bool?
    let errors: [String]?
    let warnings: [String]?
    let shape: [Int]?
    let error: String?
}

// MARK: - Data Preview Response

struct DataPreviewResponse: Decodable {
    let ok: Bool
    let columns: [String]?
    let rows: [[AnyCellValue]]?
    let shape: [Int]?
    let error: String?
}

// MARK: - Recommend Test Response

struct RecommendTestResponse: Decodable {
    let ok: Bool
    let test: String?
    let testLabel: String?
    let posthoc: String?
    let justification: String?
    let error: String?
    let checks: DiagnosticChecks?

    enum CodingKeys: String, CodingKey {
        case ok, test, posthoc, justification, error, checks
        case testLabel = "test_label"
    }
}

/// Diagnostic checks returned by /recommend-test
struct DiagnosticChecks: Decodable {
    let nGroups: Int
    let paired: Bool
    let allNormal: Bool
    let equalVariance: Bool
    let leveneP: Double?
    let minN: Int
    let normality: [String: NormalityResult]

    enum CodingKeys: String, CodingKey {
        case paired, normality
        case nGroups = "n_groups"
        case allNormal = "all_normal"
        case equalVariance = "equal_variance"
        case leveneP = "levene_p"
        case minN = "min_n"
    }
}

struct NormalityResult: Decodable {
    let stat: Double?
    let p: Double?
    let normal: Bool
}

// MARK: - Analyze Stats Response

final class AnalyzeStatsResponse: Decodable {
    let ok: Bool
    let analysisType: String?
    let analysisLabel: String?
    let recommendation: RecommendationResult?
    let descriptive: [[String: AnyCellValue]]?
    let comparisons: [[String: AnyCellValue]]?
    let summary: String?
    let error: String?
    /// Raw JSON string from the API (set after decoding, not part of the JSON).
    var rawJSON: String = ""

    enum CodingKeys: String, CodingKey {
        case ok
        case analysisType = "analysis_type"
        case analysisLabel = "analysis_label"
        case recommendation, descriptive, comparisons, summary, error
    }
}

struct RecommendationResult: Decodable {
    let test: String
    let testLabel: String
    let posthoc: String?
    let justification: String

    enum CodingKeys: String, CodingKey {
        case test
        case testLabel = "test_label"
        case posthoc, justification
    }
}

enum AnyCellValue: Decodable {
    case string(String)
    case number(Double)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let d = try? container.decode(Double.self) {
            self = .number(d)
        } else if let s = try? container.decode(String.self) {
            self = .string(s)
        } else {
            self = .null
        }
    }

    var displayString: String {
        switch self {
        case .string(let s): return s
        case .number(let d):
            if d == d.rounded() && abs(d) < 1e15 {
                return String(format: "%.0f", d)
            }
            return String(format: "%.4g", d)
        case .null: return ""
        }
    }
}
