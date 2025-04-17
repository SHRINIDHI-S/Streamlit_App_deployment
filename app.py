import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# Set Streamlit page config
st.set_page_config(page_title="Bakken Wells Dashboard", layout="wide")
st.title("🚀 Bakken Wells Analysis - Automated Streamlit App")

# Caching for performance
@st.cache_data
def fetch_and_clean_data():
    base_url = "https://www.dmr.nd.gov/oilgas/bakkenwells.asp"
    formations = {}
    all_data = []

    # Fetch dropdown options
    soup = BeautifulSoup(requests.get(base_url).text, 'html.parser')
    dropdown = soup.find("select", {"name": "menu1"})
    for option in dropdown.find_all("option"):
        if option['value'] != "SF":
            formations[option.text.strip()] = option['value']

    # Scrape data for each formation
    for formation_name, formation_value in formations.items():
        response = requests.post(base_url, data={"menu1": formation_value})
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find("table", id="bakken-horizontal")
        if table:
            headers = [th.text.strip() for th in table.find_all("th")]
            rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]
            df = pd.DataFrame(rows, columns=headers)
            df['Formation'] = formation_name
            all_data.append(df)

    # Combine and clean
    final_df = pd.concat(all_data, ignore_index=True)
    date_cols = ['Completion Date', 'Last Prod Rpt Date']
    for col in date_cols:
        final_df[col] = pd.to_datetime(final_df[col], errors='coerce')
    prod_cols = ['Cum Oil', 'Cum Water', 'Cum Gas']
    for col in prod_cols:
        final_df[col] = pd.to_numeric(final_df[col].astype(str).str.replace(',', ''), errors='coerce')
    final_df.drop_duplicates(inplace=True)
    final_df['Completion Year'] = final_df['Completion Date'].dt.year
    return final_df

# Load data
with st.spinner("Fetching and cleaning Bakken well data..."):
    df = fetch_and_clean_data()
st.success("Data loaded successfully!")

# Sidebar Filters
st.sidebar.header("📌 Filters")
formations = st.sidebar.multiselect("Select Formations", df['Formation'].unique(), default=df['Formation'].unique())
year_range = st.sidebar.slider("Select Completion Year Range", int(df['Completion Year'].min()), int(df['Completion Year'].max()), (2006, 2024))

filtered_df = df[(df['Formation'].isin(formations)) & (df['Completion Year'].between(*year_range))]

# Top Operators
st.subheader("🔍 Top 10 Most Active Operators")
top_ops = filtered_df['Operator'].value_counts().head(10)
fig1, ax1 = plt.subplots()
top_ops.plot(kind='bar', ax=ax1, color='skyblue')
ax1.set_title("Top 10 Operators")
ax1.set_ylabel("Number of Wells")
ax1.tick_params(axis='x', rotation=45)
st.pyplot(fig1)

# Formation Distribution
st.subheader("📊 Wells by Formation")
formation_counts = filtered_df['Formation'].value_counts()
fig2, ax2 = plt.subplots()
formation_counts.plot(kind='bar', ax=ax2, color='green')
ax2.set_title("Well Count by Formation")
ax2.set_ylabel("Number of Wells")
ax2.tick_params(axis='x', rotation=45)
st.pyplot(fig2)

# Completion Trends Over Time
st.subheader("📈 Completion Trends Over Time")
completions = filtered_df.groupby('Completion Year')['File No'].count()
fig3, ax3 = plt.subplots()
completions.plot(marker='o', ax=ax3, color='orange')
ax3.set_title("Well Completions Over Time")
ax3.set_xlabel("Year")
ax3.set_ylabel("Completions")
ax3.grid(True)
st.pyplot(fig3)

# Trends by Top Operators
st.subheader("📉 Completion Trends by Top Operators")
top_5 = df['Operator'].value_counts().head(5).index
operator_trends = filtered_df[filtered_df['Operator'].isin(top_5)].groupby(['Completion Year', 'Operator']).size().unstack(fill_value=0)
fig4, ax4 = plt.subplots()
operator_trends.plot(marker='o', ax=ax4)
ax4.set_title("Completion Trends for Top 5 Operators")
ax4.set_xlabel("Year")
ax4.set_ylabel("Number of Completions")
ax4.grid(True)
ax4.legend(title="Operators")
st.pyplot(fig4)

# Completion Trends by Formation
st.subheader("🧭 Completion Trends by Formation")
formation_trends = filtered_df.groupby(['Completion Year', 'Formation']).size().unstack(fill_value=0)
fig5, ax5 = plt.subplots()
formation_trends.plot(marker='o', ax=ax5)
ax5.set_title("Completion Trends by Formation")
ax5.set_xlabel("Year")
ax5.set_ylabel("Number of Completions")
ax5.grid(True)
ax5.legend(title="Formation")
st.pyplot(fig5)

# Option to download cleaned dataset
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button("Download Cleaned Data as CSV", data=csv, file_name='bakken_wells_cleaned.csv', mime='text/csv')

# Optionally view raw data
if st.checkbox("Show Raw Data"):
    st.dataframe(filtered_df)
