import streamlit as st
import altair as alt

from exploration_charts import build_exploration_charts

st.set_page_config(page_title="Exploration", layout="wide")
alt.data_transformers.disable_max_rows()

# Optional: keeps the page from re-building all charts on every tiny interaction
@st.cache_resource(show_spinner=False)
def get_charts():
    return build_exploration_charts()

st.title("Exploration")

# Build charts once
final, scatter_component, chart, chart_corr, chart_traj = get_charts()

# -----------------------------
# Intro text (from your PDF)
# -----------------------------
st.markdown(
"""
We wanted to explore the relationship between HDI and fertility rate and how that relationship  
can explain the reasoning behind the global decline in fertility.

So what is HDI? HDI is a composite measurement of life expectancy, mean years of schooling,  
expected years of schooling, and GNI per capita that is reported by the United Nations yearly.

For this project we want to look at a developing relationship, so it’s important to look not only at  
differences in HDI and Fertility Rate between countries, but also how those differences evolved  
over time.

*Interact with the visualization below to explore – click on a country to gather more detail and  
move the year slider to look at the differences over time.*
"""
)

st.markdown("### HDI Global Map")
st.altair_chart(final, use_container_width=True)

st.divider()

# -----------------------------
# Text before scatter + ranking
# -----------------------------
st.markdown(
"""
It looks like HDI has increased close to globally over the past 33 years, and with some more  
analysis it looks like fertility rate has also experienced a nearly global pattern, but in the negative  
direction. But is this change similar in magnitude across countries? Across regions? Explore the  
visualizations below to see if that’s the case. Look for outliers and patterns and see if you can  
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

# -----------------------------
# Text before ranking
# -----------------------------
st.markdown(
"""
Hopefully you were able to find that only Syria decreased in HDI from 1990 and only  
Kazakhstan and Slovenia increased in Fertility Rate. Overall, the pattern is pretty clear: as HDI  
increases, fertility rates decrease. Looking at what makes up HDI, this seems almost  
counterintuitive. A higher GNI per capita roughly translates to a higher standard of living, so one  
would think that would lead to a higher fertility rate as perhaps parents are more likely to want to  
bring in a child if they believe they can afford it, but that doesn’t seem to be the case. One might  
think a higher life expectancy means more time to have children and set up a family but again,  
the opposite is true. Expected years of schooling and mean years of schooling are also very  
negatively correlated with fertility rates, perhaps because more schooling translates into a greater  
desire for a career, which can leave little room for starting a family. If we had more time, perhaps  
looking into female education rates could be informative, as that could be a better explanatory  
component than simply years of education for all genders.

Additionally, looking at how the regions changed over time provides valuable insight. Looking at  
Europe, for example, we see that there’s basically no negative correlation between HDI and  
fertility rates, perhaps because Europe in 1990 was already fairly developed so the increase in  
HDI didn’t impact fertility rates as heavily. This hypothesis is further supported by looking at  
Oceania and Africa, which have fairly strong negative correlations. These regions are relatively  
underdeveloped, so not only are their HDI gains much larger in magnitude, but the changes bring  
them much closer to modern society and this seems to lead to a lower fertility rate. So perhaps  
fertility rates are much higher in impoverished societies with low education rates and increasing  
HDI lowers fertility rates up to a point where it becomes a diminishing return.

Changing the X axis also provides some interesting analysis. For example Africa’s GNI per  
capita looks curious, as it’s almost a vertical line at 0 but yet spread out as fertility rate change  
varies across the countries. So although HDI and Fertility Rate seem to be very correlated, the  
components’ correlation to Fertility Rate varies by region. Look at the heat map below for an  
even deeper look.

*Use the drop down to change which region you want to explore.*
"""
)

st.markdown("### Correlation Heatmap")
st.altair_chart(chart_corr, use_container_width=True)

st.divider()

# -----------------------------
# Text before trajectory
# -----------------------------
st.markdown(
"""
The key thing to look at for this graph is the first column. For all regions we can see that each  
component has a moderate to very strong negative correlation with Fertility Rate. Looking at  
how those correlations change when we switch regions is interesting. Europe, as stated above,  
shows almost no correlation between the HDI components and Fertility Rate, whereas Oceania  
shows an abnormally strong negative correlation between GNI PC and Fertility Rate. It’s  
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