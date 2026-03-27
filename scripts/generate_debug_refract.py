#!/usr/bin/env python3
"""Generate a debug.refract directory bundle with sample data for every chart type."""

import json
import os
import random
import time
import uuid
import math

# Seed for reproducibility
random.seed(42)

# Output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "debug.refract")


def uid():
    return str(uuid.uuid4()).upper()


def normal(mu, sigma, n):
    """Generate n normally-distributed values using Box-Muller."""
    vals = []
    while len(vals) < n:
        u1, u2 = random.random(), random.random()
        z0 = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        vals.append(round(mu + sigma * z0, 2))
    return vals


def make_data_json(columns, rows):
    """Build the data JSON dict (columns + rows with typed values)."""
    return {"columns": columns, "rows": rows}


# ---------------------------------------------------------------------------
# Chart type definitions: (chart_type, table_type, label, data_builder)
# Each data_builder returns (columns, rows)
# ---------------------------------------------------------------------------

def bar_data():
    cols = ["Control", "Drug A", "Drug B"]
    rows = []
    for i in range(8):
        rows.append([
            round(random.gauss(5.0, 1.2), 2),
            round(random.gauss(8.5, 1.5), 2),
            round(random.gauss(7.0, 1.0), 2),
        ])
    return cols, rows


def line_data():
    cols = ["Time (h)", "Plasma (ng/mL)", "Tissue (ng/mL)"]
    rows = []
    for t in range(0, 25, 2):
        plasma = round(100 * math.exp(-0.15 * t) + random.gauss(0, 3), 2)
        tissue = round(60 * (1 - math.exp(-0.2 * t)) * math.exp(-0.05 * t) + random.gauss(0, 2), 2)
        rows.append([t, max(0, plasma), max(0, tissue)])
    return cols, rows


def grouped_bar_data():
    cols = ["Category", "Placebo", "Low Dose", "High Dose"]
    categories = ["Week 1", "Week 2", "Week 4"]
    rows = []
    for cat in categories:
        rows.append([
            cat,
            round(random.gauss(3.0, 0.8), 2),
            round(random.gauss(5.5, 1.0), 2),
            round(random.gauss(8.0, 1.2), 2),
        ])
    return cols, rows


def box_data():
    cols = ["Saline", "Drug A", "Drug B", "Drug C"]
    rows = []
    for i in range(12):
        rows.append([
            round(random.gauss(10, 3), 2),
            round(random.gauss(15, 4), 2),
            round(random.gauss(12, 2.5), 2),
            round(random.gauss(18, 5), 2),
        ])
    return cols, rows


def scatter_data():
    cols = ["Age (years)", "Biomarker (U/L)"]
    rows = []
    for _ in range(20):
        age = round(random.uniform(20, 75), 1)
        biomarker = round(0.8 * age + random.gauss(0, 10), 2)
        rows.append([age, biomarker])
    return cols, rows


def violin_data():
    cols = ["Control", "Treatment A", "Treatment B"]
    rows = []
    for i in range(30):
        rows.append([
            round(random.gauss(50, 10), 2),
            round(random.gauss(65, 12), 2),
            round(random.gauss(55, 8), 2),
        ])
    return cols, rows


def kaplan_meier_data():
    cols = ["Control Time", "Control Event", "Treated Time", "Treated Event"]
    rows = []
    for i in range(20):
        ct = round(random.uniform(1, 24), 1)
        ce = 1 if random.random() < 0.7 else 0
        tt = round(random.uniform(3, 36), 1)
        te = 1 if random.random() < 0.5 else 0
        rows.append([ct, ce, tt, te])
    return cols, rows


def heatmap_data():
    cols = ["Gene", "Sample 1", "Sample 2", "Sample 3", "Sample 4", "Sample 5"]
    genes = ["BRCA1", "TP53", "EGFR", "MYC", "KRAS", "PTEN", "AKT1", "PIK3CA"]
    rows = []
    for gene in genes:
        row = [gene]
        for _ in range(5):
            row.append(round(random.gauss(0, 2), 2))
        rows.append(row)
    return cols, rows


def two_way_anova_data():
    cols = ["Factor_A", "Factor_B", "Value"]
    rows = []
    for a in ["Male", "Female"]:
        for b in ["Placebo", "Low", "High"]:
            for _ in range(5):
                base = 10 + (5 if a == "Female" else 0) + (3 if b == "Low" else 8 if b == "High" else 0)
                rows.append([a, b, round(random.gauss(base, 2), 2)])
    return cols, rows


def before_after_data():
    cols = ["Before", "After"]
    rows = []
    for _ in range(10):
        before = round(random.gauss(120, 15), 1)
        after = round(before - random.gauss(10, 5), 1)
        rows.append([before, after])
    return cols, rows


def histogram_data():
    cols = ["Reaction Time (ms)"]
    rows = [[round(random.gauss(350, 60), 1)] for _ in range(50)]
    return cols, rows


def subcolumn_scatter_data():
    cols = ["Group A", "Group B", "Group C"]
    rows = []
    for i in range(8):
        rows.append([
            round(random.gauss(25, 5), 2),
            round(random.gauss(30, 6), 2),
            round(random.gauss(22, 4), 2),
        ])
    return cols, rows


def curve_fit_data():
    cols = ["Concentration (uM)", "Response (%)"]
    rows = []
    for conc in [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]:
        response = round(100 / (1 + (1.0 / conc) ** 1.2) + random.gauss(0, 3), 2)
        rows.append([conc, max(0, min(100, response))])
    return cols, rows


def column_stats_data():
    cols = ["Vehicle", "Compound X", "Compound Y"]
    rows = []
    for _ in range(10):
        rows.append([
            round(random.gauss(100, 15), 2),
            round(random.gauss(130, 20), 2),
            round(random.gauss(115, 12), 2),
        ])
    return cols, rows


def contingency_data():
    cols = ["", "Improved", "No Change", "Worsened"]
    rows = [
        ["Drug", 45, 30, 10],
        ["Placebo", 20, 35, 25],
    ]
    return cols, rows


def repeated_measures_data():
    cols = ["Baseline", "Week 4", "Week 8"]
    rows = []
    for _ in range(8):
        base = round(random.gauss(80, 10), 1)
        rows.append([
            base,
            round(base - random.gauss(5, 3), 1),
            round(base - random.gauss(12, 4), 1),
        ])
    return cols, rows


def chi_square_gof_data():
    cols = ["Category", "Observed", "Expected"]
    categories = ["A", "B", "C", "D", "E"]
    rows = []
    for cat in categories:
        obs = random.randint(15, 45)
        exp = 30
        rows.append([cat, obs, exp])
    return cols, rows


def stacked_bar_data():
    cols = ["Region", "Product A", "Product B", "Product C"]
    regions = ["North", "South", "East"]
    rows = []
    for region in regions:
        rows.append([
            region,
            round(random.uniform(10, 40), 1),
            round(random.uniform(15, 35), 1),
            round(random.uniform(5, 25), 1),
        ])
    return cols, rows


def bubble_data():
    cols = ["GDP per capita ($K)", "Life Expectancy (yr)", "Population (M)"]
    rows = []
    for _ in range(15):
        gdp = round(random.uniform(5, 80), 1)
        life_exp = round(60 + 0.2 * gdp + random.gauss(0, 3), 1)
        pop = round(random.uniform(1, 300), 1)
        rows.append([gdp, life_exp, pop])
    return cols, rows


def dot_plot_data():
    cols = ["Wild Type", "Mutant A", "Mutant B", "Mutant C"]
    rows = []
    for _ in range(8):
        rows.append([
            round(random.gauss(45, 8), 2),
            round(random.gauss(32, 10), 2),
            round(random.gauss(55, 7), 2),
            round(random.gauss(40, 9), 2),
        ])
    return cols, rows


def bland_altman_data():
    cols = ["Method A", "Method B"]
    rows = []
    for _ in range(20):
        true_val = random.gauss(100, 20)
        rows.append([
            round(true_val + random.gauss(0, 5), 2),
            round(true_val + random.gauss(2, 6), 2),
        ])
    return cols, rows


def forest_plot_data():
    cols = ["Study", "Effect", "Lower CI", "Upper CI"]
    studies = ["Smith 2018", "Jones 2019", "Chen 2020", "Park 2021",
               "Garcia 2022", "Kim 2023", "Brown 2024"]
    rows = []
    for study in studies:
        effect = round(random.gauss(0.5, 0.3), 3)
        width = round(random.uniform(0.1, 0.4), 3)
        rows.append([study, effect, round(effect - width, 3), round(effect + width, 3)])
    return cols, rows


def area_chart_data():
    cols = ["Month", "Revenue ($K)", "Costs ($K)"]
    rows = []
    for m in range(1, 13):
        revenue = round(50 + 5 * m + random.gauss(0, 5), 2)
        costs = round(30 + 2 * m + random.gauss(0, 3), 2)
        rows.append([m, revenue, costs])
    return cols, rows


def raincloud_data():
    cols = ["Condition A", "Condition B", "Condition C"]
    rows = []
    for _ in range(20):
        rows.append([
            round(random.gauss(70, 12), 2),
            round(random.gauss(85, 10), 2),
            round(random.gauss(75, 15), 2),
        ])
    return cols, rows


def qq_plot_data():
    cols = ["Sample Values"]
    rows = [[round(random.gauss(0, 1), 3)] for _ in range(30)]
    return cols, rows


def lollipop_data():
    cols = ["Category A", "Category B", "Category C"]
    rows = [[
        round(random.uniform(15, 85), 1),
        round(random.uniform(20, 90), 1),
        round(random.uniform(10, 75), 1),
    ]]
    return cols, rows


def waterfall_data():
    cols = ["Category", "Value"]
    rows = [
        ["Starting Balance", 100],
        ["Sales Revenue", 45],
        ["Service Income", 20],
        ["COGS", -30],
        ["Salaries", -25],
        ["Marketing", -10],
        ["Rent", -8],
        ["Net Profit", None],
    ]
    return cols, rows


def pyramid_data():
    cols = ["Age Group", "Male", "Female"]
    age_groups = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
    rows = []
    for ag in age_groups:
        rows.append([
            ag,
            random.randint(300, 800),
            random.randint(300, 800),
        ])
    return cols, rows


def ecdf_data():
    cols = ["Placebo", "Active Drug"]
    rows = []
    for _ in range(20):
        rows.append([
            round(random.gauss(50, 15), 2),
            round(random.gauss(65, 12), 2),
        ])
    return cols, rows


# ---------------------------------------------------------------------------
# Registry: chart_type -> (table_type, label, data_fn)
# ---------------------------------------------------------------------------

CHART_TYPES = {
    "bar":               ("column",      "Bar Chart",              bar_data),
    "line":              ("xy",          "Line Graph",             line_data),
    "grouped_bar":       ("grouped",     "Grouped Bar",            grouped_bar_data),
    "box":               ("column",      "Box Plot",               box_data),
    "scatter":           ("xy",          "Scatter Plot",           scatter_data),
    "violin":            ("column",      "Violin Plot",            violin_data),
    "kaplan_meier":      ("survival",    "Survival Curve",         kaplan_meier_data),
    "heatmap":           ("grouped",     "Heatmap",                heatmap_data),
    "two_way_anova":     ("twoWay",      "Two-Way ANOVA",          two_way_anova_data),
    "before_after":      ("comparison",  "Before / After",         before_after_data),
    "histogram":         ("column",      "Histogram",              histogram_data),
    "subcolumn_scatter": ("column",      "Subcolumn Scatter",      subcolumn_scatter_data),
    "curve_fit":         ("xy",          "Curve Fit",              curve_fit_data),
    "column_stats":      ("column",      "Column Statistics",      column_stats_data),
    "contingency":       ("contingency", "Contingency Table",      contingency_data),
    "repeated_measures": ("comparison",  "Repeated Measures",      repeated_measures_data),
    "chi_square_gof":    ("column",      "Chi-Square GoF",         chi_square_gof_data),
    "stacked_bar":       ("grouped",     "Stacked Bar",            stacked_bar_data),
    "bubble":            ("xy",          "Bubble Chart",           bubble_data),
    "dot_plot":          ("column",      "Dot Plot",               dot_plot_data),
    "bland_altman":      ("comparison",  "Bland-Altman",           bland_altman_data),
    "forest_plot":       ("meta",        "Forest Plot",            forest_plot_data),
    "area_chart":        ("xy",          "Area Chart",             area_chart_data),
    "raincloud":         ("column",      "Raincloud",              raincloud_data),
    "qq_plot":           ("column",      "Q-Q Plot",               qq_plot_data),
    "lollipop":          ("column",      "Lollipop",               lollipop_data),
    "waterfall":         ("parts",       "Waterfall",              waterfall_data),
    "pyramid":           ("column",      "Pyramid",                pyramid_data),
    "ecdf":              ("column",      "ECDF",                   ecdf_data),
}


def build_project():
    """Build the full project dict and data files."""
    now = time.time()
    experiments = []
    data_files = {}  # table_id -> data_json

    for chart_type, (table_type, label, data_fn) in CHART_TYPES.items():
        exp_id = uid()
        table_id = uid()
        graph_id = uid()

        columns, rows = data_fn()

        # Store data file
        data_files[table_id] = make_data_json(columns, rows)

        experiment = {
            "id": exp_id,
            "label": label,
            "description": f"Sample data for {label} ({chart_type})",
            "info": "",
            "createdAt": now,
            "lastModifiedAt": now,
            "dataTables": [{
                "id": table_id,
                "label": f"{label} Data",
                "tableType": table_type,
                "hasData": True,
            }],
            "graphs": [{
                "id": graph_id,
                "label": label,
                "dataTableID": table_id,
                "chartType": chart_type,
                "chartConfig": {},
            }],
            "analyses": [],
        }
        experiments.append(experiment)

    project_json = {
        "format_version": 4,
        "experiments": experiments,
        "activeExperimentID": experiments[0]["id"] if experiments else "",
        "activeItemID": "",
        "activeItemKind": "",
    }

    return project_json, data_files


def write_bundle(output_dir, project_json, data_files):
    """Write the .refract directory bundle to disk."""
    os.makedirs(output_dir, exist_ok=True)
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Write project.json
    project_path = os.path.join(output_dir, "project.json")
    with open(project_path, "w") as f:
        json.dump(project_json, f, indent=2, sort_keys=True)

    # Write each data table
    for table_id, data_json in data_files.items():
        table_path = os.path.join(data_dir, f"{table_id}.json")
        with open(table_path, "w") as f:
            json.dump(data_json, f, indent=2, sort_keys=True)

    return output_dir


def main():
    print(f"Generating debug.refract bundle at: {OUTPUT_DIR}")
    project_json, data_files = build_project()
    write_bundle(OUTPUT_DIR, project_json, data_files)
    print(f"  Created project.json with {len(project_json['experiments'])} experiments")
    print(f"  Created {len(data_files)} data files in data/")
    print(f"  Chart types: {', '.join(CHART_TYPES.keys())}")
    print("Done.")


if __name__ == "__main__":
    main()
