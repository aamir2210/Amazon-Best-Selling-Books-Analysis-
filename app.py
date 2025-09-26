# app.py
from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt

ROOT = Path(__file__).resolve().parent
CLEAN = ROOT / "outputs" / "bestsellers_clean.csv"

st.set_page_config(page_title="Amazon Best Sellers Explorer", page_icon="📚", layout="wide")

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.stop()
    df = pd.read_csv(path)
    # tidy types
    df["User Rating"] = pd.to_numeric(df["User Rating"], errors="coerce")
    df["Reviews"]     = pd.to_numeric(df["Reviews"], errors="coerce").astype("Int64")
    df["Price"]       = pd.to_numeric(df["Price"], errors="coerce")
    df["Year"]        = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Genre"]       = df["Genre"].astype(str).str.title()
    return df.dropna(subset=["User Rating", "Reviews", "Price", "Year"])

df = load_data(CLEAN)

# ───────────────── Sidebar filters ─────────────────
st.sidebar.header("Filters")
genres = sorted(df["Genre"].dropna().unique().tolist())
years  = (int(df["Year"].min()), int(df["Year"].max()))

sel_genre   = st.sidebar.multiselect("Genre", genres, default=genres)
sel_years   = st.sidebar.slider("Year range", years[0], years[1], value=years)
min_reviews = st.sidebar.slider("Minimum reviews", 0, int(df["Reviews"].max()), value=1000, step=500)
min_rating  = st.sidebar.slider("Minimum rating", 0.0, 5.0, value=4.0, step=0.1)
max_price   = st.sidebar.slider("Max price ($)", 0.0, float(df["Price"].max()),
                                value=float(df["Price"].quantile(0.9)))
dedupe      = st.sidebar.checkbox("Show unique titles only (keep most-reviewed entry)", value=False)

# Apply filters (no aggregation anywhere)
view = df[
    (df["Genre"].isin(sel_genre)) &
    (df["Year"].between(sel_years[0], sel_years[1])) &
    (df["Reviews"] >= min_reviews) &
    (df["User Rating"] >= min_rating) &
    (df["Price"] <= max_price)
].copy()

if dedupe:
    view = (view.sort_values("Reviews", ascending=False)
                 .drop_duplicates(subset=["Name", "Author"], keep="first"))

# ───────────────── Header & KPIs ─────────────────
st.title("📚 Amazon Best Sellers Explorer")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Books", f"{len(view):,}")
c2.metric("Unique authors", view["Author"].nunique() if "Author" in view else df["Author"].nunique())
c3.metric("Avg rating", f"{view['User Rating'].mean():.2f}" if not view.empty else "—")
c4.metric("Median price", f"${view['Price'].median():.2f}" if not view.empty else "—")

# ───────────────── Charts ─────────────────
if not view.empty:
    # Top authors
    top_auth = (view.groupby("Author", as_index=False)["Name"]
                    .count()
                    .rename(columns={"Name": "Num Books"})
                    .sort_values("Num Books", ascending=False)
                    .head(10))
    chart_auth = (
        alt.Chart(top_auth)
           .mark_bar()
           .encode(
               x=alt.X("Num Books:Q", title="Num Books"),
               y=alt.Y("Author:N", sort="-x", title="Author"),
               tooltip=["Author", "Num Books"]
           )
           .properties(title="Top 10 Authors by #Books")
    )
    st.altair_chart(chart_auth, use_container_width=True)

    colA, colB = st.columns(2)

    # Ratings histogram — no "(binned)" label, clearer Y title
    y_title = "Number of books" if dedupe else "Number of book records"
    hist = (
        alt.Chart(view)
           .mark_bar()
           .encode(
               x=alt.X("User Rating:Q", bin=alt.Bin(maxbins=20), title="User Rating"),
               y=alt.Y("count():Q", title=y_title),
               tooltip=[alt.Tooltip("count():Q", title=y_title)]
           )
           .properties(title="User Rating Distribution")
    )
    colA.altair_chart(hist, use_container_width=True)

    # Price vs Rating scatter (always has Year, since we don’t aggregate)
    scatter = (
        alt.Chart(view)
           .mark_circle(opacity=0.6, size=60)
           .encode(
               x=alt.X("Price:Q", title="Price ($)"),
               y=alt.Y("User Rating:Q", title="User Rating"),
               color=alt.Color("Genre:N"),
               tooltip=["Name","Author","Genre","User Rating","Reviews","Price","Year"]
           )
           .properties(title="Price vs Rating")
    )
    colB.altair_chart(scatter, use_container_width=True)
else:
    st.info("No rows match the current filters.")

# ───────────────── Table + download ─────────────────
st.subheader("Table")
display_cols = ["Name", "Author", "User Rating", "Reviews", "Price", "Year", "Genre"]
df_show = view[display_cols].reset_index(drop=True)   # no index column in table
st.dataframe(df_show, use_container_width=True)

@st.cache_data
def to_csv_bytes(df_):
    return df_.to_csv(index=False).encode("utf-8")

st.download_button(
    "↓ Download filtered data (CSV)",
    to_csv_bytes(df_show),
    file_name="filtered_bestsellers.csv",
    mime="text/csv",
)


# NOTE: Streamlit < Dec 2025 → use width=True
# After Dec 25, 2025 → replace with width="stretch"
#st.altair_chart(chart_auth, width=True)
