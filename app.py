import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Set up the app
st.set_page_config(page_title="Bakken Wells Dashboard", layout="wide")
st.title("🚀 Bakken Wells Interactive Dashboard")

# Load cleaned data
data_path = "bakken_wells_cleaned.csv"  # Make sure this CSV is in your working directory
@st.cache_data
def load_data():
    df = pd.read_csv(data_path, parse_dates=['Completion Date', 'Last Prod Rpt Date'])
    df['Completion Year'] = pd.to_datetime(df['Completion Date'], errors='coerce').dt.year
    return df

df = load_data()
st.success("Data loaded successfully.")

# Sidebar Filters
st.sidebar.header("📌 Filters")
formations = st.sidebar.multiselect("Select Formation(s)", df['Formation'].dropna().unique(), default=df['Formation'].dropna().unique())
operators = st.sidebar.multiselect("Select Operator(s)", df['Operator'].dropna().unique(), default=df['Operator'].dropna().unique())
years = st.sidebar.slider("Select Completion Year Range", int(df['Completion Year'].min()), int(df['Completion Year'].max()), (2005, 2024))

# Apply filters
filtered_df = df[(df['Formation'].isin(formations)) &
                 (df['Operator'].isin(operators)) &
                 (df['Completion Year'].between(*years))]

# KPI Summary
st.subheader("📊 Key Metrics")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Wells", f"{filtered_df.shape[0]:,}")
kpi2.metric("Avg Oil (bbl)", f"{filtered_df['Cum Oil'].mean():,.0f}")
kpi3.metric("Avg Gas (MCF)", f"{filtered_df['Cum Gas'].mean():,.0f}")
kpi4.metric("Avg Water (bbl)", f"{filtered_df['Cum Water'].mean():,.0f}")

# Visual 1: Top Operators
st.subheader("🔝 Top 10 Operators by Well Count")
top_ops = filtered_df['Operator'].value_counts().head(10)
fig1, ax1 = plt.subplots()
top_ops.plot(kind='bar', color='skyblue', ax=ax1)
ax1.set_title("Top Operators")
ax1.set_ylabel("Number of Wells")
ax1.tick_params(axis='x', rotation=45)
st.pyplot(fig1)

# Visual 2: Formation Distribution
st.subheader("🏗️ Well Count by Formation")
formation_counts = filtered_df['Formation'].value_counts()
fig2, ax2 = plt.subplots()
formation_counts.plot(kind='bar', color='green', ax=ax2)
ax2.set_title("Wells by Formation")
ax2.set_ylabel("Well Count")
ax2.tick_params(axis='x', rotation=45)
st.pyplot(fig2)

# Visual 3: Completion Trends Over Time
st.subheader("📈 Completions Over Time")
completion_trend = filtered_df.groupby('Completion Year')['File No'].count()
fig3, ax3 = plt.subplots()
completion_trend.plot(marker='o', color='orange', ax=ax3)
ax3.set_title("Well Completions per Year")
ax3.set_xlabel("Year")
ax3.set_ylabel("Count")
ax3.grid(True)
st.pyplot(fig3)

# Visual 4: Production over Time by Operator
st.subheader("💥 Oil Production Over Time (Top Operators)")
top5_ops = top_ops.index.tolist()
prod_trend = filtered_df[filtered_df['Operator'].isin(top5_ops)].groupby(['Completion Year', 'Operator'])['Cum Oil'].mean().unstack()
fig4, ax4 = plt.subplots()
prod_trend.plot(marker='o', ax=ax4)
ax4.set_title("Avg Oil Production by Operator")
ax4.set_xlabel("Year")
ax4.set_ylabel("Avg Cum Oil")
ax4.legend(title="Operator")
ax4.grid(True)
st.pyplot(fig4)

# Visual 5: Custom Scatter Analysis
st.subheader("🔎 Custom Scatter Plot")
x_axis = st.selectbox("Select X-Axis", ['Cum Oil', 'Cum Gas', 'Cum Water'])
y_axis = st.selectbox("Select Y-Axis", ['Cum Water', 'Cum Gas', 'Cum Oil'])
fig5, ax5 = plt.subplots()
ax5.scatter(filtered_df[x_axis], filtered_df[y_axis], alpha=0.6)
ax5.set_xlabel(x_axis)
ax5.set_ylabel(y_axis)
ax5.set_title(f"{y_axis} vs {x_axis}")
st.pyplot(fig5)

# Data download
st.download_button("Download Filtered Dataset", data=filtered_df.to_csv(index=False), file_name="filtered_bakken_data.csv")

# Show raw data
if st.checkbox("Show Raw Data"):
    st.dataframe(filtered_df)
