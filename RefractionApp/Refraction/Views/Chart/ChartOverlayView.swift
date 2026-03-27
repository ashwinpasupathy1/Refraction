// ChartOverlayView.swift — Transparent interactive overlay on top of the chart canvas.
// Uses renderer-computed hit regions for click-to-select with tooltips,
// and click-to-edit title/axis labels. Logs all events to DebugLog.

import SwiftUI
import RefractionRenderer

struct ChartOverlayView: View {

    let spec: ChartSpec
    let plotInsets: EdgeInsets
    let graph: Graph

    @State private var selectedRegion: ChartHitRegion?
    @State private var hoveredRegion: ChartHitRegion?
    @State private var editingTitle = false
    @State private var editingXLabel = false
    @State private var editingYLabel = false

    var body: some View {
        GeometryReader { geometry in
            let size = geometry.size
            let plotRect = CGRect(
                x: plotInsets.leading,
                y: plotInsets.top,
                width: size.width - plotInsets.leading - plotInsets.trailing,
                height: size.height - plotInsets.top - plotInsets.bottom
            )
            let regions = computeHitRegions(plotRect: plotRect)

            ZStack(alignment: .topLeading) {
                // Transparent base to capture background clicks (deselect)
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        if selectedRegion != nil {
                            DebugLog.shared.logAppEvent("chart.deselect")
                        }
                        selectedRegion = nil
                        editingTitle = false
                        editingXLabel = false
                        editingYLabel = false
                    }

                // Data element hit regions
                ForEach(regions) { region in
                    Rectangle()
                        .fill(Color.clear)
                        .contentShape(Rectangle())
                        .frame(width: region.rect.width, height: region.rect.height)
                        .position(x: region.rect.midX, y: region.rect.midY)
                        .onTapGesture {
                            let isDeselect = selectedRegion?.id == region.id
                            selectedRegion = isDeselect ? nil : region
                            DebugLog.shared.logAppEvent(
                                "chart.tap(\(region.kind.rawValue))",
                                detail: "group: \(region.groupName), index: \(region.groupIndex), meta: \(region.metadata)"
                            )
                        }
                        .onHover { hovering in
                            hoveredRegion = hovering ? region : nil
                            if hovering {
                                DebugLog.shared.logAppEvent(
                                    "chart.hover(\(region.kind.rawValue))",
                                    detail: "group: \(region.groupName)"
                                )
                            }
                        }
                }

                // Selection highlight
                if let sel = selectedRegion {
                    RoundedRectangle(cornerRadius: 2)
                        .stroke(Color.accentColor, lineWidth: 2.5)
                        .frame(width: sel.rect.width + 4, height: sel.rect.height + 4)
                        .position(x: sel.rect.midX, y: sel.rect.midY)
                        .allowsHitTesting(false)
                }

                // Tooltip on hover
                if let hovered = hoveredRegion,
                   let group = spec.groups.first(where: { $0.name == hovered.groupName }) {
                    tooltipView(group: group, region: hovered)
                        .position(x: hovered.rect.midX, y: hovered.rect.minY - 40)
                        .allowsHitTesting(false)
                }

                // Editable title
                titleOverlay(size: size)

                // Editable X label
                xLabelOverlay(plotRect: plotRect, size: size)

                // Editable Y label
                yLabelOverlay(plotRect: plotRect, size: size)
            }
        }
    }

    // MARK: - Compute Hit Regions (dispatches to renderer)

    private func computeHitRegions(plotRect: CGRect) -> [ChartHitRegion] {
        var regions: [ChartHitRegion]
        switch spec.chartType {
        case "bar", "column_stats", "waterfall", "pyramid":
            regions = BarRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "box":
            regions = BoxRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "violin":
            regions = ViolinRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "scatter":
            regions = ScatterRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "line":
            regions = LineRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "histogram":
            regions = HistogramRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "before_after":
            regions = BeforeAfterRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "dot_plot", "subcolumn_scatter":
            regions = DotPlotRenderer.hitRegions(plotRect: plotRect, groups: spec.groups, style: spec.style)
        case "grouped_bar":
            regions = GroupedBarRenderer.hitRegions(plotRect: plotRect, spec: spec, style: spec.style)
        case "stacked_bar":
            regions = StackedBarRenderer.hitRegions(plotRect: plotRect, spec: spec, style: spec.style)
        case "kaplan_meier":
            regions = KaplanMeierRenderer.hitRegions(plotRect: plotRect, spec: spec, style: spec.style)
        default:
            // Fallback: column regions for any chart with groups
            guard !spec.groups.isEmpty else { return [] }
            let w = plotRect.width / CGFloat(spec.groups.count)
            regions = spec.groups.enumerated().map { i, g in
                ChartHitRegion(
                    kind: .bar,
                    rect: CGRect(x: plotRect.minX + w * CGFloat(i), y: plotRect.minY, width: w, height: plotRect.height),
                    groupIndex: i, groupName: g.name, label: g.name,
                    metadata: ["n": "\(g.values.n)"]
                )
            }
        }

        // Append bracket hit regions if brackets are visible
        if spec.style.showBrackets && !spec.brackets.isEmpty {
            regions += BracketRenderer.hitRegions(
                plotRect: plotRect,
                brackets: spec.brackets,
                groupCount: spec.groups.count,
                style: spec.style,
                groups: spec.groups
            )
        }

        return regions
    }

    // MARK: - Tooltip

    private func tooltipView(group: GroupData, region: ChartHitRegion) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(group.name)
                .font(.system(size: 11, weight: .semibold))
            ForEach(Array(region.metadata.sorted(by: { $0.key < $1.key })), id: \.key) { key, value in
                HStack(spacing: 4) {
                    Text("\(key):")
                        .foregroundStyle(.secondary)
                    Text(value)
                }
                .font(.system(size: 10, design: .monospaced))
            }
        }
        .padding(8)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 6))
        .shadow(color: .black.opacity(0.15), radius: 4)
    }

    // MARK: - Editable Title

    @ViewBuilder
    private func titleOverlay(size: CGSize) -> some View {
        let titleY: CGFloat = 12
        let titleX = size.width / 2

        if editingTitle {
            TextField("Chart Title", text: Bindable(graph).chartConfig.title)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 14, weight: .semibold))
                .multilineTextAlignment(.center)
                .frame(width: min(size.width - 40, 300))
                .position(x: titleX, y: titleY + 8)
                .onSubmit {
                    editingTitle = false
                    DebugLog.shared.logAppEvent("chart.editTitle", detail: "new: \(graph.chartConfig.title)")
                }
        } else if !spec.axes.title.isEmpty {
            Color.clear
                .frame(width: min(size.width - 40, 300), height: 24)
                .contentShape(Rectangle())
                .position(x: titleX, y: titleY + 8)
                .onTapGesture {
                    editingTitle = true
                    DebugLog.shared.logAppEvent("chart.tap(title)")
                }
                .onHover { h in
                    if h { NSCursor.iBeam.push() } else { NSCursor.pop() }
                }
        }
    }

    // MARK: - Editable X Label

    @ViewBuilder
    private func xLabelOverlay(plotRect: CGRect, size: CGSize) -> some View {
        let labelY = size.height - 8
        let labelX = plotRect.midX

        if editingXLabel {
            TextField("X Axis Label", text: Bindable(graph).chartConfig.xlabel)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12))
                .multilineTextAlignment(.center)
                .frame(width: min(plotRect.width, 250))
                .position(x: labelX, y: labelY)
                .onSubmit {
                    editingXLabel = false
                    DebugLog.shared.logAppEvent("chart.editXLabel", detail: "new: \(graph.chartConfig.xlabel)")
                }
        } else if !spec.axes.xLabel.isEmpty {
            Color.clear
                .frame(width: min(plotRect.width, 250), height: 20)
                .contentShape(Rectangle())
                .position(x: labelX, y: labelY)
                .onTapGesture {
                    editingXLabel = true
                    DebugLog.shared.logAppEvent("chart.tap(xLabel)")
                }
                .onHover { h in
                    if h { NSCursor.iBeam.push() } else { NSCursor.pop() }
                }
        }
    }

    // MARK: - Editable Y Label

    @ViewBuilder
    private func yLabelOverlay(plotRect: CGRect, size: CGSize) -> some View {
        let labelX: CGFloat = 14
        let labelY = plotRect.midY

        if editingYLabel {
            TextField("Y Axis Label", text: Bindable(graph).chartConfig.ylabel)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12))
                .frame(width: min(plotRect.height, 200))
                .position(x: labelX + 50, y: labelY)
                .onSubmit {
                    editingYLabel = false
                    DebugLog.shared.logAppEvent("chart.editYLabel", detail: "new: \(graph.chartConfig.ylabel)")
                }
        } else if !spec.axes.yLabel.isEmpty {
            Color.clear
                .frame(width: 20, height: min(plotRect.height, 200))
                .contentShape(Rectangle())
                .position(x: labelX, y: labelY)
                .onTapGesture {
                    editingYLabel = true
                    DebugLog.shared.logAppEvent("chart.tap(yLabel)")
                }
                .onHover { h in
                    if h { NSCursor.iBeam.push() } else { NSCursor.pop() }
                }
        }
    }
}
