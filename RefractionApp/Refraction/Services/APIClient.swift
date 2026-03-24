// APIClient.swift — Async HTTP client for the Python analysis engine.
// Communicates with the FastAPI server on 127.0.0.1:7331.

import Foundation

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

    // MARK: - Private helpers

    private func post(path: String, body: [String: Any]) async throws -> Data {
        let url = URL(string: "\(baseURL)\(path)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let jsonData = try JSONSerialization.data(withJSONObject: body)
        request.httpBody = jsonData

        let (data, response) = try await session.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard http.statusCode == 200 else {
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
