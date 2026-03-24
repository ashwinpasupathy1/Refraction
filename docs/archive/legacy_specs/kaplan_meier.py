"""Builds a Plotly figure spec for Kaplan-Meier survival curves."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error


def build_kaplan_meier_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, xlabel="Time", ytitle="Survival Probability")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"], header=None)
    if err:
        return err

    # Each group spans 2 columns: header row has group name repeated.
    # Row 1: "Time", "Event". Rows 2+: time value, 0/1.
    n_cols = df.shape[1]
    traces = []
    col = 0
    group_idx = 0

    while col + 1 < n_cols:
        group_name = str(df.iloc[0, col])
        # Row 1 should be "Time", "Event" headers -- skip it
        times = pd.to_numeric(df.iloc[2:, col], errors="coerce").dropna()
        events = pd.to_numeric(df.iloc[2:, col + 1], errors="coerce")
        events = events.iloc[: len(times)].fillna(0).astype(int)

        if times.empty:
            col += 2
            group_idx += 1
            continue

        # Compute Kaplan-Meier step function
        time_vals = times.values
        event_vals = events.values
        order = time_vals.argsort()
        time_vals = time_vals[order]
        event_vals = event_vals[order]

        n_at_risk = len(time_vals)
        km_times = [0.0]
        km_surv = [1.0]
        censor_times = []
        censor_surv = []
        current_surv = 1.0

        i = 0
        while i < len(time_vals):
            t = time_vals[i]
            # Collect all rows at this time point
            j = i
            while j < len(time_vals) and time_vals[j] == t:
                j += 1
            d = event_vals[i:j].sum()  # deaths
            c = (j - i) - d           # censored
            if d > 0:
                current_surv *= (n_at_risk - d) / n_at_risk
                km_times.append(t)
                km_surv.append(current_surv)
            # Record censored marks at current survival
            for _ in range(c):
                censor_times.append(t)
                censor_surv.append(current_surv)
            n_at_risk -= (j - i)
            i = j

        color = PRISM_PALETTE[group_idx % len(PRISM_PALETTE)]

        traces.append(go.Scatter(
            x=km_times,
            y=km_surv,
            mode="lines",
            line=dict(shape="hv", color=color, width=2),
            name=group_name,
        ))

        if censor_times:
            traces.append(go.Scatter(
                x=censor_times,
                y=censor_surv,
                mode="markers",
                marker=dict(symbol="cross", size=8, color=color),
                name=f"{group_name} (censored)",
                showlegend=False,
            ))

        col += 2
        group_idx += 1

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"], range=[0, 1.05]),
    ))
    return fig.to_json()
