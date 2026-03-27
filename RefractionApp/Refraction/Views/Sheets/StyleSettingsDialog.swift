// StyleSettingsDialog.swift — Preset picker for render styles.
// Shows preview images for each style. Selecting a preset applies it immediately.
// Fine-tuning individual settings is done in Format Graph / Format Axes dialogs.

import SwiftUI

struct StyleSettingsDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    @State private var isApplying = false

    var body: some View {
        VStack(spacing: 0) {
            // Title
            Text("Choose Style")
                .font(.headline)
                .padding(12)

            Divider()

            if let graph = appState.activeGraph {
                ScrollView {
                    VStack(spacing: 12) {
                        Text("Select a preset to apply its visual theme. Use Format Graph and Format Axes for fine-tuning.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                            .padding(.top, 8)

                        LazyVGrid(columns: [
                            GridItem(.flexible(), spacing: 12),
                            GridItem(.flexible(), spacing: 12)
                        ], spacing: 12) {
                            ForEach(RenderStyle.allCases) { style in
                                StylePreviewCard(
                                    style: style,
                                    isSelected: graph.renderStyle == style,
                                    action: {
                                        graph.applyRenderStyle(style)
                                    }
                                )
                            }
                        }
                        .padding()
                    }
                }
                .frame(minHeight: 420)
            } else {
                Text("Select a graph first")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            Divider()

            // Bottom buttons
            HStack {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                Spacer()
                Button("Apply") {
                    DebugLog.shared.logUI("StyleSettingsDialog apply clicked")
                    isApplying = true
                    Task {
                        _ = try? await APIClient.shared.health()
                        DebugLog.shared.logAppEvent("StyleSettingsDialog apply — dummy server call completed")
                        isApplying = false
                    }
                }
                .disabled(isApplying)
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
            }
            .padding(12)
        }
        .frame(width: 480)
    }
}

// MARK: - Style Preview Card

private struct StylePreviewCard: View {
    let style: RenderStyle
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                // Preview image
                Group {
                    if let image = loadPreviewImage(for: style) {
                        Image(nsImage: image)
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                    } else {
                        // Fallback colored rectangle
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.2))
                            .overlay {
                                Text(style.label)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                    }
                }
                .frame(height: 150)
                .clipShape(RoundedRectangle(cornerRadius: 6))

                // Label
                Text(style.label)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(isSelected ? .white : .primary)

                // Description
                Text(style.description)
                    .font(.system(size: 10))
                    .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
            .padding(10)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(isSelected ? Color.accentColor : Color(nsColor: .controlBackgroundColor))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(isSelected ? Color.accentColor : Color.gray.opacity(0.3), lineWidth: isSelected ? 2 : 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func loadPreviewImage(for style: RenderStyle) -> NSImage? {
        let filename: String
        switch style {
        case .default:    filename = "style_default"
        case .prism:      filename = "style_prism"
        case .ggplot2:    filename = "style_ggplot2"
        case .matplotlib: filename = "style_matplotlib"
        }

        // Try loading from the bundle — may be in StylePreviews subfolder or at root of Resources
        if let url = Bundle.main.url(forResource: filename, withExtension: "png", subdirectory: "StylePreviews") {
            return NSImage(contentsOf: url)
        }
        if let url = Bundle.main.url(forResource: filename, withExtension: "png") {
            return NSImage(contentsOf: url)
        }
        return nil
    }
}
