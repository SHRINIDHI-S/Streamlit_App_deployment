import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import zipfile
import os

# Page Configuration
st.set_page_config(layout="wide", page_title="Bakken Well Intelligence Hub")
st.title("📊 Bakken Well Intelligence Hub")

# === WELCOME PAGE ===
st.markdown("""
### Welcome to the Bakken Well Intelligence Hub!

This interactive dashboard is built to automate the collection, analysis, and visualization of oil well data from the Bakken region. Here's what it does:

- 📥 **Scrapes live data** from the [NDIC site](https://www.dmr.nd.gov/oilgas/bakkenwells.asp) for all Bakken formations.
- 🧹 **Cleans and preprocesses** the raw well data for consistency.
- 📈 **Analyzes production trends**, cycle times, and operator/formation performance.
- 🧪 **Extracts** a CSV file from a zip archive (`monthly_production.csv.zip`) and combines it with header data.
- 🧠 **Visualizes** top-producing wells, completion trends, and 90-day post-peak production patterns.

Use the navigation tabs to explore the dataset and uncover actionable insights!
""")

# === Load and Unzip Data ===
@st.cache_data
def extract_zip():
    zip_path = "monthly_production.csv.zip"
    extract_dir = "extracted_data"
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return os.path.join(extract_dir, "monthly_production.csv")

# === Fetch Web Data ===
@st.cache_data
def fetch_scrape_and_process():
    base_url = "https://www.dmr.nd.gov/oilgas/bakkenwells.asp"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    dropdown = soup.find("select", {"name": "menu1"})
    formations = {option.text.strip(): option['value']
                  for option in dropdown.find_all("option") if option['value'] != "SF"}

    all_data = []
    for name, value in formations.items():
        res = requests.post(base_url, data={"menu1": value})
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find("table", id="bakken-horizontal")
        if table:
            headers = [th.text.strip() for th in table.find_all("th")]
            rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]
            df = pd.DataFrame(rows, columns=headers)
            df['Formation'] = name
            all_data.append(df)

    df_all = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    return df_all

def clean_scraped_data(df):
    df['Completion Date'] = pd.to_datetime(df['Completion Date'], errors='coerce')
    df['Last Prod Rpt Date'] = pd.to_datetime(df['Last Prod Rpt Date'], errors='coerce')
    for col in ['Cum Oil', 'Cum Water', 'Cum Gas']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    df.drop_duplicates(inplace=True)
    df['Completion Year'] = df['Completion Date'].dt.year
    return df

# === Load Merged Data ===
@st.cache_data
def load_and_process_data():
    prod_path = extract_zip()
    header_path = "well_header.csv"
    
    prod_df = pd.read_csv(prod_path, delimiter='|')
    header_df = pd.read_csv(header_path, delimiter='|')

    header_df['spud_date'] = pd.to_datetime(header_df['spud_date'], errors='coerce')
    header_df['completion_date'] = pd.to_datetime(header_df['completion_date'], errors='coerce')
    header_df['cycle_time'] = (header_df['completion_date'] - header_df['spud_date']).dt.days

    prod_df['date'] = pd.to_datetime(prod_df[['year', 'month']].assign(day=1))
    merged = pd.merge(prod_df, header_df, on='well_id', how='inner')

    peak = prod_df.loc[prod_df.groupby('well_id')['production'].idxmax()].copy()
    peak['start_date'] = peak['date']
    peak['end_date'] = peak['start_date'] + pd.DateOffset(months=3)
    prod_with_peak = prod_df.merge(peak[['well_id', 'start_date', 'end_date']], on='well_id', how='left')
    prod_with_peak['in_window'] = (prod_with_peak['date'] >= prod_with_peak['start_date']) & (prod_with_peak['date'] < prod_with_peak['end_date'])

    post_peak = prod_with_peak[prod_with_peak['in_window']].groupby('well_id')['production'].sum()
    merged = merged.merge(post_peak, on='well_id', how='left')
    merged.rename(columns={'production_y': 'post_peak_90_day'}, inplace=True)
    
    return merged, header_df

# === Fetch Data ===
raw_web_data = fetch_scrape_and_process()
cleaned_web = clean_scraped_data(raw_web_data)
merged_df, header_df = load_and_process_data()

# === Tabs ===
tabs = st.tabs([
    "Web Overview",
    "Cycle & Production",
    "90-Day Performance",
    "Completion Trends",
    "Summary Insights"
])

# === Tab 1 ===
with tabs[0]:
    st.header("📌 Overview from Web Data")
    top_ops = cleaned_web['Operator'].value_counts().head(10)
    formations = cleaned_web['Formation'].value_counts()
    completions = cleaned_web.groupby('Completion Year')['File No'].count()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Operators")
        st.bar_chart(top_ops)
    with col2:
        st.subheader("Well Count by Formation")
        st.bar_chart(formations)
    st.subheader("Completions Over Time")
    st.line_chart(completions)

# === Tab 2 ===
with tabs[1]:
    st.header("🔧 Cycle Time and Production")
    avg_cycle = header_df.groupby('county')['cycle_time'].mean().sort_values(ascending=False)
    total_prod = merged_df.groupby('county')['production'].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Avg Cycle Time (days)")
        st.bar_chart(avg_cycle)
    with col2:
        st.subheader("Total Production by County")
        st.bar_chart(total_prod)

# === Tab 3 ===
with tabs[2]:
    st.header("⏱️ 90-Day Post Peak Production")
    top_peaks = merged_df[['well_id', 'post_peak_90_day']].drop_duplicates().sort_values(by='post_peak_90_day', ascending=False).head(20)
    st.dataframe(top_peaks)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(top_peaks['well_id'].astype(str), top_peaks['post_peak_90_day'], color='purple')
    ax.set_title("Top 20 Wells by 90-Day Post Peak Production")
    ax.set_xticklabels(top_peaks['well_id'], rotation=45)
    st.pyplot(fig)

# === Tab 4 ===
with tabs[3]:
    st.header("📅 Completion Trends by Operator")
    top5 = cleaned_web['Operator'].value_counts().head(5).index.tolist()
    trends = cleaned_web[cleaned_web['Operator'].isin(top5)].groupby(['Completion Year', 'Operator']).size().unstack(fill_value=0)
    st.line_chart(trends)

# === Tab 5 ===
with tabs[4]:
    st.header("🧠 Summary Insights")
    st.markdown("""
    - **County 1** leads in both well count and production volume.
    - **Middle Bakken** and **Three Forks** are the most active formations.
    - Top 5 operators show consistent completion patterns year-over-year.
    - Some wells show exceptional short-term output post-peak – these could inform drilling strategy.
    
    ---
    ⚙️ _This app is designed to scale. Future features could include forecasting, economic analysis, and spatial visualizations._
    """)
