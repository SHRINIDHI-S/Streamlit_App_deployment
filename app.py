import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# -------------------------------- CONFIG -------------------------------- #
st.set_page_config(page_title="Bakken Well Intelligence Hub", layout="wide")
st.title("🛢️ Bakken Well Intelligence Hub")

# ---------------------------- WELCOME PAGE ---------------------------- #
st.markdown("""
## 👋 Welcome to the Bakken Well Intelligence Hub

This dashboard provides insights into well production and development activities across the Bakken region.

### 🔧 Key Features:
- Live scraping from [ND DMR](https://www.dmr.nd.gov/oilgas/bakkenwells.asp)
- CSV-based well performance and cycle time analytics
- Time series and county-level production breakdowns
- 90-day post-peak production explorer

---

**Navigate through tabs to explore the dataset, discover trends, and drive data-informed decisions.**
""")

# ---------------------------- FUNCTIONS ---------------------------- #

@st.cache_data
def fetch_scrape_and_process():
    url = "https://www.dmr.nd.gov/oilgas/bakkenwells.asp"
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    dropdown = soup.find("select", {"name": "menu1"})
    formations = {o.text.strip(): o['value'] for o in dropdown.find_all("option") if o['value'] != "SF"}

    all_data = []
    for name, val in formations.items():
        html = requests.post(url, data={"menu1": val}).text
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find("table", id="bakken-horizontal")
        if table:
            headers = [th.text.strip() for th in table.find_all("th")]
            rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]
            df = pd.DataFrame(rows, columns=headers)
            df['Formation'] = name
            all_data.append(df)
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def clean_and_analyze_scraped_data(df):
    if df.empty: return None, None, None
    df['Completion Date'] = pd.to_datetime(df['Completion Date'], errors='coerce')
    df['Last Prod Rpt Date'] = pd.to_datetime(df['Last Prod Rpt Date'], errors='coerce')
    for col in ['Cum Oil', 'Cum Water', 'Cum Gas']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    df['Completion Year'] = df['Completion Date'].dt.year
    return (
        df['Operator'].value_counts().head(10),
        df['Formation'].value_counts(),
        df.groupby('Completion Year')['File No'].count()
    )

def load_csvs():
    header_df = pd.read_csv("well_header.csv", delimiter='|')
    prod_df = pd.read_csv("monthly_production.csv", delimiter='|')

    header_df['spud_date'] = pd.to_datetime(header_df['spud_date'], errors='coerce')
    header_df['completion_date'] = pd.to_datetime(header_df['completion_date'], errors='coerce')
    header_df['cycle_time'] = (header_df['completion_date'] - header_df['spud_date']).dt.days

    prod_df['date'] = pd.to_datetime(prod_df[['year', 'month']].assign(day=1))
    merged = pd.merge(prod_df, header_df, on='well_id', how='inner')

    # Peak window analysis
    peak = prod_df.loc[prod_df.groupby('well_id')['production'].idxmax()].copy()
    peak['start_date'] = peak['date']
    peak['end_date'] = peak['start_date'] + pd.DateOffset(months=3)
    prod_with_peak = prod_df.merge(peak[['well_id', 'start_date', 'end_date']], on='well_id', how='left')
    prod_with_peak['in_window'] = (
        (prod_with_peak['date'] >= prod_with_peak['start_date']) &
        (prod_with_peak['date'] < prod_with_peak['end_date'])
    )
    post_peak = prod_with_peak[prod_with_peak['in_window']].groupby('well_id')['production'].sum()
    merged = merged.merge(post_peak, on='well_id', how='left')
    merged.rename(columns={'production_y': 'post_peak_90_day'}, inplace=True)

    return merged, header_df

# ---------------------------- DATA LOAD ---------------------------- #
scraped_df = fetch_scrape_and_process()
top_ops, form_counts, completions = clean_and_analyze_scraped_data(scraped_df)
merged_df, header_df = load_csvs()

# ---------------------------- TABS ---------------------------- #
tabs = st.tabs([
    "🌐 Web-Scraped Insights",
    "📊 Cycle Time & Production",
    "🔥 90-Day Peak Performers",
    "🗺️ County Explorer",
    "📈 Production Over Time",
    "🧾 Summary & Insights"
])

# ---------------------------- TAB 1 ---------------------------- #
with tabs[0]:
    st.header("🌐 Insights from Web-Scraped ND DMR Data")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Operators")
        st.bar_chart(top_ops)
    with col2:
        st.subheader("Wells per Formation")
        st.bar_chart(form_counts)
    st.subheader("Completions by Year")
    st.line_chart(completions)

# ---------------------------- TAB 2 ---------------------------- #
with tabs[1]:
    st.header("📊 Cycle Time & Production by County")
    avg_cycle = header_df.groupby('county')['cycle_time'].mean().sort_values(ascending=False)
    total_prod = merged_df.groupby('county')['production'].sum().sort_values(ascending=False)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Average Cycle Time (days)")
        st.bar_chart(avg_cycle)
    with col2:
        st.subheader("Total Production")
        st.bar_chart(total_prod)

# ---------------------------- TAB 3 ---------------------------- #
with tabs[2]:
    st.header("🔥 Top Wells by Post-Peak 90-Day Production")
    top = merged_df[['well_id', 'post_peak_90_day']].drop_duplicates().sort_values(
        by='post_peak_90_day', ascending=False).head(20)
    st.dataframe(top)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(top['well_id'].astype(str), top['post_peak_90_day'], color='teal')
    ax.set_title("Top 20 Wells – 90-Day Post Peak Output")
    ax.set_ylabel("Production")
    ax.set_xticklabels(top['well_id'], rotation=45)
    st.pyplot(fig)

# ---------------------------- TAB 4 ---------------------------- #
with tabs[3]:
    st.header("🗺️ Monthly Production by County")
    selected = st.selectbox("Choose County", sorted(merged_df['county'].dropna().unique()))
    df_county = merged_df[merged_df['county'] == selected]
    line_data = df_county.groupby('date')['production'].sum()
    st.line_chart(line_data)

# ---------------------------- TAB 5 ---------------------------- #
with tabs[4]:
    st.header("📈 Total Production Over Time")
    all_prod = merged_df.groupby('date')['production'].sum()
    st.area_chart(all_prod)

# ---------------------------- TAB 6 ---------------------------- #
with tabs[5]:
    st.header("🧾 Summary & Business Insights")
    st.markdown("""
### Key Takeaways:

- ✅ **Continental Resources, Whiting Oil & Hess** dominate completions.
- 🧭 **Middle Bakken** is the most drilled and productive formation.
- ⚙️ Counties like **County 1, 6, and 9** are leading in output and efficiency.
- 📈 Post-peak metrics show production is highly concentrated in select wells.

---

### Potential Improvements:
- Add economic modeling (CapEx/OpEx)
- Include geospatial maps using Folium
- Add ML models to forecast cycle time and post-peak productivity

App powered by fully **automated data ingestion, processing, and visualization.**
""")

st.success("App fully loaded with automation and visualization complete!")
