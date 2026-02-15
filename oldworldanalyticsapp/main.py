import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from backend.data_loader import load_all_data

# --- Page Config ---
st.set_page_config(
    page_title="Old World Analytics", 
    page_icon="⚔️", 
    layout="wide"
)

# --- 1. Load Data ---
DATA_FOLDER = "tow_data_json" 
df = load_all_data(DATA_FOLDER)

# --- 2. Pre-Processing: Champion Renaming ---
# We do this immediately so it shows up in charts, tables, and search
if 'Role' in df.columns:
    def format_name(row):
        if row['Role'] == 'champion':
            # Avoid double naming if the name is already "Champion"
            if row['Unit Name'].lower() == "champion":
                return "Champion"
            return f"Champion - {row['Unit Name']}"
        return row['Unit Name']
    
    df['Unit Name'] = df.apply(format_name, axis=1)

# --- 3. Helper: Unit Card Dialog ---
@st.dialog("Unit Profile", width="large")
def show_unit_card(row):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"**{row['Unit Name']}**")
        st.caption(f"{row['Faction']}  |  {row['Troop Type']}  |  {row['Org Slot']}")
    with col2:
        st.metric("Points", row['Points'])

    st.markdown("---")

    # Stat Grid
    stat_html = f"""
    <table style="width:100%; text-align:center; border:1px solid #444; margin-bottom: 20px;">
        <tr style="background-color:#333; color:white;">
            <th>M</th><th>WS</th><th>BS</th><th>S</th><th>T</th><th>W</th><th>I</th><th>A</th><th>Ld</th>
        </tr>
        <tr style="font-size:18px; font-weight:bold;">
            <td>{row['M']}</td><td>{row['WS']}</td><td>{row['BS']}</td>
            <td>{row['S']}</td><td>{row['T']}</td><td>{row['W']}</td>
            <td>{row['I']}</td><td>{row['A']}</td><td>{row['Ld']}</td>
        </tr>
    </table>
    """
    st.markdown(stat_html, unsafe_allow_html=True)

    tab_rules, tab_gear, tab_math = st.tabs(["📜 Rules", "🛡️ Wargear", "🧮 Math"])

    with tab_rules:
        st.markdown("**Innate Rules:**")
        if row['Innate Rules']:
            for rule in sorted(row['Innate Rules'].split(", ")):
                if rule.strip(): st.markdown(f"- {rule}")
        else:
            st.markdown("*None*")

    with tab_gear:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ⚔️ Default Loadout")
            if row['Default Equipment']:
                items = sorted([x.strip() for x in row['Default Equipment'].split(", ") if x.strip()])
                for item in items:
                    st.markdown(f"- {item}")
            else:
                st.info("No default equipment listed.")
        
        with c2:
            st.markdown("#### 💰 Options & Upgrades")
            if row['Optional Upgrades']:
                upgrades = sorted([x.strip() for x in row['Optional Upgrades'].split(", ") if x.strip()])
                for up in upgrades:
                    st.markdown(f"- {up}")
            else:
                st.caption("No further options.")

    with tab_math:
        st.write("Combat Value Score (Approx):")
        offense = (row['A'] * row['WS']) + (row['S'] * 1.5)
        defense = (row['T'] * 1.5) + (row['W'] * 2)
        st.progress(min(int(offense + defense), 100))
        st.caption(f"Offensive Rating: {offense:.1f} | Defensive Rating: {defense:.1f}")

# --- 4. Sidebar Filters ---
st.sidebar.title("⚔️ Data Filters")

# Faction Presets
RENEGADE_KEYWORDS = ["chaos dwarf", "daemon", "demon", "chaos", "dark elf", "lizard", "ogre", "skaven", "vampire"]
def is_renegade(faction_name):
    return any(k in str(faction_name).lower() for k in RENEGADE_KEYWORDS)

all_factions = sorted(df["Faction"].unique())
renegade_factions = [f for f in all_factions if is_renegade(f)]
official_factions = [f for f in all_factions if not is_renegade(f)]

def select_official(): st.session_state["faction_select"] = official_factions
def select_renegades(): st.session_state["faction_select"] = renegade_factions
def clear_all(): st.session_state["faction_select"] = []

col_p1, col_p2 = st.sidebar.columns(2)
col_p1.button("Official", on_click=select_official, use_container_width=True)
col_p2.button("Renegades", on_click=select_renegades, use_container_width=True)
st.sidebar.button("Clear Factions", on_click=clear_all, use_container_width=True)

# 1. Faction Selector
selected_factions = st.sidebar.multiselect("Factions", all_factions, key="faction_select")

# 2. Org Slot Selector
all_slots = sorted(df["Org Slot"].astype(str).unique())
selected_slots = st.sidebar.multiselect("Organization Slot", all_slots)

# 3. Troop Type Selector
all_types = sorted(df["Troop Type"].astype(str).unique())
selected_types = st.sidebar.multiselect("Troop Type", all_types)

# 4. Search Selector
all_rules = set(df['Special Rules'].explode().dropna().unique())
all_options = set()
if 'Optional Upgrades' in df.columns:
    opt_series = df['Optional Upgrades'].dropna().astype(str)
    for x in opt_series:
        all_options.update(x.split(", "))

search_terms = sorted(list(all_rules.union(all_options)))
selected_terms = st.sidebar.multiselect("Search Rules/Gear (e.g. Fly, Lance)", search_terms)

# 5. NEW: Champion Toggle
st.sidebar.markdown("---")
show_champs = st.sidebar.checkbox("Show Unit Champions", value=False)

# --- Apply Filtering ---
filtered_df = df.copy()

# A. Champion Filter (Default Exclude)
if not show_champs:
    filtered_df = filtered_df[filtered_df['Role'] != 'champion']

# B. Standard Filters
if selected_factions:
    filtered_df = filtered_df[filtered_df["Faction"].isin(selected_factions)]

if selected_slots:
    filtered_df = filtered_df[filtered_df["Org Slot"].isin(selected_slots)]

if selected_types:
    filtered_df = filtered_df[filtered_df["Troop Type"].isin(selected_types)]

if selected_terms:
    mask = filtered_df.apply(lambda row: any(term in str(row['Innate Rules']) or 
                                             term in str(row['Default Equipment']) or 
                                             term in str(row['Optional Upgrades']) 
                                             for term in selected_terms), axis=1)
    filtered_df = filtered_df[mask]

# Sort
filtered_df = filtered_df.sort_values(["Faction", "Org Slot", "Unit Name"])

# --- Main UI ---
st.title("🛡️ Warhammer: The Old World - Analytics")

if filtered_df.empty:
    st.info("👋 Use the sidebar to select Factions, Org Slots, or Search to begin.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Data Browser", "📈 Scatter Analysis", "🔍 Value Discovery"])
    
    with tab1:
        st.header("Unit Roster")
        st.caption(f"Showing **{len(filtered_df)}** units. 👈 Click a row for details.")
        
        # Display Columns
        display_cols = ["Faction", "Unit Name", "Org Slot", "Points", "Troop Type", "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"]
        
        event = st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            height=800,
            on_select="rerun",
            selection_mode="single-row"
        )

        if len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            selected_unit_data = filtered_df.iloc[selected_row_index]
            show_unit_card(selected_unit_data)

    with tab2:
        st.header("Efficiency Comparison")
        col1, col2 = st.columns(2)
        with col1:
            x_ax = st.selectbox("X Axis", ["Points", "W", "T", "S", "M"], index=0)
        with col2:
            y_ax = st.selectbox("Y Axis", ["Points", "W", "T", "S", "A", "WS", "I"], index=5)
        
        fig = px.scatter(
            filtered_df, x=x_ax, y=y_ax, color="Faction",
            hover_name="Unit Name", 
            hover_data=["Troop Type", "Innate Rules"],
            size="W", template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.header("Value Discovery")
        st.markdown("Weight characteristics to find under-pointed units.")
        
        col_m, col_c = st.columns([1, 3])
        with col_m:
            w_ws = st.slider("WS Weight", 0.5, 3.0, 1.5)
            w_s = st.slider("S Weight", 0.5, 3.0, 2.0)
            w_t = st.slider("T Weight", 0.5, 3.0, 2.0)
            w_w = st.slider("W Weight", 1.0, 5.0, 3.0)
            
            filtered_df["TCV"] = (
                (filtered_df["WS"] * w_ws) + (filtered_df["S"] * w_s) + 
                (filtered_df["T"] * w_t) + (filtered_df["W"] * w_w) + (filtered_df["A"] * 2.0)
            )
            filtered_df["Efficiency"] = (filtered_df["TCV"] / filtered_df["Points"]).replace([np.inf, -np.inf], 0)

        with col_c:
            
            fig_val = px.scatter(
                filtered_df, x="TCV", y="Points", color="Faction",
                hover_name="Unit Name", trendline="ols", template="plotly_dark"
            )
            st.plotly_chart(fig_val, use_container_width=True)