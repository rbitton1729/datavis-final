import pandas as pd
import altair as alt
import streamlit as st
from exploration_charts import build_exploration_charts

alt.data_transformers.enable("vegafusion")

st.set_page_config(
    page_title="Global Fertility & Population Dynamics",
    layout="wide",
)


@st.cache_data
def load_fert():
    df = pd.read_csv("data/fertvhdi.csv")
    df["year"] = pd.to_datetime(df["year"], format="%Y")
    return df


@st.cache_data
def load_pyramid():
    df = pd.read_csv("data/population_pyramid_1950-2022.csv")
    df = df.rename(columns={"M": "Male", "F": "Female"})
    return df.melt(
        id_vars=["Country", "Age", "Year"],
        value_vars=["Male", "Female"],
        var_name="gender",
        value_name="population",
    )


@st.cache_resource(show_spinner=False)
def load_exploration_charts():
    return build_exploration_charts()


df = load_fert()
ppdf = load_pyramid()


REGION_DOMAIN = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]
REGION_SCALE = alt.Scale(domain=REGION_DOMAIN, scheme="tableau10")


def make_figure2(df):
    regiondf = df.copy()
    specific_region = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]
    regiondf = regiondf[regiondf["entity"].isin(specific_region)]

    label = alt.selection_point(
        encodings=["x"],
        on="mouseover",
        nearest=True,
        empty=False,
    )

    base = alt.Chart(regiondf).mark_line().encode(
        x=alt.X("year:T", title="Year"),
        y=alt.Y("fertility_rate__sex_all__age_all__variant_estimates", title="Fertility Rate"),
        color=alt.Color("entity:N", title="Regions", scale=REGION_SCALE),
    )

    chart = alt.layer(
        base,
        base.mark_circle().encode(
            opacity=alt.condition(label, alt.value(1), alt.value(0))
        ).add_params(label),
        alt.Chart().mark_rule(color="#aaa").encode(x="year:T").transform_filter(label),
        base.mark_text(align="left", dx=5, dy=-5, stroke="white", strokeWidth=2).encode(
            text="fertility_rate__sex_all__age_all__variant_estimates:Q"
        ).transform_filter(label),
        base.mark_text(align="left", dx=5, dy=-5).encode(
            text="fertility_rate__sex_all__age_all__variant_estimates:Q"
        ).transform_filter(label),
        data=regiondf,
    ).properties(title="Average Regional Fertility Rate Over Time", width=800, height=400)

    rule_data = pd.DataFrame({"y": [2.1]})
    horizontal_line = alt.Chart(rule_data).mark_rule(color="black", strokeWidth=2).encode(y="y")

    return chart + horizontal_line


def make_figure1(df):
    timedf = df.dropna(subset=["owid_region"]).copy()

    input_dropdown = alt.binding_select(
        options=[None, "Africa", "Asia", "Europe", "North America", "Oceania", "South America"],
        labels=["All", "Africa", "Asia", "Europe", "North America", "Oceania", "South America"],
        name="Region",
    )
    selection = alt.selection_point(fields=["owid_region"], bind=input_dropdown, empty=True)

    color = (
        alt.when(selection)
        .then(alt.Color("owid_region:N", title="Regions", scale=REGION_SCALE))
        .otherwise(alt.value("lightgray"))
    )
    opacity = alt.condition(selection, alt.value(1.0), alt.value(0.1))

    base = alt.Chart(timedf).mark_point().encode(
        x=alt.X("year:T", title="Year"),
        y=alt.Y("fertility_rate__sex_all__age_all__variant_estimates", title="Fertility Rate"),
        color=color,
        opacity=opacity,
    ).add_params(selection).properties(title="Fertility Rate Over Time", width=900, height=400)

    tooltips = base.mark_circle().encode(
        opacity=alt.value(0),
        tooltip=[
            alt.Tooltip("entity", title="Country"),
            alt.Tooltip("fertility_rate__sex_all__age_all__variant_estimates", title="Fertility Rate"),
            alt.Tooltip("year:T", title="Year"),
        ],
    ).transform_filter(selection)

    rule_data = pd.DataFrame({"y": [2.1]})
    horizontal_line = alt.Chart(rule_data).mark_rule(color="black", strokeWidth=3).encode(y="y")

    return base + tooltips + horizontal_line


AGE_ORDER = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74",
    "75-79", "80-84", "85-89", "90-94", "95-99", "100+",
]

PYRAMID_REGIONS = {
    "World": "WORLD",
    "Africa": "AFRICA",
    "Asia": "ASIA",
    "Europe": "EUROPE",
    "North America": "NORTHERN AMERICA",
    "Oceania": "OCEANIA",
    "South America": "South America",
}


PP_YEARS = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2022]


def make_pyramid(ppdf, region_name, year, title=None):
    data = ppdf[(ppdf["Country"] == region_name) & (ppdf["Year"] == year)].copy()
    female = data[data["gender"] == "Female"].copy()
    male = data[data["gender"] == "Male"].copy()

    color_scale = alt.Scale(domain=["Male", "Female"], range=["#89CFF0", "#F4C2C2"])

    left = (
        alt.Chart(female)
        .mark_bar()
        .encode(
            alt.Y("Age:O", sort=AGE_ORDER).axis(None),
            alt.X("population:Q", title="Population", sort="descending"),
            alt.Color("gender:N", scale=color_scale, legend=None),
        )
        .properties(width=260, title="Female")
    )

    middle = (
        alt.Chart(female)
        .mark_text()
        .encode(
            alt.Y("Age:O", sort=AGE_ORDER).axis(None),
            alt.Text("Age:O"),
        )
        .properties(width=40)
    )

    right = (
        alt.Chart(male)
        .mark_bar()
        .encode(
            alt.Y("Age:O", sort=AGE_ORDER).axis(None),
            alt.X("population:Q", title="Population"),
            alt.Color("gender:N", scale=color_scale, legend=None),
        )
        .properties(width=260, title="Male")
    )

    chart_title = title or region_name.title()
    return (
        alt.hconcat(left, middle, right, spacing=5)
        .resolve_scale(y="shared")
        .properties(
            title=alt.TitleParams(text=chart_title, anchor="middle", fontSize=20, fontWeight="bold")
        )
    )


# ── Page layout ───────────────────────────────────────────────────────────────

st.title("Global Fertility Rates and Population Dynamics")

st.markdown(
    """
Declining global fertility rates have been plaguing the world recently, with global fertility
rates in 2023 reaching **2.3 children per woman** - less than half of the 4.9 seen in the 1950s.

But why should declining fertility rates concern us? We are now reaching a level where women on
average are having so few children that over half of all countries are now below the **2.1
replacement rate** - the total fertility rate needed to maintain a stable population without
relying on migration.
"""
)

# ── Figure 2: Regional average fertility ────────────────────────────────────
st.subheader("Average Regional Fertility Rate Over Time")
st.altair_chart(make_figure2(df), use_container_width=True)
st.markdown(
    """
In the figure above, it can be observed how fertility rate worldwide, across different regions,
has been declining. Excluding Africa, most regions have experienced a fast decline.
The first concerning point was when **Europe fell below the replacement rate in 1975**. In the
past 20 years, South America, North America, and Asia have also fallen below the 2.1 threshold.
"""
)

st.divider()

# ── Figure 1: Country-level fertility scatter ────────────────────────────────
st.subheader("Fertility Rate Over Time by Country")
st.markdown(
    """
Although regional averages are informative, there is still a lot of variation *within* each
region. Use the **Region** dropdown in the chart to focus on a single region. For example,
within Asia in 2023, fertility ranged from **4.84** (Afghanistan) down to **0.66** (Macao).
"""
)
st.altair_chart(make_figure1(df), use_container_width=True)
st.markdown(
    """
This scatter plot shows individual countries. Color encodes region; the black horizontal line
marks the 2.1 replacement rate. Hover over any point to see country, fertility rate, and year.
"""
)

st.divider()

st.subheader("World Population Pyramid")
st.markdown(
    """
Low fertility rates are a problem below the 2.1 threshold because they lead to fewer workers,
fewer consumers, fewer taxpayers, and an increasingly aging population with a smaller younger
base to support it.

The population pyramid below shows the global age distribution. Use the year slider to travel from
1950 to 2022. In **1950** the pyramid was healthy - a broad base of young people tapering with
age. By **2020** the base has narrowed noticeably, signaling an aging world population.
"""
)
year_world = st.select_slider("Year", options=PP_YEARS, value=2020, key="world_pp")
st.altair_chart(make_pyramid(ppdf, "WORLD", year_world, "World Population Pyramid"), use_container_width=True)

st.divider()

st.subheader("Population Pyramid by Region")
st.markdown(
    """
Comparing regions reveals stark differences. In the 1950s most regions had a healthy youthful
base. Today only **Africa** maintains that strong triangle. **Europe** now shows an inverted
base - more 50–60 year-olds than 0–10 year-olds. **North America** follows closely. **Asia**
is in a near-stationary stage. **South America** is slightly contracting.

Select a region and year below to explore how each region's pyramid has shifted.
"""
)

selected_display = st.selectbox("Select region", list(PYRAMID_REGIONS.keys()))
year_region = st.select_slider("Year", options=PP_YEARS, value=2020, key="region_pp")
region_csv_name = PYRAMID_REGIONS[selected_display]
st.altair_chart(
    make_pyramid(ppdf, region_csv_name, year_region, f"{selected_display} Population Pyramid"),
    use_container_width=True,
)

st.divider()

st.subheader("Why Are Fertility Rates Declining? The HDI Connection")
st.markdown(
    """
We wanted to explore the relationship between HDI and fertility rate and how that relationship
can explain the reasoning behind the global decline in fertility.

So what is HDI? HDI is a composite measurement of life expectancy, mean years of schooling,
expected years of schooling, and GNI per capita that is reported by the United Nations yearly.

For this project we want to look at a developing relationship, so it's important to look not only at
differences in HDI and Fertility Rate between countries, but also how those differences evolved
over time.

*Interact with the visualization below to explore - click on a country to gather more detail and
move the year slider to look at the differences over time.*
"""
)

final, scatter_component, chart, chart_corr, chart_traj = load_exploration_charts()

st.markdown("### HDI Global Map")
st.altair_chart(final, use_container_width=True)

st.divider()

st.markdown(
    """
It looks like HDI has increased close to globally over the past 33 years, and with some more
analysis it looks like fertility rate has also experienced a nearly global pattern, but in the negative
direction. But is this change similar in magnitude across countries? Across regions? Explore the
visualizations below to see if that's the case. Look for outliers and patterns and see if you can
find the lone country that lost HDI rating and the only two countries that gain fertility rate.

*For the scatterplot try changing the X-Axis variable to look at how components of HDI affect
fertility rates. Also try clicking the legend to organize the graph by region. Hover over a point to
gather more information.*

*For the bar chart, toggle between HDI and Fertility Rate and change around the ranking criteria
to find new patterns. Sort by region by using the legend again.*
"""
)

st.markdown("### Change in Fertility vs Change in HDI Components")
st.altair_chart(scatter_component, use_container_width=True)

st.markdown("### Top Country Changes")
st.altair_chart(chart, use_container_width=True)

st.divider()

st.markdown(
    """
Hopefully you were able to find that only Syria decreased in HDI from 1990 and only
Kazakhstan and Slovenia increased in Fertility Rate. Overall, the pattern is pretty clear: as HDI
increases, fertility rates decrease. Looking at what makes up HDI, this seems almost
counterintuitive. A higher GNI per capita roughly translates to a higher standard of living, so one
would think that would lead to a higher fertility rate as perhaps parents are more likely to want to
bring in a child if they believe they can afford it, but that doesn't seem to be the case. One might
think a higher life expectancy means more time to have children and set up a family but again,
the opposite is true. Expected years of schooling and mean years of schooling are also very
negatively correlated with fertility rates, perhaps because more schooling translates into a greater
desire for a career, which can leave little room for starting a family. If we had more time, perhaps
looking into female education rates could be informative, as that could be a better explanatory
component than simply years of education for all genders.

Additionally, looking at how the regions changed over time provides valuable insight. Looking at
Europe, for example, we see that there's basically no negative correlation between HDI and
fertility rates, perhaps because Europe in 1990 was already fairly developed so the increase in
HDI didn't impact fertility rates as heavily. This hypothesis is further supported by looking at
Oceania and Africa, which have fairly strong negative correlations. These regions are relatively
underdeveloped, so not only are their HDI gains much larger in magnitude, but the changes bring
them much closer to modern society and this seems to lead to a lower fertility rate. So perhaps
fertility rates are much higher in impoverished societies with low education rates and increasing
HDI lowers fertility rates up to a point where it becomes a diminishing return.

Changing the X axis also provides some interesting analysis. For example Africa's GNI per
capita looks curious, as it's almost a vertical line at 0 but yet spread out as fertility rate change
varies across the countries. So although HDI and Fertility Rate seem to be very correlated, the
components' correlation to Fertility Rate varies by region. Look at the heat map below for an
even deeper look.

*Use the drop down to change which region you want to explore.*
"""
)

st.markdown("### Correlation Heatmap")
st.altair_chart(chart_corr, use_container_width=True)

st.divider()

st.markdown(
    """
The key thing to look at for this graph is the first column. For all regions we can see that each
component has a moderate to very strong negative correlation with Fertility Rate. Looking at
how those correlations change when we switch regions is interesting. Europe, as stated above,
shows almost no correlation between the HDI components and Fertility Rate, whereas Oceania
shows an abnormally strong negative correlation between GNI PC and Fertility Rate. It's
fascinating to see why some regions seem to have certain components impact Fertility Rate more
than others and with more time and resources this study could be fleshed out to become more
specific and include more variables.

Finally, the following visualization lets you follow countries and regions over time across every
component of HDI. Explore those outliers we found as well as any countries that you see with an
unusual path across the years.

*Try clicking a country to see its path over time. Use the year slider and X axis drop down to
customize what you see. Use the legend once again to sort by region.*
"""
)

st.markdown("### Trajectories Over Time")
st.altair_chart(chart_traj, use_container_width=True)

st.divider()

st.subheader("Conclusion")
st.markdown(
    """
The data tells a consistent story: global fertility rates have fallen dramatically over the past
70 years and show no sign of reversing. What began as a European phenomenon in the 1970s
has since spread to South America, North America, and Asia, leaving Africa as the last major
region still above the 2.1 replacement rate. The consequences are already visible in population
pyramids that have shifted from broad youthful bases to narrowing, aging distributions -
particularly in Europe and East Asia.

The HDI analysis adds an important explanatory layer. As countries develop, gaining in life
expectancy, education, and income, fertility rates fall, and they fall hard. The correlation is
nearly universal across regions, though its magnitude varies: less-developed regions show the
steepest declines as they modernize, while already-developed regions have largely plateaued
at low fertility with little room left to fall. The implication is that we are not simply witnessing
a temporary demographic transition but a structural shift in how modern societies form families.

Without significant policy intervention or migration, the demographic math leads to shrinking
workforces, strained pension systems, and reduced economic dynamism in affected countries.
The challenge for the coming decades will be managing the consequences of a world that is
simultaneously aging in the developed world and still growing in parts of the developing world:
two realities that will require very different policy responses.
"""
)

st.divider()

with st.expander("Methodology"):
    st.markdown(
        """
**Figure 1 - Fertility Rate Over Time (country scatter)**
Uses `fertvhdi.csv`. X axis = time, Y axis = fertility rate, color = region.
A region dropdown lets viewers focus on one region at a time. Tooltip shows country, rate, and year.
The black line marks the 2.1 replacement rate.

**Figure 2 - Average Regional Fertility Rate Over Time**
Also uses `fertvhdi.csv`. X = year, Y = fertility rate, color = region.
A mouseover crosshair shows exact rates at each year. Replacement rate line at y = 2.1.

**World Population Pyramid**
Uses `population_pyramid_1950-2022.csv`. Left = female distribution, right = male, middle = age labels.
Color encodes gender (light blue = male, light pink = female). Year slider from 1950 to 2022.

**Regional Population Pyramids**
Same structure as the World pyramid. A dropdown selects the region. Allows comparison of how
Africa's youthful base contrasts with Europe's aging one across different decades.

**Figure 5 - HDI Choropleth + Linked Country Time Series**
Data: `children-per-woman-vs-human-development-index.csv` for HDI map lookup + merged OWID
components for the line views. Map marks: country geoshapes (Equal Earth projection). Encodings
(map): color (sequential) = HDI; tooltip = country, ISO3 code, year, HDI. Interactions: year slider
filters map to one year (lookup key `id_year`); click country selects/highlights boundary and drives
linked views. Linked views (lines): x = Year, y = HDI (top) and Fertility rate (bottom); vertical rule
at selected year for alignment; tooltips show values by year for selected country.

**Figure 6 - Fertility Change vs Development Component Change**
Data: country-level 1990 → latest deltas. Marks: points (country-level). Encodings: x = chosen
Δ development metric (dropdown: ΔHDI / Δlife expectancy / Δexpected schooling / Δmean schooling
/ ΔGNI per capita); y = Δ fertility rate (latest − 1990); color = region; tooltip = country, region,
latest year, all Δ fields. Interactions: dropdown switches x-variable via calculated field; legend click
filters/spotlights regions (drives opacity).

**Figure 7 - Top-Change Ranking Bars with Secondary Metric**
Data: country-level change table. Marks: bars in two aligned panels (top 10 ranked list). Left panel:
y = country (sorted by chosen rank metric), x = Δ of selected metric, fill = region. Right panel: same
country order (axis hidden), x = Δ of the other metric, stroke = region with white fill. Interactions:
"Rank by" dropdown toggles primary metric (Fertility / HDI); "Show" dropdown toggles ranking rule
(biggest declines / biggest increases / biggest absolute change); legend click filters regions so top N
recomputes within selected regions. Zero rules at x = 0 on both panels.

**Figure 8 - Correlation Heatmap (Region Dropdown)**
Data: merged dataset filtered to 2020; Pearson correlations among fertility, HDI, life expectancy,
expected schooling, mean schooling, and GNI per capita for All regions and each region separately.
Marks: rect heatmap + text annotations. Encodings: x = variable, y = variable, color (diverging) =
Pearson r in [−1, 1]; text = r label; tooltip = region + variable pair + r. Lower triangle only to avoid
redundancy. Interaction: region dropdown switches which correlation matrix is displayed.

**Figure 9 - Trajectory Plot Over Time**
Data: merged country-year dataset (1990–2023). Marks: points for the selected year snapshot, lines
for selected-country paths, emphasized points for selected countries at the current year. Encodings:
x = selected development metric (dropdown: HDI / life expectancy / expected schooling / mean
schooling / GNI per capita), y = fertility rate, color = region, opacity conditioned on region selection.
Interactions: year slider filters scatter to a single year with fixed y-domain; x-axis dropdown switches
metric (fold + filter); click country toggles trajectory lines (multi-select); legend click filters regions;
tooltips show country, region, year, metric, x value, fertility.
"""
    )

with st.expander("Data Sources"):
    st.markdown(
        """
**fertvhdi.csv** - Fertility rate vs Human Development Index by country and year (1950–2023).
Source: Our World in Data.

**population_pyramid_1950-2022.csv** - Population by age group and gender for countries and
world regions (1950–2022).
Source: [Kaggle - Population Pyramid by Country from 1950–2022](https://www.kaggle.com/datasets/prasertk/population-pyramid-by-country-from-19502022)
(original data: populationpyramid.net)

**children-per-woman-vs-human-development-index.csv** - Fertility rate and HDI by country
and year. Source: Our World in Data.

**Components CSVs** - Life expectancy, expected years of schooling, mean years of schooling,
GNI per capita. Source: Our World in Data / UNDP.
"""
    )
