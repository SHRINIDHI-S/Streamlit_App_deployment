import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import io

# Page Configuration
st.set_page_config(layout="wide", page_title="Bakken Well Intelligence Hub")
st.title(":oil_drum: Bakken Well Intelligence Hub")

@st.cache_data

def fetch_scrape_and_process():
    base_url = "https://www.dmr.nd.gov/oilgas/bakkenwells.asp"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dropdown = soup.find("select", {"name": "menu1"})
    formations = {option.text.strip(): option['value'] for option in dropdown.find_all("option") if option['value'] != "SF"}

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

# Web Scraped Data Analysis
def clean_and_analyze_scraped_data(raw_df):
    if raw_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    raw_df['Completion Date'] = pd.to_datetime(raw_df['Completion Date'], errors='coerce')
    raw_df['Last Prod Rpt Date'] = pd.to_datetime(raw_df['Last Prod Rpt Date'], errors='coerce')
    for col in ['Cum Oil', 'Cum Water', 'Cum Gas']:
        raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',', ''), errors='coerce')
    raw_df.drop_duplicates(inplace=True)
    raw_df['Completion Year'] = raw_df['Completion Date'].dt.year

    top_operators = raw_df['Operator'].value_counts().head(10)
    formation_counts = raw_df['Formation'].value_counts()
    completions_by_year = raw_df.groupby('Completion Year')['File No'].count()
    return top_operators, formation_counts, completions_by_year

# Load Preprocessed CSV Data
def load_csvs():
    header_df = pd.read_csv("well_header.csv", delimiter='|')
    prod_df = pd.read_csv("monthly_production.csv", delimiter='|')

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

# Fetch and process all data
raw_web_data = fetch_scrape_and_process()
top_ops, form_counts, completions = clean_and_analyze_scraped_data(raw_web_data)
merged_df, header_df = load_csvs()

# App Tabs
tabs = st.tabs([
    "Web Overview", 
    "Completion Timeline", 
    "Cycle & Production", 
    "Post-Peak Performers", 
    "County Comparisons"
])

with tabs[0]:
    st.header("Scraped Insights: Operators & Formations")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Operators")
        st.bar_chart(top_ops)
    with col2:
        st.subheader("Well Count by Formation")
        st.bar_chart(form_counts)

with tabs[1]:
    st.header("Well Completion Trends")
    st.line_chart(completions)

with tabs[2]:
    st.header("Cycle Time & Total Production by County")
    county_avg = header_df.groupby('county')['cycle_time'].mean().sort_values(ascending=False)
    county_prod = merged_df.groupby('county')['production'].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Average Cycle Time (days)")
        st.bar_chart(county_avg)
    with col2:
        st.subheader("Total Production")
        st.bar_chart(county_prod)

with tabs[3]:
    st.header("Top 90-Day Post Peak Production Wells")
    top_peaks = merged_df[['well_id', 'post_peak_90_day']].drop_duplicates().sort_values(by='post_peak_90_day', ascending=False).head(20)
    st.dataframe(top_peaks)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(top_peaks['well_id'].astype(str), top_peaks['post_peak_90_day'], color='teal')
    ax.set_xticklabels(top_peaks['well_id'], rotation=45)
    ax.set_title("Top 20 Wells by 90-Day Post Peak Production")
    st.pyplot(fig)

with tabs[4]:
    st.header("Compare Counties Side-by-Side")
    selected = st.multiselect("Select counties to compare:", merged_df['county'].unique(), default=merged_df['county'].unique()[:3])
    if selected:
        county_data = merged_df[merged_df['county'].isin(selected)].groupby(['county', 'date'])['production'].sum().reset_index()
        pivot = county_data.pivot(index='date', columns='county', values='production')
        st.line_chart(pivot)

st.success("Dashboard Loaded Successfully!")