"""
CS 230 Final Project: NASA Fireballs Explorer

Name: Elias Waich
Section: CS230 - 7
Dataset: NASA Fireballs (1988 to 2026), NASA/JPL Center for Near-Earth Object
         Studies (CNEOS), https://cneos.jpl.nasa.gov/fireballs/
App URL: https://danpdbnqob6slqg6hvea29.streamlit.app/
Description: An app for a teacher to explore where and when fireballs
             happened, how many were seen each year, and which were the
             biggest.
LLM used: Claude (Anthropic)
References: Streamlit documentation, PyDeck documentation,
            Matplotlib documentation
"""

import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
import streamlit as st

DATA_FILE = "cneos_fireball_data.csv"

# What the user can rank fireballs by in Question 3:
# label shown -> (column name, unit)
# #[DICT_DRIVEN] AUGMENT
# The AI's first dictionary only matched each label to a column name.
# I added the unit (joules, kilotons of TNT, km) to every entry.
# The keys fill the Question 3 dropdown. The column name picks what to
# sort by. The unit goes in the x-axis label of the bar chart.
# Example: the user picks "Impact energy". RANK_OPTIONS["Impact energy"]
# gives ("impact_kt", "kilotons of TNT"). The app sorts by impact_kt and
# the axis says "Impact energy (kilotons of TNT)".
RANK_OPTIONS = {
    "Total radiated energy": ("energy_j", "joules"),
    "Impact energy": ("impact_kt", "kilotons of TNT"),
    "Altitude": ("alt", "km"),
}


def load_data(filename):
    # The file has two header rows (the second one only names vx, vy, vz),
    # so skip both and give the columns my own names
    names = ["date", "lat", "lon", "alt", "vx", "vy", "vz",
             "energy_j", "impact_kt"]
    df = pd.read_csv(filename, skiprows=2, header=None, names=names)

    # Keep only the fireballs that have a location
    df = df.dropna(subset=["lat", "lon"]).copy()

    # lat and lon are text like "41.8S" or "173.1W".
    # Save the last letter, turn the rest into a number,
    # then make south and west negative.
    # #[STR_CLEAN] IDENTIFY & EXPLAIN
    # The AI wrote this to turn the text coordinates into numbers.
    # .str.strip() removes extra spaces, .str[-1] takes the last letter
    # (N, S, E or W) and .str[:-1] takes everything before it.
    # astype(float) makes that text a number. South and west are then made
    # negative because the map needs negative numbers for them.
    # Example: "41.8S" -> letter "S", number text "41.8" -> 41.8 -> -41.8.
    # "173.1E" stays 173.1.
    lat_dir = df["lat"].str.strip().str[-1]
    lon_dir = df["lon"].str.strip().str[-1]
    df["lat"] = df["lat"].str.strip().str[:-1].astype(float)
    df["lon"] = df["lon"].str.strip().str[:-1].astype(float)
    df.loc[lat_dir == "S", "lat"] = -df.loc[lat_dir == "S", "lat"]
    df.loc[lon_dir == "W", "lon"] = -df.loc[lon_dir == "W", "lon"]

    # Turn the text date into a real date and get the year
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # The file gives speed in three parts (vx, vy, vz).
    # The total speed is the square root of vx^2 + vy^2 + vz^2.
    df["speed"] = (df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2) ** 0.5
    return df


def get_year_range(data):
    # This function returns two values: the first year and the last year
    return int(data["year"].min()), int(data["year"].max())


# #[REUSE_FUNC] IDENTIFY & EXPLAIN
# The AI wrote one function that styles a chart (title, axis labels, grid,
# line color and width). Both charts call it, so the styling code is not
# copied twice. color has a default value, so a call can leave it out.
# Example: Question 2 calls style_chart(ax, title, "Year", "Number of
# fireballs") with no color. Python uses color="#d95f02" and the loop runs
# line.set_color("#d95f02") on the line. Question 3 also calls it, but a
# bar chart has no lines, so the loop does nothing and the bars keep the
# purple color given in barh.
def style_chart(ax, title, xlabel, ylabel, color="#d95f02"):
    # One place to style every chart, so both charts look the same
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    for line in ax.get_lines():
        line.set_color(color)
        line.set_linewidth(2)


st.title("NASA Fireballs Explorer")
st.write("Fireballs are bright meteors that explode in Earth's atmosphere. "
         "They were detected by U.S. government sensors from 1988 to 2026. "
         "This app is for a science teacher who wants to show a class "
         "where and when fireballs happen.")

# #[INPUT_CHECK] AUGMENT
# I added try/except so a missing file shows a message and not a crash.
# Example: if cneos_fireball_data.csv is not next to app.py, load_data
# raises FileNotFoundError. The except shows "Could not find ..." and
# st.stop() ends the script so no later line uses a df that was not made.
try:
    df = load_data(DATA_FILE)
except FileNotFoundError:
    st.error(f"Could not find {DATA_FILE}. Put it in the same folder as app.py.")
    st.stop()

min_year, max_year = get_year_range(df)

# Sidebar: how many fireballs have a value for each ranking choice.
# .items() gives each label with its (column, unit) pair, and the loop
# goes through them one at a time.
st.sidebar.header("About the data")
st.sidebar.write(f"{len(df)} fireballs have a location.")
for label, (col, unit) in RANK_OPTIONS.items():
    st.sidebar.write(f"{label}: {df[col].notna().sum()} fireballs")


# ---------------- Question 1 ----------------
st.header("Question 1: Where did the fastest fireballs happen?")

# Only some fireballs have a recorded speed, so the rest are left out here
df_speed = df.dropna(subset=["speed"])
st.caption(f"Only {len(df_speed)} of {len(df)} fireballs have a recorded speed. "
           "The other fireballs are not included in this question.")

min_v = int(df_speed["speed"].min())
max_v = int(df_speed["speed"].max()) + 1
speed = st.slider("Faster than (km/s)", min_v, max_v,
                  int(df_speed["speed"].median()))
years = st.slider("Years", min_year, max_year, (min_year, max_year))

result = df_speed[(df_speed["speed"] > speed)
                  & (df_speed["year"] >= years[0])
                  & (df_speed["year"] <= years[1])]

# #[INPUT_CHECK] AUGMENT
# I added this check so a choice with no matches shows a warning and not
# an empty map. result.empty is True when the filter keeps zero rows.
# Example: speed 72 with years 1988 to 2026 -> no fireball is faster than
# 72, result is empty, so the app shows "No fireballs match these
# choices. Try a lower speed or a wider range of years."
if result.empty:
    st.warning("No fireballs match these choices. Try a lower speed "
               "or a wider range of years.")
else:
    st.write(f"{len(result)} fireballs were faster than {speed} km/s "
             f"between {years[0]} and {years[1]}.")

    # The map only gets the columns it needs. The tooltip needs text,
    # so the date is turned into text and missing altitudes say "unknown".
    map_data = result[["lat", "lon"]].copy()
    map_data["speed"] = result["speed"].round(1)
    map_data["date_text"] = result["date"].dt.strftime("%Y-%m-%d")
    map_data["alt_text"] = result["alt"].apply(lambda a: "unknown" if pd.isna(a) else str(a))
    # Faster fireballs get bigger dots
    map_data["size"] = result["speed"] * 6000

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="[lon, lat]",
        get_radius="size",
        get_fill_color="[255, 80, 0, 160]",
        get_line_color="[0, 0, 0]",
        line_width_min_pixels=1,
        stroked=True,
        pickable=True,
    )
    view = pdk.ViewState(latitude=20, longitude=0, zoom=0.8)
    tooltip = {"html": "<b>{date_text}</b><br/>Speed: {speed} km/s"
                       "<br/>Altitude: {alt_text} km"}
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
                             tooltip=tooltip, map_style="dark"))

    st.caption("Hover over a dot to see the date, speed, and altitude. "
               "Bigger dots are faster fireballs. Fireballs are only "
               "detected by certain sensors, so this map does not show "
               "every meteor that hit the Earth.")


# ---------------- Question 2 ----------------
st.header("Question 2: How many fireballs were seen each year?")

hemisphere = st.radio("Hemisphere", ["Northern", "Southern"])

if hemisphere == "Northern":
    df_half = df[df["lat"] >= 0]
else:
    df_half = df[df["lat"] < 0]

# Count the fireballs in each year. Years with none get a 0.
counts = df_half.groupby("year").size()
counts = counts.reindex(range(min_year, max_year + 1), fill_value=0)

# #[INPUT_CHECK] AUGMENT
# Same idea for Question 2. counts has one number per year, so if the
# sum is 0 there is nothing to draw.
# Example: if a hemisphere had no fireballs, every year would be 0, the
# sum would be 0, and the warning shows instead of a flat chart.
if counts.sum() == 0:
    st.warning("No fireballs were found for this hemisphere.")
else:
    best_year = counts.idxmax()
    st.write(f"The {hemisphere.lower()} hemisphere had {counts.sum()} fireballs. "
             f"The busiest year was {best_year} with {counts.max()}.")

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(counts.index, counts.values, marker="o")
    style_chart(ax, f"Fireballs per year ({hemisphere} hemisphere)",
                "Year", "Number of fireballs")
    st.pyplot(fig)
    st.caption("The 2026 count is lower because the year is not over yet.")


# ---------------- Question 3 ----------------
st.header("Question 3: Which fireballs were the biggest?")

# The dropdown choices come from the dictionary at the top of the file
# #[LIST_COMP] REVISE/REWRITE
# The AI's original line was:
#     options = [label for label in RANK_OPTIONS]
#   - "for label in RANK_OPTIONS" goes through the dictionary keys
#   - each label is put into a new list without any change
# My simpler version is:
#     options = list(RANK_OPTIONS)
#   - list() on a dictionary gives its keys in order
# Both give ["Total radiated energy", "Impact energy", "Altitude"].
# The loop only copied the keys, so list() does the same job in less code
# and is easier to read.
options = list(RANK_OPTIONS)
rank_by = st.selectbox("Rank fireballs by", options)
top_n = st.number_input("How many fireballs to show", min_value=1,
                        max_value=25, value=10, step=1)

column, unit = RANK_OPTIONS[rank_by]
df_rank = df.dropna(subset=[column])
top = df_rank.sort_values(column, ascending=False).head(int(top_n))

# #[INPUT_CHECK] AUGMENT
# Same idea for Question 3. df_rank drops rows with no value in the chosen
# column, so top can end up empty.
# Example: if no row had a value for the chosen column, top.empty is True
# and the app shows "No fireballs have a value for this choice."
if top.empty:
    st.warning("No fireballs have a value for this choice.")
else:
    st.write(f"The top {len(top)} fireballs by {rank_by.lower()}:")

    # Label each bar with its date. The biggest is at the top of the chart.
    labels = [d.strftime("%Y-%m-%d") for d in top["date"]]
    fig2, ax2 = plt.subplots(figsize=(9, 5))
    ax2.barh(labels[::-1], top[column].values[::-1], color="#7570b3")
    style_chart(ax2, f"Top {len(top)} fireballs by {rank_by.lower()}",
                f"{rank_by} ({unit})", "Date of fireball")
    st.pyplot(fig2)

    # Altitude is already in the table, so do not add it twice
    table_columns = ["date", "lat", "lon", "alt"]
    # #[INPUT_CHECK] AUGMENT
    # alt is already in table_columns. If the user ranks by Altitude and
    # the column is added again, the table gets two alt columns and the app
    # crashed. This check only adds the ranked column when it is not alt.
    # Example: rank by "Impact energy" -> column is "impact_kt", so the table
    # is date, lat, lon, alt, impact_kt. Rank by "Altitude" -> column is
    # "alt", so the table stays date, lat, lon, alt.
    if column != "alt":
        table_columns.append(column)
    table = top[table_columns].copy()
    table["date"] = table["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(table, hide_index=True)
    st.caption(f"Only {len(df_rank)} of {len(df)} fireballs have a recorded "
               f"{rank_by.lower()}.")