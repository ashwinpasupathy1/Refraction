// HitRegion.swift — Describes a clickable region on the chart canvas.
// Computed by renderers alongside drawing, so positions are always in sync.

import Foundation

/// A clickable/hoverable region on the chart canvas.
public struct ChartHitRegion: Identifiable {
    public let id: String
    public let kind: Kind
    public let rect: CGRect
    public let groupIndex: Int
    public let groupName: String
    public let label: String       // display label for tooltip
    public let metadata: [String: String]  // extra info (mean, n, etc.)

    public enum Kind: String {
        case bar
        case box
        case point
        case line
        case violin
        case histogram
        case title
        case xLabel
        case yLabel
        case legend
        case bracket
    }

    public init(
        kind: Kind,
        rect: CGRect,
        groupIndex: Int,
        groupName: String,
        label: String = "",
        metadata: [String: String] = [:]
    ) {
        self.id = "\(kind.rawValue)_\(groupIndex)_\(groupName)"
        self.kind = kind
        self.rect = rect
        self.groupIndex = groupIndex
        self.groupName = groupName
        self.label = label
        self.metadata = metadata
    }
}
