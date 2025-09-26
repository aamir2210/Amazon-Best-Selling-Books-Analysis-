# main.py
from pathlib import Path
import pandas as pd

# --------- Paths ----------
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "bestsellers with categories.csv"   # <= Kaggle file (exact name)
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


# --------- Load & Harmonize to Kaggle schema ----------
# Try standard read; if it comes in as one column, force comma parsing
df = pd.read_csv(DATA, engine="python", encoding="utf-8-sig")
if df.shape[1] == 1:
    df = pd.read_csv(DATA, sep=",", engine="python", encoding="utf-8-sig")

# If the file has extra columns (e.g., 13), keep the first 7 and rename to Kaggle headers
if df.shape[1] >= 7:
    df = df.iloc[:, :7]
    df.columns = ['Name', 'Author', 'User Rating', 'Reviews', 'Price', 'Year', 'Genre']
else:
    # If fewer than 7 columns, stop so we can inspect the file
    raise ValueError(f"Expected at least 7 columns; got {df.shape[1]}: {list(df.columns)}")



# Expected columns:
# ['Name', 'Author', 'User Rating', 'Reviews', 'Price', 'Year', 'Genre']

# --------- Clean / types ----------
df.columns = [c.strip() for c in df.columns]  # tidy headers

to_types = [
    ("User Rating", "float64"),
    ("Reviews", "Int64"),   # Pandas nullable int
    ("Price", "float64"),
    ("Year", "Int64"),
]
for col, dtype in to_types:
    df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)

# Normalize Genre values
df["Genre"] = df["Genre"].astype(str).str.strip().str.title()  # 'Fiction' / 'Non Fiction'

# Drop exact duplicates, if any
df.drop_duplicates(inplace=True)

# Save a cleaned copy
clean_path = OUT / "bestsellers_clean.csv"
df.to_csv(clean_path, index=False)
print(f"Saved cleaned dataset → {clean_path}")

# --------- Analyses ----------
# 1) Top authors by number of books
top_authors = df["Author"].value_counts().rename_axis("Author").reset_index(name="Num Books")
top_authors.to_csv(OUT / "top_authors.csv", index=False)
print("Saved → outputs/top_authors.csv")

# 2) Average rating by genre
avg_rating_by_genre = df.groupby("Genre", dropna=False)["User Rating"].mean().reset_index()
avg_rating_by_genre.to_csv(OUT / "avg_rating_by_genre.csv", index=False)
print("Saved → outputs/avg_rating_by_genre.csv")

# 3) Top 20 most-reviewed books
top20_reviewed = df.sort_values("Reviews", ascending=False).head(20)
top20_reviewed.to_csv(OUT / "top20_most_reviewed.csv", index=False)
print("Saved → outputs/top20_most_reviewed.csv")

print("\nDone. Check the 'outputs' folder.")

# 4) Top 10 highest-rated books with at least 10,000 reviews
top_rated_strong = (
    df[df["Reviews"] >= 10_000]
    .sort_values(["User Rating", "Reviews"], ascending=[False, False])
    .head(10)
)
top_rated_strong.to_csv(OUT / "top10_highest_rated_min10k_reviews.csv", index=False)
print("Saved → outputs/top10_highest_rated_min10k_reviews.csv")

# 5) Price + rating summary by genre
by_genre = (
    df.groupby("Genre", dropna=False)
      .agg(Avg_Rating=("User Rating", "mean"),
           Median_Price=("Price", "median"),
           Count=("Name", "count"))
      .reset_index()
)
by_genre.to_csv(OUT / "summary_by_genre.csv", index=False)
print("Saved → outputs/summary_by_genre.csv")

with pd.ExcelWriter(OUT / "report.xlsx", engine="openpyxl") as xls:
    df.to_excel(xls, sheet_name="Cleaned", index=False)
    top_authors.to_excel(xls, sheet_name="Top Authors", index=False)
    avg_rating_by_genre.to_excel(xls, sheet_name="Avg Rating by Genre", index=False)
    top20_reviewed.to_excel(xls, sheet_name="Top20 by Reviews", index=False)
    top_rated_strong.to_excel(xls, sheet_name="Top Rated ≥10k", index=False)
    by_genre.to_excel(xls, sheet_name="Genre Summary", index=False)

print("Saved → outputs/report.xlsx")

# ------- Charts: saved as PNGs and linked in the report -------
import matplotlib.pyplot as plt
CHARTS = OUT / "charts"
CHARTS.mkdir(exist_ok=True)

# --- Markdown report ---
total_books    = len(df)
unique_authors = df["Author"].nunique()
avg_rating     = df["User Rating"].mean()
median_price   = df["Price"].median()

# If you already computed 'by_genre' earlier, reuse it; otherwise:
by_genre = (
    df.groupby("Genre", dropna=False)
      .agg(Avg_Rating=("User Rating","mean"), Median_Price=("Price","median"), Count=("Name","count"))
      .reset_index()
)

md = f"""# Amazon Best Sellers – Quick Report

**Data source:** Kaggle  
**Rows:** {total_books}  
**Unique authors:** {unique_authors}  
**Average rating:** {avg_rating:.2f}  
**Median price:** ${median_price:.2f}

## Top 10 Authors by Number of Books
{top_authors.head(10).to_markdown(index=False)}

## Average Rating & Price by Genre
{by_genre.to_markdown(index=False)}

## Charts
![Top Authors](charts/top_authors.png)  
![Ratings Histogram](charts/ratings_hist.png)  
![Price vs Rating](charts/price_vs_rating.png)
"""

(OUT / "README.md").write_text(md, encoding="utf-8")
print("Saved → outputs/README.md")


# Bar: Top 10 authors by #books
ax = top_authors.head(10).plot(kind="bar", x="Author", y="Num Books", legend=False, title="Top 10 Authors by #Books")
plt.tight_layout()
plt.savefig(CHARTS / "top_authors.png"); plt.close()

# Histogram: User ratings
df["User Rating"].plot(kind="hist", bins=20, title="User Rating Distribution")
plt.xlabel("User Rating"); plt.tight_layout()
plt.savefig(CHARTS / "ratings_hist.png"); plt.close()

# Scatter: Price vs Rating
df.plot(kind="scatter", x="Price", y="User Rating", title="Price vs User Rating", alpha=0.6)
plt.tight_layout()
plt.savefig(CHARTS / "price_vs_rating.png"); plt.close()
