import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Page config
st.set_page_config(layout="wide", page_title="Bakken Well Intelligence Hub")

# Title
st.title("\U0001F4C8 Bakken Well Intelligence Hub")

# Load data
@st.cache_data
def load_data():
    merged_df = pd.read_csv("merged_well_data.csv")
    production_by_county = pd.read_csv("production_by_county.csv", names=["County", "Total Production"], skiprows=1)
    cycle_time_by_county = pd.read_csv("cycle_time_by_county.csv", names=["County", "Avg Cycle Time"], skiprows=1)
    return merged_df, production_by_county, cycle_time_by_county

merged_df, production_by_county, cycle_time_by_county = load_data()

# Tabs
tabs = st.tabs(["Well Summary", "Temporal Trends", "County Intelligence", "Well Performance"])

# ------------------------- TAB 1 -------------------------
with tabs[0]:
    st.header("Well Summary Dashboard")
    selected_counties = st.multiselect(
        "Select Counties to Display",
        options=production_by_county["County"].unique(),
        default=production_by_county["County"].unique()[:5]
    )

    filtered_prod = production_by_county[production_by_county["County"].isin(selected_counties)]
    filtered_cycle = cycle_time_by_county[cycle_time_by_county["County"].isin(selected_counties)]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Total Production by County")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(filtered_prod["County"], filtered_prod["Total Production"], color='teal', edgecolor='black')
        ax.set_ylabel("Total Production")
        ax.set_xticklabels(filtered_prod["County"], rotation=45)
        st.pyplot(fig)

    with col2:
        st.subheader("Average Cycle Time by County")
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.bar(filtered_cycle["County"], filtered_cycle["Avg Cycle Time"], color='coral', edgecolor='black')
        ax2.set_ylabel("Cycle Time (Days)")
        ax2.set_xticklabels(filtered_cycle["County"], rotation=45)
        st.pyplot(fig2)

    st.subheader("Download Data")
    col3, col4 = st.columns(2)
    with col3:
        st.download_button("Download Merged Well Data", data=merged_df.to_csv(index=False), file_name="merged_well_data.csv", mime="text/csv")
    with col4:
        st.download_button("Download Production by County", data=production_by_county.to_csv(index=False), file_name="production_by_county.csv", mime="text/csv")

# ------------------------- TAB 2 -------------------------
with tabs[1]:
    st.header("Temporal Trends Analysis")
    st.markdown("Analyze how completions and production evolved over time.")

    # Completions over time
    st.subheader("Completions Over Time")
    completion_counts = merged_df.drop_duplicates('well_id').groupby(merged_df['completion_date'].str[:4])['well_id'].count()
    completion_counts.index.name = 'Year'

    fig3, ax3 = plt.subplots(figsize=(10, 5))
    completion_counts.plot(kind='line', marker='o', ax=ax3, color='orange')
    ax3.set_ylabel("Number of Completions")
    ax3.set_title("Well Completions Over Years")
    st.pyplot(fig3)

    # Production over time
    st.subheader("Production Over Time")
    production_trend = merged_df.groupby(['year', 'month'])['production'].sum().reset_index()
    production_trend['date'] = pd.to_datetime(production_trend[['year', 'month']].assign(day=1))

    fig4, ax4 = plt.subplots(figsize=(10, 5))
    ax4.plot(production_trend['date'], production_trend['production'], color='green')
    ax4.set_title("Total Production Over Time")
    ax4.set_ylabel("Production")
    st.pyplot(fig4)

# ------------------------- TAB 3 -------------------------
with tabs[2]:
    st.header("County Intelligence")
    county_selected = st.selectbox("Choose a County", merged_df['county'].unique())

    df_county = merged_df[merged_df['county'] == county_selected]

    st.subheader(f"Well Activity in {county_selected}")
    col1, col2 = st.columns(2)
    with col1:
        avg_cycle = df_county['cycle_time'].mean()
        st.metric("Average Cycle Time (days)", f"{avg_cycle:.1f}")
    with col2:
        total_prod = df_county['production'].sum()
        st.metric("Total Production", f"{total_prod:,.0f} bbl")

    st.subheader("Monthly Production Timeline")
    monthly_prod = df_county.groupby(['year', 'month'])['production'].sum().reset_index()
    monthly_prod['date'] = pd.to_datetime(monthly_prod[['year', 'month']].assign(day=1))

    fig5, ax5 = plt.subplots(figsize=(10, 4))
    ax5.plot(monthly_prod['date'], monthly_prod['production'], marker='o')
    ax5.set_ylabel("Production")
    ax5.set_title(f"Monthly Production in {county_selected}")
    st.pyplot(fig5)

# ------------------------- TAB 4 -------------------------
with tabs[3]:
    st.header("Well Performance Explorer")
    unique_ids = merged_df['well_id'].unique()
    well_selected = st.selectbox("Choose a Well ID", unique_ids)
    
    df_well = merged_df[merged_df['well_id'] == well_selected]

    if not df_well.empty:
        st.subheader(f"Cycle Time & Post-Peak Analysis for Well {well_selected}")
        col1, col2 = st.columns(2)
        with col1:
            cycle = df_well['cycle_time'].iloc[0]
            st.metric("Cycle Time", f"{cycle} days")
        with col2:
            post_peak = df_well['post_peak_90_day'].iloc[0]
            st.metric("90-Day Post-Peak Prod", f"{post_peak:,.0f} bbl")

        st.subheader("Production Trend")
        df_well_sorted = df_well.sort_values(by=['year', 'month'])
        df_well_sorted['date'] = pd.to_datetime(df_well_sorted[['year', 'month']].assign(day=1))

        fig6, ax6 = plt.subplots(figsize=(10, 4))
        ax6.plot(df_well_sorted['date'], df_well_sorted['production'], color='purple')
        ax6.set_title(f"Production Curve - Well {well_selected}")
        ax6.set_ylabel("Production")
        st.pyplot(fig6)

        st.dataframe(df_well_sorted[['year', 'month', 'production']].reset_index(drop=True))
