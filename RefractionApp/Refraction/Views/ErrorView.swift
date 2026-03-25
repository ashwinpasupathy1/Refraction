// ErrorView.swift — User-friendly error display for Python backend errors.
// Parses common error patterns into plain English and provides Copy/Retry actions.

import SwiftUI

struct ErrorView: View {

    let errorMessage: String
    var onRetry: (() -> Void)?
    var onDismiss: (() -> Void)?

    var body: some View {
        VStack(spacing: 16) {
            // Icon
            Image(systemName: parsedError.icon)
                .font(.system(size: 40))
                .foregroundStyle(parsedError.color)

            // Friendly title
            Text(parsedError.title)
                .font(.headline)

            // Friendly description
            Text(parsedError.description)
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)

            // Technical details (collapsible)
            DisclosureGroup("Technical Details") {
                ScrollView {
                    Text(errorMessage)
                        .font(.system(size: 11, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .frame(maxHeight: 120)
                .background(.fill.quaternary, in: RoundedRectangle(cornerRadius: 6))
            }
            .frame(maxWidth: 420)

            // Actions
            HStack(spacing: 12) {
                Button {
                    copyErrorToClipboard()
                } label: {
                    Label("Copy Error Details", systemImage: "doc.on.doc")
                }
                .buttonStyle(.bordered)

                if let onRetry {
                    Button {
                        onRetry()
                    } label: {
                        Label("Retry", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.borderedProminent)
                }

                if let onDismiss {
                    Button("Dismiss", role: .cancel) {
                        onDismiss()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding(24)
    }

    // MARK: - Error Parsing

    private struct ParsedError {
        let title: String
        let description: String
        let icon: String
        let color: Color
    }

    private var parsedError: ParsedError {
        let msg = errorMessage.lowercased()

        if msg.contains("not found in app bundle") || msg.contains("sample data") {
            return ParsedError(
                title: "Sample Data Missing",
                description: "The bundled sample data could not be found. This usually means xcodegen needs to be re-run. Run 'xcodegen generate' in RefractionApp/ and rebuild.",
                icon: "shippingbox.and.arrow.backward",
                color: .orange
            )
        }

        if msg.contains("filenotfounderror") || msg.contains("no such file") {
            return ParsedError(
                title: "File Not Found",
                description: "The data file could not be located. It may have been moved, renamed, or deleted. Try selecting the file again.",
                icon: "doc.questionmark",
                color: .orange
            )
        }

        if msg.contains("valueerror") || msg.contains("could not convert") {
            return ParsedError(
                title: "Invalid Data Format",
                description: "The data file contains values that could not be processed. Check that your spreadsheet follows the expected layout for this chart type.",
                icon: "exclamationmark.triangle",
                color: .orange
            )
        }

        if msg.contains("keyerror") {
            return ParsedError(
                title: "Missing Column",
                description: "A required column or header is missing from your data file. Verify that column headers match the expected format.",
                icon: "tablecells.badge.ellipsis",
                color: .orange
            )
        }

        if msg.contains("permissionerror") || msg.contains("permission denied") {
            return ParsedError(
                title: "Permission Denied",
                description: "The app does not have permission to access this file. Try moving it to your Documents folder or granting access in System Settings.",
                icon: "lock.shield",
                color: .red
            )
        }

        if msg.contains("connection") || msg.contains("urlsession") || msg.contains("network") {
            return ParsedError(
                title: "Server Connection Error",
                description: "Could not connect to the analysis engine. The Python server may still be starting up. Wait a moment and try again.",
                icon: "wifi.exclamationmark",
                color: .red
            )
        }

        if msg.contains("memoryerror") || msg.contains("memory") {
            return ParsedError(
                title: "Out of Memory",
                description: "The dataset is too large to process. Try reducing the number of rows or columns in your data file.",
                icon: "memorychip",
                color: .red
            )
        }

        if msg.contains("timeout") {
            return ParsedError(
                title: "Request Timed Out",
                description: "The analysis took too long to complete. This may happen with very large datasets. Try reducing the data size.",
                icon: "clock.badge.exclamationmark",
                color: .orange
            )
        }

        if msg.contains("import") || msg.contains("modulenotfounderror") {
            return ParsedError(
                title: "Missing Dependency",
                description: "A required Python package is not installed. Try running setup.sh or reinstalling the app.",
                icon: "shippingbox",
                color: .red
            )
        }

        // Generic fallback
        return ParsedError(
            title: "Something Went Wrong",
            description: "An unexpected error occurred while processing your request. Check the technical details below for more information.",
            icon: "exclamationmark.circle",
            color: .red
        )
    }

    // MARK: - Actions

    private func copyErrorToClipboard() {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()

        let report = """
        Refraction Error Report
        =======================
        \(parsedError.title)

        \(errorMessage)

        App Version: \(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown")
        macOS: \(ProcessInfo.processInfo.operatingSystemVersionString)
        Bundle: \(Bundle.main.bundlePath)
        Date: \(ISO8601DateFormatter().string(from: Date()))
        """

        pasteboard.setString(report, forType: .string)
    }
}
