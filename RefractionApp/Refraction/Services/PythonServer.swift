// PythonServer.swift — Manages the Python uvicorn subprocess that hosts
// the Refraction analysis engine on 127.0.0.1:7331.
//
// Supports bundled Python (inside .app bundle) with fallback to system python3.
// Captures stderr, writes crash logs, and auto-restarts once on unexpected exit.

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

    /// The last crash message, shown to the user via alert.
    private(set) var lastCrashMessage: String?

    /// Whether the crash alert should be presented.
    var showCrashAlert: Bool = false

    private var process: Process?
    private var stdoutPipe: Pipe?
    private var stderrPipe: Pipe?
    private var healthPollTimer: Timer?

    /// Accumulated stderr output from the Python process.
    private var stderrBuffer: String = ""

    /// Whether we have already attempted one auto-restart.
    private var hasAutoRestarted: Bool = false

    /// Port the Python server listens on.
    static let port: Int = 7331

    /// Maximum time to wait for the server to become healthy.
    private static let startupTimeout: TimeInterval = 15.0

    /// Interval between /health polls during startup.
    private static let pollInterval: TimeInterval = 0.5

    /// Directory for crash logs.
    private static var logDirectory: URL {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home.appendingPathComponent("Library/Logs/Refraction")
    }

    // MARK: - Lifecycle

    /// Start the Python analysis server as a subprocess.
    /// Polls /health until the server responds, then transitions to `.running`.
    func start() {
        guard state == .idle || isFailedState else { return }

        state = .starting
        stderrBuffer = ""

        let proc = Process()
        let stdout = Pipe()
        let stderr = Pipe()

        let python = Self.pythonPath()
        let projectRoot = Self.resolveProjectRoot()

        NSLog("[PythonServer] Using Python: %@", python)
        NSLog("[PythonServer] Project root: %@", projectRoot.path)

        if python.contains("/usr/bin/env") {
            // System Python via env lookup
            proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            proc.arguments = [
                "python3", "-c",
                """
                import uvicorn
                from refraction.server.api import _make_app
                uvicorn.run(_make_app(), host='127.0.0.1', port=\(Self.port), log_level='warning')
                """
            ]
        } else {
            // Bundled Python — invoke directly
            proc.executableURL = URL(fileURLWithPath: python)
            proc.arguments = [
                "-c",
                """
                import uvicorn
                from refraction.server.api import _make_app
                uvicorn.run(_make_app(), host='127.0.0.1', port=\(Self.port), log_level='warning')
                """
            ]
        }

        proc.currentDirectoryURL = projectRoot

        // Build environment with PYTHONPATH
        var env = ProcessInfo.processInfo.environment
        let pythonPath = projectRoot.path
        if let existing = env["PYTHONPATH"] {
            env["PYTHONPATH"] = "\(pythonPath):\(existing)"
        } else {
            env["PYTHONPATH"] = pythonPath
        }
        proc.environment = env

        proc.standardOutput = stdout
        proc.standardError = stderr

        // Continuously read stderr in background
        stderr.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            DispatchQueue.main.async {
                self?.stderrBuffer += text
            }
        }

        // Handle unexpected termination
        proc.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                guard let self else { return }
                // Stop reading stderr
                stderr.fileHandleForReading.readabilityHandler = nil

                if case .running = self.state {
                    let exitCode = process.terminationStatus
                    let message = "Python server exited unexpectedly (code \(exitCode))"
                    self.writeCrashLog(message: message, stderr: self.stderrBuffer)
                    self.state = .failed(message)

                    // Auto-restart once
                    if !self.hasAutoRestarted {
                        self.hasAutoRestarted = true
                        NSLog("[PythonServer] Auto-restarting after crash...")
                        self.process = nil
                        self.state = .idle
                        self.start()
                    } else {
                        // Already tried auto-restart, show alert
                        self.lastCrashMessage = message
                        self.showCrashAlert = true
                    }
                }
            }
        }

        self.process = proc
        self.stdoutPipe = stdout
        self.stderrPipe = stderr

        do {
            try proc.run()
        } catch {
            let msg = "Failed to launch Python: \(error.localizedDescription)"
            state = .failed(msg)
            writeCrashLog(message: msg, stderr: "")
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

        // Stop stderr reading
        stderrPipe?.fileHandleForReading.readabilityHandler = nil

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

    /// Dismiss the crash alert.
    func dismissCrashAlert() {
        showCrashAlert = false
        lastCrashMessage = nil
    }

    // MARK: - Python Resolution

    /// Resolve the Python binary path.
    /// Priority: bundled python-env > REFRACTION_PYTHON env > well-known paths > system python3
    private static func pythonPath() -> String {
        // Check for bundled Python inside the .app bundle
        if let bundled = Bundle.main.resourceURL?
            .appendingPathComponent("python-env/bin/python3").path,
           FileManager.default.fileExists(atPath: bundled) {
            NSLog("[PythonServer] Found bundled Python at: %@", bundled)
            return bundled
        }

        // Check REFRACTION_PYTHON env var (set by user or launch script)
        if let envPython = ProcessInfo.processInfo.environment["REFRACTION_PYTHON"],
           FileManager.default.fileExists(atPath: envPython) {
            NSLog("[PythonServer] Using REFRACTION_PYTHON: %@", envPython)
            return envPython
        }

        // Check well-known Python locations that typically have packages.
        // /usr/bin/env inside Xcode subprocesses often resolves to a bare
        // system Python that lacks uvicorn/fastapi/etc.
        let candidates = [
            "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
        ]
        for path in candidates {
            if FileManager.default.fileExists(atPath: path) {
                NSLog("[PythonServer] Found Python at well-known path: %@", path)
                return path
            }
        }

        // Fall back to system Python for development
        NSLog("[PythonServer] No bundled Python found, using system python3")
        return "/usr/bin/env python3"
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
                    NSLog("[PythonServer] Server is healthy and running on port %d", Self.port)
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
        if !stderrBuffer.isEmpty {
            message += ": \(String(stderrBuffer.prefix(500)))"
        } else if let pipe = stderrPipe {
            let data = pipe.fileHandleForReading.availableData
            if let text = String(data: data, encoding: .utf8), !text.isEmpty {
                message += ": \(String(text.prefix(500)))"
            }
        }
        writeCrashLog(message: message, stderr: stderrBuffer)
        state = .failed(message)
        stop()
    }

    // MARK: - Crash Logging

    /// Write a crash log entry to ~/Library/Logs/Refraction/crash.log
    private func writeCrashLog(message: String, stderr: String) {
        let logDir = Self.logDirectory
        let logFile = logDir.appendingPathComponent("crash.log")

        do {
            try FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

            let timestamp = ISO8601DateFormatter().string(from: Date())
            let entry = """
            === Refraction Crash Report ===
            Timestamp: \(timestamp)
            Message:   \(message)
            Python:    \(Self.pythonPath())

            --- stderr output ---
            \(stderr.isEmpty ? "(empty)" : String(stderr.suffix(2000)))
            === End Report ===


            """

            if FileManager.default.fileExists(atPath: logFile.path) {
                let handle = try FileHandle(forWritingTo: logFile)
                handle.seekToEndOfFile()
                if let data = entry.data(using: .utf8) {
                    handle.write(data)
                }
                handle.closeFile()
            } else {
                try entry.write(to: logFile, atomically: true, encoding: .utf8)
            }

            NSLog("[PythonServer] Crash log written to: %@", logFile.path)
        } catch {
            NSLog("[PythonServer] Failed to write crash log: %@", error.localizedDescription)
        }
    }

    /// Resolve the project root directory (parent of RefractionApp/).
    /// In development, this walks up from the current file or uses a known path.
    private static func resolveProjectRoot() -> URL {
        // Strategy 1: Check if REFRACTION_ROOT env var is set
        if let root = ProcessInfo.processInfo.environment["REFRACTION_ROOT"] {
            return URL(fileURLWithPath: root)
        }

        // Strategy 2: Walk up from the main bundle looking for refraction/
        // The bundle is usually deep in DerivedData, so walk up generously.
        var candidate = Bundle.main.bundleURL
        for _ in 0..<10 {
            candidate = candidate.deletingLastPathComponent()
            let marker = candidate.appendingPathComponent("refraction").appendingPathComponent("__init__.py")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
        }

        // Strategy 3: Walk up from the Xcode project source root.
        // The .xcodeproj lives in RefractionApp/ which is one level below the repo root.
        // Use the SOURCE_ROOT build setting if available, or locate via the
        // project.yml that xcodegen uses.
        if let sourceRoot = ProcessInfo.processInfo.environment["SOURCE_ROOT"] {
            let repoRoot = URL(fileURLWithPath: sourceRoot).deletingLastPathComponent()
            let marker = repoRoot.appendingPathComponent("refraction").appendingPathComponent("__init__.py")
            if FileManager.default.fileExists(atPath: marker.path) {
                NSLog("[PythonServer] Found project root via SOURCE_ROOT: %@", repoRoot.path)
                return repoRoot
            }
        }

        // Strategy 4: Search well-known development paths.
        // Check any active worktrees first (they have the latest code),
        // then fall back to the main repo.
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var knownPaths = [String]()

        // Scan for worktrees under the main repo (they contain the latest dev code)
        let worktreeDir = "\(home)/Documents/Claude Prism/.claude/worktrees"
        if let entries = try? FileManager.default.contentsOfDirectory(atPath: worktreeDir) {
            for entry in entries {
                knownPaths.append("\(worktreeDir)/\(entry)")
            }
        }

        knownPaths += [
            "\(home)/Documents/Claude Prism",
            "\(home)/Documents/Refraction",
        ]
        for path in knownPaths {
            let marker = URL(fileURLWithPath: path).appendingPathComponent("refraction").appendingPathComponent("__init__.py")
            if FileManager.default.fileExists(atPath: marker.path) {
                NSLog("[PythonServer] Found project root at known path: %@", path)
                return URL(fileURLWithPath: path)
            }
        }

        // Strategy 5: Fall back to current working directory
        NSLog("[PythonServer] WARNING: Could not find project root, falling back to cwd: %@",
              FileManager.default.currentDirectoryPath)
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}
