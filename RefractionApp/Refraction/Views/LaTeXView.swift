// LaTeXView.swift — Renders a LaTeX formula as an image via the Python engine.
// Caches rendered images in memory to avoid redundant server calls.

import SwiftUI

struct LaTeXView: View {
    let latex: String
    let fontSize: Int

    @State private var image: NSImage?
    @State private var isLoading = false

    // In-memory cache shared across all LaTeXView instances
    private static var cache: [String: NSImage] = [:]

    init(_ latex: String, fontSize: Int = 20) {
        self.latex = latex
        self.fontSize = fontSize
    }

    var body: some View {
        Group {
            if let image {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
            } else if isLoading {
                ProgressView()
                    .controlSize(.small)
            } else {
                // Fallback: show the raw LaTeX in monospace
                Text(latex)
                    .font(.system(.callout, design: .monospaced))
            }
        }
        .task(id: latex) {
            await loadImage()
        }
    }

    private func loadImage() async {
        let cacheKey = "\(latex)_\(fontSize)"

        // Check cache first
        if let cached = Self.cache[cacheKey] {
            image = cached
            return
        }

        isLoading = true
        do {
            let pngData = try await APIClient.shared.renderLatex(
                latex: latex, dpi: 200, fontsize: fontSize
            )
            if let nsImage = NSImage(data: pngData) {
                Self.cache[cacheKey] = nsImage
                image = nsImage
            }
        } catch {
            // Silently fall back to text display
            image = nil
        }
        isLoading = false
    }
}
