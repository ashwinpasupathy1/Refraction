// PythonServer.swift — Manages the Python uvicorn subprocess that hosts
// the Refraction analysis engine on 127.0.0.1:7331.

import Foundation

@Observable
final class PythonServer {

    enum State: Equatable {
        case idle
        case starting
        case running
        case failed(String)
    }

    private(set) var state: State = .idle

    private var process: Process?
    private var stdoutPipe: Pipe?
    private var stderrPipe: Pipe?
    private var healthPollTimer: Timer?

    /// Port the Python server listens on.
    static let port: Int = 7331

    /// Maximum time to wait for the server to become healthy.
    private static let startupTimeout: TimeInterval = 15.0

    /// Interval between /health polls during startup.
    private static let pollInterval: TimeInterval = 0.5

    // MARK: - Lifecycle

    /// Start the Python analysis server as a subprocess.
    /// Polls /health until the server responds, then transitions to `.running`.
    func start() {
        guard state == .idle || isFailedState else { return }

        state = .starting

        let proc = Process()
        let stdout = Pipe()
        let stderr = Pipe()

        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.arguments = [
            "python3", "-c",
            """
            import uvicorn
            from refraction.server.api import _make_app
            uvicorn.run(_make_app(), host='127.0.0.1', port=\(Self.port), log_level='warning')
            """
        ]

        // Working directory: project root (parent of RefractionApp/)
        let appDir = Bundle.main.bundleURL
            .deletingLastPathComponent()  // Contents/
        // In development, assume CWD or use project root
        let projectRoot = Self.resolveProjectRoot()
        proc.currentDirectoryURL = projectRoot

        // Inherit the current environment so python3 resolves correctly
        var env = ProcessInfo.processInfo.environment
        // Ensure the refraction package is importable
        let pythonPath = projectRoot.path
        if let existing = env["PYTHONPATH"] {
            env["PYTHONPATH"] = "\(pythonPath):\(existing)"
        } else {
            env["PYTHONPATH"] = pythonPath
        }
        proc.environment = env

        proc.standardOutput = stdout
        proc.standardError = stderr

        // Handle unexpected termination
        proc.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                guard let self else { return }
                if case .running = self.state {
                    self.state = .failed("Server exited with code \(process.terminationStatus)")
                }
            }
        }

        self.process = proc
        self.stdoutPipe = stdout
        self.stderrPipe = stderr

        do {
            try proc.run()
        } catch {
            state = .failed("Failed to launch python3: \(error.localizedDescription)")
            return
        }

        // Poll /health until the server is ready
        pollForHealth()
    }

    /// Gracefully stop the Python server. Sends SIGTERM, then SIGKILL after 2s.
    func stop() {
        healthPollTimer?.invalidate()
        healthPollTimer = nil

        guard let proc = process, proc.isRunning else {
            state = .idle
            process = nil
            return
        }

        // SIGTERM for graceful shutdown
        proc.terminate()

        // Force-kill after 2 seconds if still running
        DispatchQueue.global().asyncAfter(deadline: .now() + 2.0) { [weak self] in
            guard let self, let p = self.process, p.isRunning else { return }
            kill(p.processIdentifier, SIGKILL)
            DispatchQueue.main.async {
                self.state = .idle
                self.process = nil
            }
        }

        // Wait briefly for clean exit
        DispatchQueue.global().async { [weak self] in
            proc.waitUntilExit()
            DispatchQueue.main.async {
                self?.state = .idle
                self?.process = nil
            }
        }
    }

    // MARK: - Private

    private var isFailedState: Bool {
        if case .failed = state { return true }
        return false
    }

    /// Poll the /health endpoint until the server responds or timeout.
    private func pollForHealth() {
        let startTime = Date()
        let url = URL(string: "http://127.0.0.1:\(Self.port)/health")!

        let timer = Timer.scheduledTimer(withTimeInterval: Self.pollInterval, repeats: true) { [weak self] timer in
            guard let self else { timer.invalidate(); return }

            // Check timeout
            if Date().timeIntervalSince(startTime) > Self.startupTimeout {
                timer.invalidate()
                self.readStderrAndFail()
                return
            }

            // Try /health
            let task = URLSession.shared.dataTask(with: url) { data, response, error in
                guard error == nil,
                      let http = response as? HTTPURLResponse,
                      http.statusCode == 200 else {
                    return // Not ready yet, keep polling
                }

                DispatchQueue.main.async {
                    timer.invalidate()
                    self.healthPollTimer = nil
                    self.state = .running
                }
            }
            task.resume()
        }

        RunLoop.main.add(timer, forMode: .common)
        healthPollTimer = timer
    }

    /// Read stderr output and transition to failed state.
    private func readStderrAndFail() {
        var message = "Server failed to start within \(Int(Self.startupTimeout))s"
        if let pipe = stderrPipe {
            let data = pipe.fileHandleForReading.availableData
            if let text = String(data: data, encoding: .utf8), !text.isEmpty {
                message += ": \(text.prefix(500))"
            }
        }
        state = .failed(message)
        stop()
    }

    /// Resolve the project root directory (parent of RefractionApp/).
    /// In development, this walks up from the current file or uses a known path.
    private static func resolveProjectRoot() -> URL {
        // Strategy 1: Check if REFRACTION_ROOT env var is set
        if let root = ProcessInfo.processInfo.environment["REFRACTION_ROOT"] {
            return URL(fileURLWithPath: root)
        }

        // Strategy 2: Walk up from the main bundle looking for refraction/
        var candidate = Bundle.main.bundleURL
        for _ in 0..<5 {
            candidate = candidate.deletingLastPathComponent()
            let marker = candidate.appendingPathComponent("refraction").appendingPathComponent("__init__.py")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
        }

        // Strategy 3: Fall back to current working directory
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}
