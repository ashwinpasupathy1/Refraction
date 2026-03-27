// StatsTestDetailDialog.swift — Full mathematical description of a statistical test.
// Presented as a sheet from the Stats Wiki dialog.

import SwiftUI

struct StatsTestDetailDialog: View {

    let detail: StatsTestDetail
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            HStack {
                Text(detail.name)
                    .font(.headline)
                Spacer()
                Button { dismiss() } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                        .font(.title3)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 20)
            .padding(.top, 16)
            .padding(.bottom, 8)

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {

                    // Aliases
                    if !detail.aliases.isEmpty {
                        Text("Also known as: \(detail.aliases.joined(separator: ", "))")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }

                    // Hypotheses
                    sectionView(title: "Hypotheses", systemImage: "function") {
                        formulaText(detail.hypotheses)
                    }

                    // Test Statistic
                    sectionView(title: "Test Statistic", systemImage: "x.squareroot") {
                        formulaText(detail.testStatistic)
                    }

                    // Distribution
                    sectionView(title: "Distribution under H\u{2080}", systemImage: "chart.bar.xaxis") {
                        Text(detail.distribution)
                            .font(.callout)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    // Assumptions
                    sectionView(title: "Assumptions", systemImage: "checklist") {
                        VStack(alignment: .leading, spacing: 4) {
                            ForEach(detail.assumptions, id: \.self) { assumption in
                                HStack(alignment: .top, spacing: 6) {
                                    Text("\u{2022}")
                                        .font(.callout)
                                        .foregroundStyle(.secondary)
                                    Text(assumption)
                                        .font(.callout)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }

                    // When to Use
                    sectionView(title: "When to Use", systemImage: "checkmark.circle") {
                        Text(detail.whenToUse)
                            .font(.callout)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    // When Not to Use
                    sectionView(title: "When Not to Use", systemImage: "xmark.circle") {
                        Text(detail.whenNotToUse)
                            .font(.callout)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    // Notes
                    if !detail.notes.isEmpty {
                        sectionView(title: "Notes", systemImage: "info.circle") {
                            Text(detail.notes)
                                .font(.callout)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    // References
                    if !detail.references.isEmpty {
                        sectionView(title: "References", systemImage: "book") {
                            VStack(alignment: .leading, spacing: 4) {
                                ForEach(detail.references, id: \.self) { ref in
                                    Text(ref)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }
                }
                .padding(20)
            }

            Divider()

            HStack {
                Spacer()
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 600, height: 580)
    }

    // MARK: - Helpers

    private func sectionView<Content: View>(
        title: String,
        systemImage: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                Label(title, systemImage: systemImage)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)

                content()
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func formulaText(_ text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            // Lines prefixed with $ are LaTeX formulas.
            // Lines prefixed with # are explanatory italic text.
            // Everything else is monospaced plain text.
            ForEach(Array(text.components(separatedBy: "\n").enumerated()), id: \.offset) { _, line in
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                if !trimmed.isEmpty {
                    if trimmed.hasPrefix("$") && trimmed.hasSuffix("$") && trimmed.count > 2 {
                        // Explicit LaTeX: $...$
                        let latex = String(trimmed.dropFirst().dropLast())
                        LaTeXView(latex)
                            .frame(height: 36)
                    } else if trimmed.hasPrefix("#") {
                        // Explanatory text in italic
                        Text(String(trimmed.dropFirst()).trimmingCharacters(in: .whitespaces))
                            .font(.callout)
                            .italic()
                            .foregroundStyle(.secondary)
                    } else if containsMathSymbols(trimmed) {
                        // Auto-detect lines with Unicode math and render as LaTeX
                        LaTeXView(unicodeToLatex(trimmed))
                            .frame(height: 36)
                    } else {
                        Text(trimmed)
                            .font(.system(.callout, design: .monospaced))
                    }
                }
            }
        }
    }

    /// Does this line contain Unicode math symbols that should be rendered as LaTeX?
    private func containsMathSymbols(_ line: String) -> Bool {
        let mathChars: [Character] = [
            "\u{03B1}", "\u{03B2}", "\u{03BC}", "\u{03C3}", "\u{03C7}",  // α β μ σ χ
            "\u{2211}", "\u{220F}", "\u{221A}",                           // Σ Π √
            "\u{2260}", "\u{2264}", "\u{2265}",                           // ≠ ≤ ≥
        ]
        // Must contain at least one math character
        return line.contains(where: { mathChars.contains($0) }) ||
               line.contains("x\u{0305}") ||  // x̄
               line.contains("R\u{0305}")      // R̄
    }

    /// Convert Unicode math notation to LaTeX.
    private func unicodeToLatex(_ text: String) -> String {
        var s = text
        // Greek letters
        s = s.replacingOccurrences(of: "\u{03B1}", with: "\\alpha ")
        s = s.replacingOccurrences(of: "\u{03B2}", with: "\\beta ")
        s = s.replacingOccurrences(of: "\u{03BC}", with: "\\mu ")
        s = s.replacingOccurrences(of: "\u{03C3}", with: "\\sigma ")
        s = s.replacingOccurrences(of: "\u{03C7}", with: "\\chi ")
        // Subscripts
        s = s.replacingOccurrences(of: "\u{2080}", with: "_0")
        s = s.replacingOccurrences(of: "\u{2081}", with: "_1")
        s = s.replacingOccurrences(of: "\u{2082}", with: "_2")
        s = s.replacingOccurrences(of: "\u{2083}", with: "_3")
        s = s.replacingOccurrences(of: "\u{1D62}", with: "_i")  // ᵢ
        // Superscripts
        s = s.replacingOccurrences(of: "\u{00B2}", with: "^2")
        // Operators
        s = s.replacingOccurrences(of: "\u{221A}", with: "\\sqrt")
        s = s.replacingOccurrences(of: "\u{2212}", with: "-")
        s = s.replacingOccurrences(of: "\u{2260}", with: "\\neq ")
        s = s.replacingOccurrences(of: "\u{2264}", with: "\\leq ")
        s = s.replacingOccurrences(of: "\u{2265}", with: "\\geq ")
        s = s.replacingOccurrences(of: "\u{2211}", with: "\\sum ")
        s = s.replacingOccurrences(of: "\u{220F}", with: "\\prod ")
        // Bars (x̄, R̄)
        s = s.replacingOccurrences(of: "x\u{0305}", with: "\\bar{x}")
        s = s.replacingOccurrences(of: "R\u{0305}", with: "\\bar{R}")
        // Dashes
        s = s.replacingOccurrences(of: "\u{2014}", with: "---")
        s = s.replacingOccurrences(of: "\u{2013}", with: "--")
        // H₀ / H₁ formatting
        s = s.replacingOccurrences(of: "H_0:", with: "H_0:\\;")
        s = s.replacingOccurrences(of: "H_1:", with: "H_1:\\;")
        return s
    }
}
