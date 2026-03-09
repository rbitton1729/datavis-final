# exploration_charts.py
import altair as alt
import pandas as pd
import pycountry
from vega_datasets import data

alt.data_transformers.disable_max_rows()

# ----------------------------
# Helpers
# ----------------------------
def load_local_grapher(path, value_name):
    t = pd.read_csv(path)
    value_col = [c for c in t.columns if c not in ["Entity", "Code", "Year"]][0]
    return t.rename(columns={value_col: value_name})

def prep_owid(df, value_cols):
    keep = ["Entity", "Code", "Year"] + value_cols
    out = df[keep].copy()

    out = out[
        out["Code"].notna()
        & out["Code"].map(lambda x: isinstance(x, str) and len(x.strip()) == 3)
    ].copy()

    out["Code"] = out["Code"].astype(str).str.strip().str.upper()

    out = (
        out.sort_values(["Code", "Year"])
        .groupby(["Code", "Year"], as_index=False)
        .first()
    )
    return out

def iso3_to_numeric(code):
    if pd.isna(code):
        return None
    code = str(code).strip().upper()
    if len(code) != 3:
        return None
    c = pycountry.countries.get(alpha_3=code)
    return int(c.numeric) if c and c.numeric else None


# ----------------------------
# MAIN: build charts for Streamlit
# ----------------------------
def build_exploration_charts():
    """
    Returns charts in this order:
      final, scatter_component, chart, chart_corr, chart_traj
    """

    # ----------------------------
    # 1) Load main dataset
    # ----------------------------
    df = pd.read_csv(r"HDI vs Fertility Data/children-per-woman-vs-human-development-index.csv")
    df["Code"] = df["Code"].astype(str).str.strip().str.upper()

    # Filter to ISO3 only
    d = df[df["Code"].astype(str).str.len() == 3].copy()
    d["Code"] = d["Code"].astype(str).str.strip().str.upper()

    # ----------------------------
    # 2) Load component CSVs (local)
    # ----------------------------
    lifeexp = load_local_grapher(r"Components/life-expectancy-unwpp.csv", "Life expectancy at birth")
    expschool = load_local_grapher(r"Components/expected-years-of-schooling.csv", "Expected years of schooling")
    meanschool = load_local_grapher(r"Components/years-of-schooling.csv", "Mean years of schooling")
    gni = load_local_grapher(r"Components/gross-national-income-per-capita-undp.csv", "GNI per capita")

    # ----------------------------
    # 3) Prep + merge
    # ----------------------------
    fert = prep_owid(df, [
        "Fertility rate",
        "Human Development Index",
        "World region according to OWID",
        "Population"
    ])
    life = prep_owid(lifeexp, ["Life expectancy at birth"])
    expy = prep_owid(expschool, ["Expected years of schooling"])
    meany = prep_owid(meanschool, ["Mean years of schooling"])
    gni2 = prep_owid(gni, ["GNI per capita"])

    merged = (
        fert.merge(life.drop(columns=["Entity"]), on=["Code", "Year"], how="left")
            .merge(expy.drop(columns=["Entity"]), on=["Code", "Year"], how="left")
            .merge(meany.drop(columns=["Entity"]), on=["Code", "Year"], how="left")
            .merge(gni2.drop(columns=["Entity"]), on=["Code", "Year"], how="left")
    )

    # ----------------------------
    # 4) d_map for choropleth lookup
    # ----------------------------
    d = d[(d["Year"] >= 1990) & (d["Year"] <= 2023)].copy()
    d["id"] = d["Code"].apply(iso3_to_numeric)

    d_map = d[d["id"].notna()].copy()
    d_map["id_year"] = (
        d_map["id"].astype(int).astype(str)
        + "_"
        + d_map["Year"].astype(int).astype(str)
    )

    # ----------------------------
    # 5) Build chg_small (1990 -> latest)
    # ----------------------------
    m = merged.copy()
    m = m[(m["Year"] >= 1990) & (m["Year"] <= 2023)].copy()

    cols_needed = [
        "Fertility rate",
        "Human Development Index",
        "Life expectancy at birth",
        "Expected years of schooling",
        "Mean years of schooling",
        "GNI per capita",
    ]
    m = m.dropna(subset=["Fertility rate", "Human Development Index"])

    baseline_year = 1990

    base90 = m[m["Year"] == baseline_year][
        ["Code", "Entity", "World region according to OWID", "Population"] + cols_needed
    ].rename(columns={c: f"{c}_1990" for c in cols_needed})

    idx_latest = m.groupby("Code")["Year"].idxmax()
    latest = m.loc[idx_latest, ["Code", "Year", "Population"] + cols_needed].rename(
        columns={c: f"{c}_latest" for c in cols_needed}
    ).rename(columns={"Year": "Year_latest", "Population": "Population_latest"})

    chg = base90.merge(latest, on="Code", how="inner")
    for c in cols_needed:
        chg[f"Δ {c}"] = chg[f"{c}_latest"] - chg[f"{c}_1990"]

    chg["Country"] = chg["Entity"]
    chg_small = chg[[
        "Code", "Country", "World region according to OWID", "Year_latest",
        "Population_latest",
        "Δ Fertility rate",
        "Δ Human Development Index",
        "Δ Life expectancy at birth",
        "Δ Expected years of schooling",
        "Δ Mean years of schooling",
        "Δ GNI per capita",
    ]].copy()

    # ============================================================
    # 6) VISUALIZATIONS (fixed indentation + missing traj)
    # ============================================================

    # ---------- final (map + linked lines) ----------
    world = data.world_110m.url

    year_map = alt.param(
        name="year_map",
        value=2020,
        bind=alt.binding_range(
            min=int(d_map["Year"].min()),
            max=int(d_map["Year"].max()),
            step=1,
            name="Year"
        ),
    )

    country_click = alt.selection_point(
        name="country_click",
        fields=["id"],
        on="click",
        empty=False
    )

    map_chart = (
        alt.Chart(alt.topo_feature(world, "countries"))
        .add_params(year_map, country_click)
        .transform_calculate(
            id_year="toString(datum.id) + '_' + toString(year_map)"
        )
        .transform_lookup(
            lookup="id_year",
            from_=alt.LookupData(
                d_map,
                key="id_year",
                fields=["Entity", "Year", "Human Development Index", "Code"]
            )
        )
        .mark_geoshape(stroke="black", strokeWidth=0.2)
        .encode(
            color=alt.Color(
                "Human Development Index:Q",
                title="HDI",
                scale=alt.Scale(domain=[0.3, 1.0])
            ),
            strokeWidth=alt.condition(country_click, alt.value(1.8), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("Entity:N", title="Country"),
                alt.Tooltip("Code:N", title="Code"),
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip("Human Development Index:Q", title="HDI", format=".3f"),
            ],
        )
        .project("equalEarth")
        .properties(width=900, height=480, title="HDI by Country")
    )

    ts = merged.copy()
    ts = ts[ts["Code"].astype(str).str.len() == 3].copy()
    ts = ts.dropna(subset=["Human Development Index", "Fertility rate"])

    hdi_domain = [0.3, 1.0]
    fert_min = float(ts["Fertility rate"].min())
    fert_max = float(ts["Fertility rate"].max())
    fert_domain = [max(0, fert_min - 0.3), fert_max + 0.3]

    id_to_code = (
        d_map.dropna(subset=["id", "Code"])
        .drop_duplicates(subset=["id"])[["id", "Code", "Entity"]]
    )

    hdi_line = (
        alt.Chart(ts)
        .transform_lookup(
            lookup="Code",
            from_=alt.LookupData(id_to_code, key="Code", fields=["id", "Entity"])
        )
        .transform_filter(country_click)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("Year:O", title=None),
            y=alt.Y("Human Development Index:Q", title="HDI", scale=alt.Scale(domain=hdi_domain)),
            tooltip=[
                alt.Tooltip("Entity:N", title="Country"),
                alt.Tooltip("Year:O"),
                alt.Tooltip("Human Development Index:Q", title="HDI", format=".3f"),
            ],
        )
        .properties(width=900, height=160, title="HDI over time (selected country)")
    )

    fert_line = (
        alt.Chart(ts)
        .transform_lookup(
            lookup="Code",
            from_=alt.LookupData(id_to_code, key="Code", fields=["id", "Entity"])
        )
        .transform_filter(country_click)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("Year:O", title=None),
            y=alt.Y("Fertility rate:Q", title="Fertility rate", scale=alt.Scale(domain=fert_domain)),
            tooltip=[
                alt.Tooltip("Entity:N", title="Country"),
                alt.Tooltip("Year:O"),
                alt.Tooltip("Fertility rate:Q", title="Fertility", format=".2f"),
            ],
        )
        .properties(width=900, height=160, title="Fertility over time (selected country)")
    )

    year_rule = (
        alt.Chart(pd.DataFrame({"Year": list(sorted(ts["Year"].unique()))}))
        .mark_rule(opacity=0.25)
        .encode(x="Year:O")
        .transform_filter(alt.datum.Year == year_map)
    )

    final = (
        alt.vconcat(map_chart, hdi_line + year_rule, fert_line + year_rule, spacing=10)
        .configure_view(stroke=None)
        .configure_axis(domain=False, ticks=False, grid=True, labelFontSize=12, titleFontSize=13)
        .configure_title(fontSize=16, anchor="start", offset=10)
    )

    # ---------- scatter_component ----------
    x_options_sc = [
        "Δ Human Development Index",
        "Δ Life expectancy at birth",
        "Δ Expected years of schooling",
        "Δ Mean years of schooling",
        "Δ GNI per capita",
    ]

    xvar_sc = alt.param(
        name="xvar_sc",
        value="Δ Human Development Index",
        bind=alt.binding_select(options=x_options_sc, name="X variable: ")
    )

    x_expr_sc = (
        "xvar_sc == 'Δ Human Development Index' ? datum['Δ Human Development Index'] : "
        "xvar_sc == 'Δ Life expectancy at birth' ? datum['Δ Life expectancy at birth'] : "
        "xvar_sc == 'Δ Expected years of schooling' ? datum['Δ Expected years of schooling'] : "
        "xvar_sc == 'Δ Mean years of schooling' ? datum['Δ Mean years of schooling'] : "
        "datum['Δ GNI per capita']"
    )

    region_sel_sc = alt.selection_point(
        name="region_sel_sc",
        fields=["World region according to OWID"],
        bind="legend",
        empty="all"
    )

    scatter_component = (
        alt.Chart(chg_small)
        .add_params(xvar_sc, region_sel_sc)
        .transform_calculate(x_value=x_expr_sc)
        .transform_filter("isValid(datum['Δ Fertility rate']) && isValid(datum.x_value)")
        .mark_circle(opacity=0.8)
        .encode(
            x=alt.X("x_value:Q", title=None),
            y=alt.Y("Δ Fertility rate:Q", title="Change in Fertility Rate (2023 − 1990)"),
            color=alt.Color("World region according to OWID:N", title="Region"),
            opacity=alt.condition(region_sel_sc, alt.value(0.9), alt.value(0.08)),
            tooltip=[
                alt.Tooltip("Country:N"),
                alt.Tooltip("World region according to OWID:N", title="Region"),
                alt.Tooltip("Year_latest:O", title="Latest year"),
                alt.Tooltip("Δ Fertility rate:Q", format=".2f"),
                alt.Tooltip("Δ Human Development Index:Q", format=".3f"),
                alt.Tooltip("Δ Life expectancy at birth:Q", format=".2f"),
                alt.Tooltip("Δ Expected years of schooling:Q", format=".2f"),
                alt.Tooltip("Δ Mean years of schooling:Q", format=".2f"),
                alt.Tooltip("Δ GNI per capita:Q", format=".0f"),
            ],
        )
        .properties(width=800, height=450, title="Fertility Change vs Development Component Change")
        .configure_view(stroke=None)
    )

    # ---------- chart (ranking bars) ----------
    TOP_N = 10

    r = chg_small.dropna(subset=["Δ Fertility rate", "Δ Human Development Index"]).copy()
    r["CountryLabel"] = r["Country"] + " (" + r["World region according to OWID"] + ")"
    regions_rank = sorted([x for x in r["World region according to OWID"].dropna().unique()])
    region_scale = alt.Scale(domain=regions_rank, scheme="tableau10")

    rank_metric = alt.param(
        name="rank_metric",
        value="Fertility",
        bind=alt.binding_select(options=["Fertility", "HDI"], name="Rank by: ")
    )
    mode = alt.param(
        name="mode",
        value="Biggest declines",
        bind=alt.binding_select(
            options=["Biggest declines", "Biggest increases", "Biggest absolute change"],
            name="Show: "
        )
    )
    region_sel_rank = alt.selection_point(
        name="region_sel_rank",
        fields=["World region according to OWID"],
        bind="legend",
        empty="all"
    )

    value_for_rank_expr = (
        "rank_metric == 'Fertility' ? datum['Δ Fertility rate'] : datum['Δ Human Development Index']"
    )
    sort_key_expr = (
        "mode == 'Biggest declines' ? (" + value_for_rank_expr + ") : "
        "mode == 'Biggest increases' ? (-(" + value_for_rank_expr + ")) : "
        "(-abs(" + value_for_rank_expr + "))"
    )
    other_value_expr = (
        "rank_metric == 'Fertility' ? datum['Δ Human Development Index'] : datum['Δ Fertility rate']"
    )
    bar_title_expr = (
        "rank_metric == 'Fertility' ? 'Δ Fertility (latest − 1990)' : 'Δ HDI (latest − 1990)'"
    )
    other_title_expr = (
        "rank_metric == 'Fertility' ? 'Δ HDI (latest − 1990)' : 'Δ Fertility (latest − 1990)'"
    )

    base = (
        alt.Chart(r)
        .add_params(rank_metric, mode, region_sel_rank)
        .transform_filter(region_sel_rank)
        .transform_calculate(
            sort_key=sort_key_expr,
            bar_value=value_for_rank_expr,
            other_value=other_value_expr,
            bar_title=bar_title_expr,
            other_title=other_title_expr
        )
        .transform_window(
            rank="row_number()",
            sort=[alt.SortField("sort_key", order="ascending")]
        )
        .transform_filter(f"datum.rank <= {TOP_N}")
    )

    y_left = alt.Y("CountryLabel:N", sort=alt.SortField(field="bar_value", order="ascending"), title=None)

    bars_left = base.mark_bar().encode(
        y=y_left,
        x=alt.X("bar_value:Q", title=None, axis=alt.Axis(format=".2f")),
        color=alt.Color("World region according to OWID:N", title="Region", scale=region_scale),
    ).properties(width=620, height=28 * TOP_N)

    zero_left = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(strokeWidth=1).encode(x="x:Q")

    bars_right = base.mark_bar(fill="white", strokeWidth=2).encode(
        y=alt.Y("CountryLabel:N", sort=alt.SortField(field="bar_value", order="ascending"), axis=None, title=None),
        x=alt.X("other_value:Q", title=None, axis=alt.Axis(format=".2f")),
        stroke=alt.Stroke("World region according to OWID:N", title="Region", scale=region_scale),
    ).properties(width=240, height=28 * TOP_N)

    zero_right = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(strokeWidth=1).encode(x="x:Q")

    bar_title = base.transform_window(_="rank()").transform_filter("datum.rank == 1").mark_text(
        align="left", fontSize=13, fontWeight=600
    ).encode(text="bar_title:N").properties(width=620, height=18)

    other_title = base.transform_window(_="rank()").transform_filter("datum.rank == 1").mark_text(
        align="left", fontSize=13, fontWeight=600
    ).encode(text="other_title:N").properties(width=240, height=18)

    title = alt.Chart(pd.DataFrame({"t": ["Top 10 country changes (1990 → 2023)"]})).mark_text(
        align="left", fontSize=16, fontWeight=600
    ).encode(text="t:N").properties(width=880, height=24)

    chart = (
        alt.vconcat(
            title,
            alt.hconcat(
                alt.vconcat(bar_title, bars_left + zero_left, spacing=4),
                alt.vconcat(other_title, bars_right + zero_right, spacing=4),
                spacing=18
            ),
            spacing=8
        )
        .configure_view(stroke=None)
        .configure_axis(domain=False, ticks=False, grid=True, labelFontSize=12)
        .configure_legend(titleFontSize=12, labelFontSize=11)
    )

    # ---------- chart_corr ----------
    YEAR = 2020
    vars_full = [
        "Fertility rate",
        "Human Development Index",
        "Life expectancy at birth",
        "Expected years of schooling",
        "Mean years of schooling",
        "GNI per capita",
    ]
    label_map = {
        "Fertility rate": "Fertility",
        "Human Development Index": "HDI",
        "Life expectancy at birth": "Life exp",
        "Expected years of schooling": "Exp school",
        "Mean years of schooling": "Mean school",
        "GNI per capita": "GNI PC",
    }
    order_full = vars_full[:]

    d0 = merged.copy()
    d0 = d0[d0["Code"].astype(str).str.len() == 3]
    d0 = d0[d0["Year"] == YEAR].copy()

    regions_corr = sorted([r0 for r0 in d0["World region according to OWID"].dropna().unique()])
    region_levels = ["All"] + regions_corr

    def corr_long_for_subset(sub_df, region_name):
        num = sub_df[vars_full].dropna()
        if len(num) < 5:
            return pd.DataFrame(columns=["Region", "Var1", "Var2", "r", "Var1_short", "Var2_short", "i", "j"])
        corr = num.corr(method="pearson")
        out = (
            corr.reset_index()
                .melt(id_vars="index", var_name="Var2", value_name="r")
                .rename(columns={"index": "Var1"})
        )
        out["Region"] = region_name
        out["Var1_short"] = out["Var1"].map(label_map)
        out["Var2_short"] = out["Var2"].map(label_map)
        idx = {v: k for k, v in enumerate(order_full)}
        out["i"] = out["Var1"].map(idx)
        out["j"] = out["Var2"].map(idx)
        return out

    corr_all = corr_long_for_subset(d0, "All")
    corr_by_region = [corr_long_for_subset(d0[d0["World region according to OWID"] == rr], rr) for rr in regions_corr]
    corr_long = pd.concat([corr_all] + corr_by_region, ignore_index=True)

    region_param = alt.param(
        name="region_corr",
        value="All",
        bind=alt.binding_select(options=region_levels, name="Region: ")
    )

    base_corr = (
        alt.Chart(corr_long)
        .add_params(region_param)
        .transform_filter(alt.datum.Region == region_param)
        .transform_filter(alt.datum.i >= alt.datum.j)
    )

    heat = base_corr.mark_rect(stroke="white", strokeWidth=1).encode(
        x=alt.X("Var2_short:N", sort=[label_map[v] for v in order_full], title=None,
                axis=alt.Axis(labelAngle=0, labelPadding=8)),
        y=alt.Y("Var1_short:N", sort=[label_map[v] for v in order_full], title=None),
        color=alt.Color(
            "r:Q",
            title="Pearson r",
            scale=alt.Scale(domain=[-1, 1], scheme="redblue"),
            legend=alt.Legend(format=".2f")
        ),
        tooltip=[
            alt.Tooltip("Region:N"),
            alt.Tooltip("Var1:N", title="Variable 1"),
            alt.Tooltip("Var2:N", title="Variable 2"),
            alt.Tooltip("r:Q", title="Pearson r", format=".2f"),
        ]
    )

    labels = base_corr.mark_text(fontSize=12, baseline="middle").encode(
        x=alt.X("Var2_short:N", sort=[label_map[v] for v in order_full]),
        y=alt.Y("Var1_short:N", sort=[label_map[v] for v in order_full]),
        text=alt.Text("r:Q", format=".2f"),
        color=alt.condition("abs(datum.r) > 0.55", alt.value("white"), alt.value("black"))
    )

    chart_corr = (
        (heat + labels)
        .properties(width=520, height=520, title=f"Correlation of Fertility, HDI, and Components ({YEAR})")
        .configure_view(stroke=None)
        .configure_axis(domain=False, ticks=False, grid=False, labelFontSize=12)
        .configure_title(fontSize=16, anchor="start", offset=8)
        .configure_legend(titleFontSize=12, labelFontSize=11)
    )

    # ---------- chart_traj (FIX: define traj) ----------
    traj = merged.copy()
    traj = traj[(traj["Year"] >= 1990) & (traj["Year"] <= 2023)].copy()
    traj = traj[traj["Code"].astype(str).str.len() == 3].copy()
    traj = traj.dropna(subset=["Fertility rate"]).copy()

    x_options = [
        "Human Development Index",
        "Life expectancy at birth",
        "Expected years of schooling",
        "Mean years of schooling",
        "GNI per capita",
    ]

    xvar_traj = alt.param(
        name="xvar_traj",
        value="Human Development Index",
        bind=alt.binding_select(options=x_options, name="X axis: ")
    )

    year_traj = alt.param(
        name="year_traj",
        value=2020,
        bind=alt.binding_range(
            min=int(traj["Year"].min()),
            max=int(traj["Year"].max()),
            step=1,
            name="Year"
        )
    )

    country_sel = alt.selection_point(
        name="country_sel",
        fields=["Code"],
        on="click",
        toggle=True,
        empty=False
    )

    region_sel_traj = alt.selection_point(
        name="region_sel_traj",
        fields=["World region according to OWID"],
        bind="legend",
        empty="all"
    )

    regions_traj = sorted([rr for rr in traj["World region according to OWID"].dropna().unique()])
    region_scale_traj = alt.Scale(domain=regions_traj, scheme="tableau10")

    y_min = float(traj["Fertility rate"].min())
    y_max = float(traj["Fertility rate"].max())
    y_domain = [max(0, y_min - 0.3), y_max + 0.3]

    folded = (
        alt.Chart(traj)
        .transform_fold(x_options, as_=["metric", "x_value"])
        .transform_filter(alt.datum.metric == xvar_traj)
        .transform_filter("isValid(datum.x_value) && isValid(datum['Fertility rate'])")
    )

    scatter = (
        folded
        .transform_filter(alt.datum.Year == year_traj)
        .mark_circle(size=70)
        .encode(
            x=alt.X("x_value:Q", title=None),
            y=alt.Y(
                "Fertility rate:Q",
                title="Fertility rate (children per woman)",
                scale=alt.Scale(domain=y_domain),
                axis=alt.Axis(format=".1f")
            ),
            color=alt.Color(
                "World region according to OWID:N",
                title="Region",
                scale=region_scale_traj,
                legend=alt.Legend(orient="right")
            ),
            opacity=alt.condition(region_sel_traj, alt.value(0.55), alt.value(0.08)),
            tooltip=[
                alt.Tooltip("Entity:N", title="Country"),
                alt.Tooltip("World region according to OWID:N", title="Region"),
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip("metric:N", title="X metric"),
                alt.Tooltip("x_value:Q", title="X value"),
                alt.Tooltip("Fertility rate:Q", title="Fertility", format=".2f"),
            ],
        )
    )

    domain_layer = (
        folded
        .transform_filter(region_sel_traj)
        .mark_point(opacity=0)
        .encode(
            x=alt.X("x_value:Q", title=None),
            y=alt.Y("Fertility rate:Q", scale=alt.Scale(domain=y_domain), title=None),
        )
    )

    lines = (
        folded
        .transform_filter(country_sel)
        .transform_filter(region_sel_traj)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("x_value:Q", title=None),
            y=alt.Y("Fertility rate:Q", scale=alt.Scale(domain=y_domain), title=None),
            detail="Code:N",
            stroke=alt.Stroke("World region according to OWID:N", scale=region_scale_traj, legend=None),
        )
    )

    selected_points = (
        folded
        .transform_filter(country_sel)
        .transform_filter(region_sel_traj)
        .transform_filter(alt.datum.Year == year_traj)
        .mark_circle(size=115, stroke="black", strokeWidth=1.2)
        .encode(
            x=alt.X("x_value:Q", title=None),
            y=alt.Y("Fertility rate:Q", scale=alt.Scale(domain=y_domain), title=None),
            fill=alt.Fill("World region according to OWID:N", scale=region_scale_traj, legend=None),
        )
    )

    chart_traj = (
        alt.layer(scatter, domain_layer, lines, selected_points)
        .add_params(year_traj, xvar_traj, country_sel, region_sel_traj)
        .properties(width=900, height=520, title="Components of HDI vs Fertility over time")
        .configure_view(stroke=None)
        .configure_axis(domain=False, ticks=False, grid=True, labelFontSize=12, titleFontSize=13)
        .configure_title(fontSize=16, anchor="start", offset=10)
        .configure_legend(orient="right", titleFontSize=12, labelFontSize=11, symbolSize=120)
    )

    return final, scatter_component, chart, chart_corr, chart_traj