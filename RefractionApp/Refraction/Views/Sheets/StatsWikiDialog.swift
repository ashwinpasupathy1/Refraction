// StatsWikiDialog.swift — Educational reference for statistical tests.
// Left sidebar with categories, right panel with searchable test cards.
// Matches the Architecture Guide navigation pattern.

import SwiftUI

// MARK: - Test Catalog Model

struct StatTestEntry: Identifiable {
    let id: String
    let name: String
    let description: String
    let whenToUse: String
    let assumptions: [String]
    let category: StatTestCategory
}

enum StatTestCategory: String, CaseIterable, Identifiable {
    case parametric = "Parametric"
    case nonparametric = "Nonparametric"
    case categorical = "Categorical"
    case correlation = "Correlation"
    case survival = "Survival"
    case correction = "Multiple Testing"
    case other = "Other"

    var id: String { rawValue }

    var fullLabel: String {
        switch self {
        case .parametric: return "Parametric (assumes normality)"
        case .nonparametric: return "Nonparametric (no normality assumption)"
        case .categorical: return "Categorical / Count data"
        case .correlation: return "Correlation & Regression"
        case .survival: return "Survival"
        case .correction: return "Multiple Testing Correction"
        case .other: return "Other"
        }
    }

    var sfSymbol: String {
        switch self {
        case .parametric: return "chart.bar.fill"
        case .nonparametric: return "chart.dots.scatter"
        case .categorical: return "tablecells"
        case .correlation: return "point.topleft.down.to.point.bottomright.curvepath"
        case .survival: return "heart.text.clipboard"
        case .correction: return "checkmark.shield"
        case .other: return "ellipsis.circle"
        }
    }
}

// MARK: - Dialog View

struct StatsWikiDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    @State private var recommendation: RecommendTestResponse?
    @State private var isLoading = true
    @State private var searchText = ""
    @State private var selectedCategory: StatTestCategory? = nil
    @State private var expandedEntryIDs: Set<String> = []
    @State private var selectedTestDetail: StatsTestDetail?

    private var table: DataTable? { appState.activeDataTable }

    private var filteredTests: [StatTestEntry] {
        let tests: [StatTestEntry]
        if let cat = selectedCategory {
            tests = Self.allTests.filter { $0.category == cat }
        } else {
            tests = Self.allTests
        }

        guard !searchText.isEmpty else { return tests }

        let query = searchText.lowercased()
        return tests.filter {
            $0.name.lowercased().contains(query) ||
            $0.description.lowercased().contains(query) ||
            $0.whenToUse.lowercased().contains(query) ||
            $0.assumptions.contains { $0.lowercased().contains(query) }
        }
    }

    /// Tests grouped by category, preserving order.
    private var groupedTests: [(StatTestCategory, [StatTestEntry])] {
        var result: [(StatTestCategory, [StatTestEntry])] = []
        for cat in StatTestCategory.allCases {
            let inCat = filteredTests.filter { $0.category == cat }
            if !inCat.isEmpty {
                result.append((cat, inCat))
            }
        }
        return result
    }

    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            HStack {
                Image(systemName: "book.fill")
                    .foregroundStyle(.cyan)
                Text("Statistics Guide")
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

            HSplitView {
                // MARK: - Left Sidebar: Categories
                VStack(alignment: .leading, spacing: 0) {
                    // "All" button
                    sidebarButton(
                        label: "All",
                        icon: "square.grid.2x2",
                        isSelected: selectedCategory == nil,
                        count: Self.allTests.count
                    ) {
                        selectedCategory = nil
                    }

                    Divider().padding(.vertical, 4)

                    // Category buttons
                    ForEach(StatTestCategory.allCases) { category in
                        let count = Self.allTests.filter { $0.category == category }.count
                        sidebarButton(
                            label: category.rawValue,
                            icon: category.sfSymbol,
                            isSelected: selectedCategory == category,
                            count: count
                        ) {
                            selectedCategory = category
                        }
                    }

                    Spacer()
                }
                .frame(minWidth: 160, maxWidth: 200)
                .padding(.vertical, 8)
                .background(Color(nsColor: .controlBackgroundColor))

                // MARK: - Right Content
                VStack(spacing: 0) {
                    // Search bar
                    HStack(spacing: 6) {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                        TextField("Search tests...", text: $searchText)
                            .textFieldStyle(.plain)
                            .font(.callout)
                        if !searchText.isEmpty {
                            Button {
                                searchText = ""
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.tertiary)
                            }
                            .buttonStyle(.plain)
                        }

                        Spacer()

                        Button("Expand All") {
                            expandedEntryIDs = Set(filteredTests.map(\.id))
                        }
                        .font(.caption)
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)

                        Button("Collapse All") {
                            expandedEntryIDs.removeAll()
                        }
                        .font(.caption)
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(.bar)

                    Divider()

                    // Content
                    if isLoading {
                        Spacer()
                        ProgressView("Analyzing data...")
                        Spacer()
                    } else {
                        ScrollView {
                            LazyVStack(alignment: .leading, spacing: 12) {
                                // Data diagnostics card (if data loaded)
                                if let checks = recommendation?.checks {
                                    yourDataCard(checks)
                                }

                                // Decision tree
                                if let rec = recommendation, rec.ok {
                                    decisionTreeCard(rec)
                                }

                                // Test cards grouped by category
                                ForEach(groupedTests, id: \.0) { category, tests in
                                    Text(category.fullLabel)
                                        .font(.subheadline)
                                        .fontWeight(.semibold)
                                        .foregroundStyle(.secondary)
                                        .padding(.top, 8)

                                    ForEach(tests) { test in
                                        testRow(test)
                                    }
                                }

                                if filteredTests.isEmpty {
                                    VStack(spacing: 8) {
                                        Image(systemName: "magnifyingglass")
                                            .font(.title)
                                            .foregroundStyle(.quaternary)
                                        Text("No matching tests")
                                            .foregroundStyle(.secondary)
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding(.top, 40)
                                }
                            }
                            .padding(16)
                        }
                    }
                }
            }

            Divider()

            HStack {
                Spacer()
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 850, height: 700)
        .sheet(item: $selectedTestDetail) { detail in
            StatsTestDetailDialog(detail: detail)
        }
        .task {
            await loadRecommendation()
        }
    }

    // MARK: - Sidebar Button

    private func sidebarButton(label: String, icon: String, isSelected: Bool, count: Int, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .frame(width: 16)
                Text(label)
                    .font(.caption)
                    .lineLimit(1)
                Spacer()
                Text("\(count)")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 1)
                    .background(.quaternary.opacity(0.5))
                    .clipShape(Capsule())
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 5)
            .background(isSelected ? Color.accentColor.opacity(0.15) : Color.clear)
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(isSelected ? .primary : .secondary)
    }

    // MARK: - Your Data Card

    private func yourDataCard(_ checks: DiagnosticChecks) -> some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                Label("Your Data", systemImage: "tablecells")
                    .font(.headline)

                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 6) {
                    GridRow {
                        Text("Groups:").foregroundStyle(.secondary)
                        Text("\(checks.nGroups)").fontWeight(.medium)
                    }
                    GridRow {
                        Text("Paired:").foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Image(systemName: checks.paired ? "checkmark.circle.fill" : "xmark.circle")
                                .foregroundStyle(checks.paired ? .green : .secondary)
                            Text(checks.paired ? "Yes" : "No")
                        }
                    }
                    GridRow {
                        Text("Normality:").foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Image(systemName: checks.allNormal ? "checkmark.circle.fill" : "xmark.circle")
                                .foregroundStyle(checks.allNormal ? .green : .orange)
                            Text(checks.allNormal ? "All groups normal" : "Not all groups normal")
                        }
                    }
                    GridRow {
                        Text("Equal variance:").foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Image(systemName: checks.equalVariance ? "checkmark.circle.fill" : "xmark.circle")
                                .foregroundStyle(checks.equalVariance ? .green : .orange)
                            if let lp = checks.leveneP {
                                Text("\(checks.equalVariance ? "Yes" : "No") (Levene's p = \(lp, specifier: "%.4f"))")
                            } else {
                                Text(checks.equalVariance ? "Yes" : "No")
                            }
                        }
                    }
                }

                if !checks.normality.isEmpty {
                    Divider()
                    Text("Normality per group (Shapiro-Wilk)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    ForEach(checks.normality.sorted(by: { $0.key < $1.key }), id: \.key) { name, result in
                        HStack(spacing: 6) {
                            Image(systemName: result.normal ? "checkmark.circle.fill" : "xmark.circle")
                                .foregroundStyle(result.normal ? .green : .orange)
                                .font(.caption)
                            Text(name)
                                .font(.caption)
                                .fontWeight(.medium)
                            if let p = result.p {
                                Text("p = \(p, specifier: "%.4f")")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            } else {
                                Text("n < 3")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Decision Tree Card

    private func decisionTreeCard(_ rec: RecommendTestResponse) -> some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                Label("Decision Path", systemImage: "arrow.triangle.branch")
                    .font(.headline)

                if let checks = rec.checks {
                    let steps = buildDecisionPath(checks, recommendedTest: rec.test)
                    ForEach(Array(steps.enumerated()), id: \.offset) { index, step in
                        HStack(spacing: 8) {
                            Image(systemName: step.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(step.passed ? .green : .orange)
                                .font(.callout)
                            Text(step.label)
                                .font(.callout)
                                .fontWeight(step.isFinal ? .bold : .regular)
                            if index < steps.count - 1 {
                                Spacer()
                                Image(systemName: "arrow.down")
                                    .foregroundStyle(.tertiary)
                                    .font(.caption2)
                            }
                        }
                    }
                }

                HStack(spacing: 6) {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.orange)
                    Text(rec.testLabel ?? rec.test ?? "Unknown")
                        .fontWeight(.semibold)
                }
                .padding(.top, 4)

                if let justification = rec.justification {
                    Text(justification)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Test Row

    private func testRow(_ test: StatTestEntry) -> some View {
        let applicability = checkApplicability(test)
        let isRecommended = test.id == recommendation?.test
        let isApplicable = applicability == nil
        let isExpanded = expandedEntryIDs.contains(test.id)

        return GroupBox {
            VStack(alignment: .leading, spacing: 6) {
                // Header — always visible, clickable to expand
                Button {
                    if expandedEntryIDs.contains(test.id) {
                        expandedEntryIDs.remove(test.id)
                    } else {
                        expandedEntryIDs.insert(test.id)
                    }
                } label: {
                    HStack {
                        Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .frame(width: 10)
                        Text(test.name)
                            .font(.callout)
                            .fontWeight(.semibold)
                            .foregroundStyle(isApplicable ? .primary : .secondary)
                        if isRecommended {
                            Label("Recommended", systemImage: "star.fill")
                                .font(.caption2)
                                .foregroundStyle(.orange)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(.orange.opacity(0.1))
                                .clipShape(Capsule())
                        }
                        Spacer()
                        if !isApplicable {
                            Image(systemName: "exclamationmark.triangle")
                                .foregroundStyle(.secondary)
                                .font(.caption)
                        }
                        if StatsTestCatalog.detail(for: test.id) != nil {
                            Button {
                                selectedTestDetail = StatsTestCatalog.detail(for: test.id)
                            } label: {
                                Image(systemName: "info.circle")
                                    .foregroundStyle(.blue)
                                    .font(.caption)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Text(test.description)
                    .font(.caption)
                    .foregroundStyle(isApplicable ? .primary : .tertiary)

                // Expanded detail
                if isExpanded {
                    Divider()

                    HStack(alignment: .top, spacing: 16) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("When to use")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                                .fontWeight(.medium)
                            Text(test.whenToUse)
                                .font(.caption2)
                                .foregroundStyle(isApplicable ? .secondary : .tertiary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Assumptions")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                                .fontWeight(.medium)
                            ForEach(test.assumptions, id: \.self) { assumption in
                                Text("- \(assumption)")
                                    .font(.caption2)
                                    .foregroundStyle(isApplicable ? .secondary : .tertiary)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if let reason = applicability {
                        Text(reason)
                            .font(.caption2)
                            .foregroundStyle(.orange)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(.orange.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .opacity(isApplicable ? 1.0 : 0.6)
    }

    // MARK: - Applicability Check

    private func checkApplicability(_ test: StatTestEntry) -> String? {
        guard let checks = recommendation?.checks else { return nil }

        let n = checks.nGroups
        let paired = checks.paired
        let normal = checks.allNormal

        switch test.id {
        case "unpaired_t":
            if n != 2 { return "Requires exactly 2 groups (you have \(n))" }
            if paired { return "Requires independent (unpaired) groups" }
            if !normal { return "Data not normally distributed" }
            if !checks.equalVariance { return "Unequal variances -- use Welch's t-test" }
        case "welch_t":
            if n != 2 { return "Requires exactly 2 groups (you have \(n))" }
            if paired { return "Requires independent (unpaired) groups" }
            if !normal { return "Data not normally distributed" }
        case "paired_t":
            if n != 2 { return "Requires exactly 2 groups (you have \(n))" }
            if !paired { return "Requires paired/matched data" }
            if !normal { return "Differences not normally distributed" }
        case "anova":
            if n < 3 { return "Requires 3+ groups (you have \(n))" }
            if paired { return "Requires independent groups" }
            if !normal { return "Data not normally distributed" }
            if !checks.equalVariance { return "Unequal variances -- use Welch's ANOVA" }
        case "welch_anova":
            if n < 3 { return "Requires 3+ groups (you have \(n))" }
            if paired { return "Requires independent groups" }
            if !normal { return "Data not normally distributed" }
        case "repeated_measures_anova":
            if n < 3 { return "Requires 3+ groups (you have \(n))" }
            if !paired { return "Requires paired/repeated measures data" }
        case "two_way_anova":
            if n < 2 { return "Requires structured factorial data" }
        case "mann_whitney":
            if n != 2 { return "Requires exactly 2 groups (you have \(n))" }
            if paired { return "Requires independent groups" }
        case "wilcoxon":
            if n != 2 { return "Requires exactly 2 groups (you have \(n))" }
            if !paired { return "Requires paired/matched data" }
        case "kruskal_wallis":
            if n < 3 { return "Requires 3+ groups (you have \(n))" }
            if paired { return "Requires independent groups" }
        case "friedman":
            if n < 3 { return "Requires 3+ groups (you have \(n))" }
            if !paired { return "Requires paired/repeated measures data" }
        case "chi_square":
            return "Requires contingency table data"
        case "fisher_exact":
            return "Requires 2x2 contingency table data"
        case "chi_square_gof":
            return "Requires observed vs expected frequency data"
        case "mcnemar":
            return "Requires paired categorical data"
        case "pearson":
            if n < 2 { return "Requires XY data with 2+ data points" }
        case "spearman":
            if n < 2 { return "Requires XY data with 2+ data points" }
        case "linear_regression":
            if n < 2 { return "Requires XY data" }
        case "multiple_regression":
            return "Requires multiple predictor variables"
        case "log_rank":
            return "Requires time-to-event survival data"
        case "gehan_wilcoxon":
            return "Requires time-to-event survival data"
        case "cox_ph":
            return "Requires time-to-event survival data with covariates"
        case "one_sample_t":
            break
        case "permutation":
            if n < 2 { return "Requires 2+ groups (you have \(n))" }
        case "ks_test":
            break
        default:
            break
        }
        return nil
    }

    // MARK: - Decision Path Builder

    private struct DecisionStep {
        let label: String
        let passed: Bool
        let isFinal: Bool
    }

    private func buildDecisionPath(_ checks: DiagnosticChecks, recommendedTest: String?) -> [DecisionStep] {
        var steps: [DecisionStep] = []

        if checks.nGroups == 1 {
            steps.append(DecisionStep(label: "1 group", passed: true, isFinal: false))
            steps.append(DecisionStep(label: "Descriptive statistics only", passed: true, isFinal: true))
            return steps
        } else if checks.nGroups == 2 {
            steps.append(DecisionStep(label: "2 groups", passed: true, isFinal: false))
        } else {
            steps.append(DecisionStep(label: "\(checks.nGroups) groups (3+)", passed: true, isFinal: false))
        }

        steps.append(DecisionStep(
            label: checks.paired ? "Paired / related" : "Independent",
            passed: true, isFinal: false
        ))

        steps.append(DecisionStep(
            label: checks.allNormal ? "Normal distribution" : "Not normal",
            passed: checks.allNormal, isFinal: false
        ))

        if checks.allNormal && !checks.paired {
            steps.append(DecisionStep(
                label: checks.equalVariance ? "Equal variance" : "Unequal variance",
                passed: checks.equalVariance, isFinal: false
            ))
        }

        if let label = recommendedTest {
            let humanLabel = Self.allTests.first(where: { $0.id == label })?.name ?? label
            steps.append(DecisionStep(label: humanLabel, passed: true, isFinal: true))
        }

        return steps
    }

    // MARK: - Load Data

    private func loadRecommendation() async {
        guard let table, table.hasData else {
            isLoading = false
            return
        }
        do {
            recommendation = try await APIClient.shared.recommendTest(
                inlineData: table.toAnalyzePayload(),
                paired: table.tableType == .comparison,
                tableType: table.tableType.rawValue
            )
        } catch {
            recommendation = nil
        }
        isLoading = false
    }

    // MARK: - Complete Test Catalog

    static let allTests: [StatTestEntry] = [
        // Parametric
        StatTestEntry(id: "unpaired_t", name: "Unpaired t-test",
            description: "Compare means of 2 independent groups.",
            whenToUse: "Two unrelated groups, continuous outcome, normal data with equal variance.",
            assumptions: ["Normality", "Equal variance", "Independent observations"],
            category: .parametric),
        StatTestEntry(id: "welch_t", name: "Welch's t-test",
            description: "Compare means of 2 independent groups without assuming equal variance.",
            whenToUse: "Two unrelated groups, normal data but variances may differ.",
            assumptions: ["Normality", "Independent observations"],
            category: .parametric),
        StatTestEntry(id: "paired_t", name: "Paired t-test",
            description: "Compare means of 2 related or matched groups.",
            whenToUse: "Before/after measurements, matched pairs, or repeated measures on same subjects.",
            assumptions: ["Normally distributed differences", "Paired observations"],
            category: .parametric),
        StatTestEntry(id: "anova", name: "One-way ANOVA",
            description: "Compare means of 3 or more independent groups.",
            whenToUse: "Three+ unrelated groups with a single factor. Use Tukey HSD for posthoc.",
            assumptions: ["Normality", "Equal variance", "Independent observations"],
            category: .parametric),
        StatTestEntry(id: "welch_anova", name: "Welch's ANOVA",
            description: "Compare means of 3+ independent groups with unequal variance.",
            whenToUse: "Three+ groups when Levene's test rejects equal variance. Use Games-Howell for posthoc.",
            assumptions: ["Normality", "Independent observations"],
            category: .parametric),
        StatTestEntry(id: "repeated_measures_anova", name: "Repeated measures ANOVA",
            description: "Compare means of 3+ related groups (same subjects measured multiple times).",
            whenToUse: "Longitudinal data or multiple conditions on same subjects.",
            assumptions: ["Normality", "Sphericity", "Paired observations"],
            category: .parametric),
        StatTestEntry(id: "two_way_anova", name: "Two-way ANOVA",
            description: "Test effects of two factors and their interaction.",
            whenToUse: "Data classified by two categorical factors (e.g., drug x dose).",
            assumptions: ["Normality", "Equal variance", "Independent observations"],
            category: .parametric),

        // Nonparametric
        StatTestEntry(id: "mann_whitney", name: "Mann-Whitney U",
            description: "Compare distributions of 2 independent groups.",
            whenToUse: "Alternative to unpaired t-test when normality is violated.",
            assumptions: ["Independent observations", "Similar distribution shapes"],
            category: .nonparametric),
        StatTestEntry(id: "wilcoxon", name: "Wilcoxon signed-rank",
            description: "Compare 2 related groups using ranks.",
            whenToUse: "Alternative to paired t-test when differences are not normally distributed.",
            assumptions: ["Paired observations", "Symmetric difference distribution"],
            category: .nonparametric),
        StatTestEntry(id: "kruskal_wallis", name: "Kruskal-Wallis",
            description: "Compare distributions of 3 or more independent groups.",
            whenToUse: "Alternative to one-way ANOVA when normality is violated. Use Dunn's test for posthoc.",
            assumptions: ["Independent observations", "Ordinal or continuous data"],
            category: .nonparametric),
        StatTestEntry(id: "friedman", name: "Friedman test",
            description: "Compare 3 or more related groups using ranks.",
            whenToUse: "Alternative to repeated measures ANOVA for non-normal data.",
            assumptions: ["Paired/repeated observations", "Ordinal or continuous data"],
            category: .nonparametric),

        // Categorical
        StatTestEntry(id: "chi_square", name: "Chi-square test of independence",
            description: "Test association between two categorical variables.",
            whenToUse: "Contingency table with expected counts >= 5 in each cell.",
            assumptions: ["Independent observations", "Expected counts >= 5"],
            category: .categorical),
        StatTestEntry(id: "fisher_exact", name: "Fisher's exact test",
            description: "Like chi-square but exact, for small sample sizes.",
            whenToUse: "2x2 contingency tables with small expected counts.",
            assumptions: ["Independent observations", "2x2 table"],
            category: .categorical),
        StatTestEntry(id: "chi_square_gof", name: "Chi-square goodness of fit",
            description: "Test if observed frequencies match expected distribution.",
            whenToUse: "One categorical variable, comparing to theoretical distribution.",
            assumptions: ["Independent observations", "Expected counts >= 5"],
            category: .categorical),
        StatTestEntry(id: "mcnemar", name: "McNemar's test",
            description: "Paired categorical data (before/after on same subjects).",
            whenToUse: "Matched pairs with binary outcome.",
            assumptions: ["Paired observations", "Binary outcome"],
            category: .categorical),

        // Correlation & Regression
        StatTestEntry(id: "pearson", name: "Pearson correlation",
            description: "Measure linear relationship between two continuous variables.",
            whenToUse: "Both variables are continuous, normally distributed, and linearly related.",
            assumptions: ["Normality", "Linear relationship", "Continuous data"],
            category: .correlation),
        StatTestEntry(id: "spearman", name: "Spearman correlation",
            description: "Measure monotonic relationship between variables.",
            whenToUse: "Nonparametric alternative to Pearson. Works with ordinal data.",
            assumptions: ["Monotonic relationship", "Ordinal or continuous data"],
            category: .correlation),
        StatTestEntry(id: "linear_regression", name: "Simple linear regression",
            description: "Predict Y from X. Returns slope, intercept, and R-squared.",
            whenToUse: "Model a linear relationship between a predictor and outcome.",
            assumptions: ["Linearity", "Normality of residuals", "Homoscedasticity"],
            category: .correlation),
        StatTestEntry(id: "multiple_regression", name: "Multiple regression",
            description: "Predict Y from multiple X variables.",
            whenToUse: "Model outcome from several predictors simultaneously.",
            assumptions: ["Linearity", "No multicollinearity", "Normal residuals"],
            category: .correlation),

        // Survival
        StatTestEntry(id: "log_rank", name: "Log-rank test",
            description: "Compare survival curves between groups.",
            whenToUse: "Time-to-event data with two or more groups and possible censoring.",
            assumptions: ["Non-informative censoring", "Proportional hazards"],
            category: .survival),
        StatTestEntry(id: "gehan_wilcoxon", name: "Gehan-Wilcoxon test",
            description: "Like log-rank but weights early events more heavily.",
            whenToUse: "When early differences between survival curves are more important.",
            assumptions: ["Non-informative censoring"],
            category: .survival),
        StatTestEntry(id: "cox_ph", name: "Cox proportional hazards",
            description: "Regression model for survival data with covariates.",
            whenToUse: "Survival analysis adjusting for multiple predictors.",
            assumptions: ["Proportional hazards", "Non-informative censoring"],
            category: .survival),

        // Multiple Testing Correction
        StatTestEntry(id: "bonferroni", name: "Bonferroni correction",
            description: "Divide significance threshold by the number of comparisons. Most conservative.",
            whenToUse: "Few comparisons where controlling family-wise error rate is critical.",
            assumptions: ["Independent tests (conservative if dependent)"],
            category: .correction),
        StatTestEntry(id: "holm_bonferroni", name: "Holm-Bonferroni (step-down)",
            description: "Sequential rejection: order p-values and compare to progressively less strict thresholds.",
            whenToUse: "Default recommendation. Uniformly more powerful than Bonferroni while controlling FWER.",
            assumptions: ["Valid for any dependency structure"],
            category: .correction),
        StatTestEntry(id: "sidak", name: "\u{0160}id\u{00E1}k correction",
            description: "Like Bonferroni but slightly less conservative: threshold = 1 - (1 - \u{03B1})^(1/m).",
            whenToUse: "Independent tests where slightly more power than Bonferroni is desired.",
            assumptions: ["Independent tests"],
            category: .correction),
        StatTestEntry(id: "hochberg", name: "Hochberg (step-up)",
            description: "Step-up version: start from largest p-value, accept all below threshold.",
            whenToUse: "When tests are independent or positively correlated. More powerful than Holm.",
            assumptions: ["Independent or positively dependent tests"],
            category: .correction),
        StatTestEntry(id: "benjamini_hochberg", name: "Benjamini-Hochberg (FDR)",
            description: "Controls false discovery rate instead of family-wise error rate. Much more powerful.",
            whenToUse: "Exploratory analyses, genomics, or when many tests are performed.",
            assumptions: ["Independent or positively dependent tests"],
            category: .correction),
        StatTestEntry(id: "tukey_hsd", name: "Tukey's HSD",
            description: "Post-hoc pairwise comparisons after ANOVA. Controls FWER for all pairwise tests.",
            whenToUse: "After significant one-way ANOVA with equal group sizes.",
            assumptions: ["Normality", "Equal variance", "Equal sample sizes (approximately)"],
            category: .correction),
        StatTestEntry(id: "dunnett", name: "Dunnett's test",
            description: "Compare each treatment group to a single control group.",
            whenToUse: "When only comparisons to a control are of interest.",
            assumptions: ["Normality", "Equal variance", "Designated control group"],
            category: .correction),
        StatTestEntry(id: "dunn", name: "Dunn's test",
            description: "Nonparametric posthoc pairwise comparisons after Kruskal-Wallis.",
            whenToUse: "After significant Kruskal-Wallis when data are not normally distributed.",
            assumptions: ["Independent observations", "Ordinal or continuous data"],
            category: .correction),

        // Other
        StatTestEntry(id: "one_sample_t", name: "One-sample t-test",
            description: "Compare a group mean to a known or hypothesized value.",
            whenToUse: "Testing whether a sample mean differs from a specific number.",
            assumptions: ["Normality", "Continuous data"],
            category: .other),
        StatTestEntry(id: "permutation", name: "Permutation test",
            description: "Distribution-free test using resampling.",
            whenToUse: "When parametric assumptions are questionable.",
            assumptions: ["Exchangeability under null hypothesis"],
            category: .other),
        StatTestEntry(id: "ks_test", name: "Kolmogorov-Smirnov test",
            description: "Compare two distributions or test normality.",
            whenToUse: "Testing whether a sample follows a specific distribution.",
            assumptions: ["Continuous data"],
            category: .other),
    ]
}
