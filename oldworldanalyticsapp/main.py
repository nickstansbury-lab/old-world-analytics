import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import json
import os
from backend.data_loader import load_all_data

# --- Page Config ---
st.set_page_config(
    page_title="Old World Analytics", 
    page_icon="⚔️", 
    layout="wide"
)

# --- 1. Load Data & Reference Files ---
DATA_FOLDER = "tow_data_json" 
df = load_all_data(DATA_FOLDER)

# A. Load Equipment (Critical)
try:
    with open("equipment_values.json", "r") as f:
        EQUIPMENT_DB = json.load(f)
except FileNotFoundError:
    EQUIPMENT_DB = {"rank_and_file": {}, "character": {}}
    st.error("⚠️ 'equipment_values.json' not found. Gear valuation will be skipped.")

# B. Load Rules (Optional / Future)
try:
    with open("rules.json", "r") as f:
        RULES_DB = json.load(f)
except FileNotFoundError:
    RULES_DB = {"rank_and_file": {}, "character": {}}
    # Non-fatal warning in sidebar
    st.sidebar.warning("⚠️ 'rules.json' not found. Special Rules valuation will be skipped.")

# --- 2. Logic: Split Valuation (Robust) ---

def calculate_split_values(row):
    """
    Returns a tuple (gear_value, rules_value).
    Uses robust 'Reverse Lookup' to find items inside text strings.
    """
    role = "character" if row["Org Slot"] == "Characters" else "rank_and_file"
    
    # Get the specific lookup tables for this role
    # We default to 'rank_and_file' if key missing to be safe
    equip_prices = EQUIPMENT_DB.get(role, EQUIPMENT_DB.get("rank_and_file", {}))
    rule_prices = RULES_DB.get(role, RULES_DB.get("rank_and_file", {}))
    
    g_val = 0.0
    r_val = 0.0
    
    # 1. Calculate Equipment Value (Robust Scan)
    if row['Default Equipment']:
        # Normalize the unit's loadout string to lowercase for searching
        loadout_str = row['Default Equipment'].lower()
        
        # Iterate through every known item in our database
        for item_key, price in equip_prices.items():
            item_lower = item_key.lower()
            
            # Check if this item exists in the loadout string
            if item_lower in loadout_str:
                
                # --- Safeguards against Double Counting ---
                # 1. Don't count "Bow" if it's actually "Crossbow" or "Longbow"
                if item_lower == "bow":
                    if any(x in loadout_str for x in ["crossbow", "longbow", "shortbow", "elbow"]):
                        continue
                
                # 2. Don't count "Spear" if it's "Throwing Spear"
                if item_lower == "spear":
                    if any(x in loadout_str for x in ["throwing spear", "cavalry spear"]):
                        continue
                        
                # 3. Don't count "Armour" if "Heavy Armour" etc. (Though usually DB has full names)
                # (Add more exclusions here if you find other overlaps)
                
                g_val += price

    # 2. Calculate Rules Value (Standard Scan)
    if row['Innate Rules']:
        rules_str = row['Innate Rules'].lower()
        for rule_key, price in rule_prices.items():
            if rule_key.lower() in rules_str:
                r_val += price
                
    return g_val, r_val

# --- 3. Pre-processing ---
if "saved_units" not in st.session_state:
    st.session_state["saved_units"] = set()

# Champion / Character Name Formatting
if 'Role' in df.columns:
    def format_name(row):
        if row['Role'] == 'champion':
            if row['Unit Name'].lower() == "champion": return "Champion"
            return f"Champion - {row['Unit Name']}"
        return row['Unit Name']
    df['Unit Name'] = df.apply(format_name, axis=1)

# Generate Unique ID
df["unique_id"] = df["Faction"] + " - " + df["Unit Name"]

# --- 4. Unit Card Dialog ---
@st.dialog("Unit Profile", width="large")
def show_unit_card(row):
    # Calculate values on the fly
    g_val, r_val = calculate_split_values(row)
    total_extras = g_val + r_val
    naked_cost = max(row['Points'] - total_extras, 1.0)
    
    col_h1, col_h2 = st.columns([3, 2])
    with col_h1:
        st.subheader(f"**{row['Unit Name']}**")
        st.caption(f"{row['Faction']}  |  {row['Troop Type']}  |  {row['Org Slot']}")
    
    with col_h2:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", f"{row['Points']:.0f}")
        c2.metric("Naked Body", f"{naked_cost:.0f}")
        c3.metric("Gear", f"{g_val:.0f}", delta="included")
        c4.metric("Rules", f"{r_val:.0f}", delta="included")

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

    tab_rules, tab_gear, tab_math = st.tabs(["📜 Rules & Gear", "💰 Options", "🧮 Math"])

    role_key = "character" if row["Org Slot"] == "Characters" else "rank_and_file"
    # Safe getters for prices (Robust lookup for display too)
    e_prices = EQUIPMENT_DB.get(role_key, {})
    r_prices = RULES_DB.get(role_key, {})

    with tab_rules:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ⚔️ Equipment")
            if row['Default Equipment']:
                # We simply list what is in the string, but try to bold items we found value for
                items = sorted([x.strip() for x in row['Default Equipment'].split(",") if x.strip()])
                for item in items:
                    # check if this specific item triggered a value
                    val_str = ""
                    for db_k, db_p in e_prices.items():
                        if db_k.lower() in item.lower():
                            # Safeguard check again for display
                            if db_k.lower() == "bow" and any(x in item.lower() for x in ["crossbow", "longbow"]):
                                continue
                            val_str = f" `({db_p} pts)`"
                            break
                    st.markdown(f"- {item}{val_str}")
            else:
                st.caption("None")

        with c2:
            st.markdown("#### 📜 Special Rules")
            if row['Innate Rules']:
                rules = sorted([x.strip() for x in row['Innate Rules'].split(",") if x.strip()])
                for rule in rules:
                    val_str = ""
                    for db_k, db_p in r_prices.items():
                        if db_k.lower() in rule.lower():
                            val_str = f" `({db_p} pts)`"
                            break
                    st.markdown(f"- {rule}{val_str}")
            else:
                st.caption("None")

    with tab_gear:
        st.markdown("#### Available Upgrades")
        if row['Optional Upgrades']:
            upgrades = sorted([x.strip() for x in row['Optional Upgrades'].split(", ") if x.strip()])
            for up in upgrades:
                st.markdown(f"- {up}")
        else:
            st.caption("No upgrades listed.")

    with tab_math:
        st.write("Combat Efficiency Score:")
        offense = (row['A'] * row['WS']) + (row['S'] * 1.5)
        defense = (row['T'] * 1.5) + (row['W'] * 2)
        st.progress(min(int(offense + defense), 100))
        st.markdown(f"**True Efficiency (Stats per Naked Point):** {((offense+defense)/naked_cost):.2f}")

# --- 5. Sidebar Filters ---
st.sidebar.title("⚔️ Data Filters")
# Faction Logic
RENEGADE_KEYWORDS = ["chaos dwarf", "daemon", "demon", "chaos", "dark elf", "lizard", "ogre", "skaven", "vampire"]
def is_renegade(faction_name): return any(k in str(faction_name).lower() for k in RENEGADE_KEYWORDS)
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

selected_factions = st.sidebar.multiselect("Factions", all_factions, key="faction_select")
all_slots = sorted(df["Org Slot"].astype(str).unique())
selected_slots = st.sidebar.multiselect("Organization Slot", all_slots)
all_types = sorted(df["Troop Type"].astype(str).unique())
selected_types = st.sidebar.multiselect("Troop Type", all_types)

all_rules = set(df['Special Rules'].explode().dropna().unique())
all_options = set()
if 'Optional Upgrades' in df.columns:
    opt_series = df['Optional Upgrades'].dropna().astype(str)
    for x in opt_series: all_options.update(x.split(", "))
search_terms = sorted(list(all_rules.union(all_options)))
selected_terms = st.sidebar.multiselect("Search Rules/Gear", search_terms)

st.sidebar.markdown("---")
show_champs = st.sidebar.checkbox("Show Unit Champions", value=False)

st.sidebar.markdown("### 📋 My List")
list_mode = st.sidebar.radio("View Mode", ["All Units", "Saved List Only", "Exclude Saved List"])
st.sidebar.caption(f"**{len(st.session_state['saved_units'])}** units saved.")
if st.sidebar.button("🗑️ Clear Saved List"):
    st.session_state["saved_units"] = set()
    st.rerun()

# --- 6. Apply Filtering ---
filtered_df = df.copy()

if list_mode == "Saved List Only":
    filtered_df = filtered_df[filtered_df["unique_id"].isin(st.session_state["saved_units"])]
elif list_mode == "Exclude Saved List":
    filtered_df = filtered_df[~filtered_df["unique_id"].isin(st.session_state["saved_units"])]

if not show_champs:
    filtered_df = filtered_df[filtered_df['Role'] != 'champion']

if selected_factions: filtered_df = filtered_df[filtered_df["Faction"].isin(selected_factions)]
if selected_slots: filtered_df = filtered_df[filtered_df["Org Slot"].isin(selected_slots)]
if selected_types: filtered_df = filtered_df[filtered_df["Troop Type"].isin(selected_types)]
if selected_terms:
    mask = filtered_df.apply(lambda row: any(term in str(row['Innate Rules']) or 
                                             term in str(row['Default Equipment']) or 
                                             term in str(row['Optional Upgrades']) 
                                             for term in selected_terms), axis=1)
    filtered_df = filtered_df[mask]

filtered_df = filtered_df.sort_values(["Faction", "Org Slot", "Unit Name"])

# --- 7. Main UI ---
st.title("🛡️ Warhammer: The Old World - Analytics")

if filtered_df.empty:
    st.info("👋 Use the sidebar to select Factions, Org Slots, or Search to begin.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Data Browser", "📈 Scatter Analysis", "🔍 Value Discovery"])

    with tab1:
        st.header("Unit Roster")
        st.caption(f"Showing **{len(filtered_df)}** units.")
        display_cols = ["Faction", "Unit Name", "Org Slot", "Points", "Troop Type", "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"]
        event = st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True, height=600, on_select="rerun", selection_mode="multi-row")
        
        selected_indices = event.selection.rows
        if selected_indices:
            selected_ids = filtered_df.iloc[selected_indices]["unique_id"].tolist()
            last_selected_row = filtered_df.iloc[selected_indices[-1]] 
            st.markdown("#### ⚡ Selection Actions")
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button(f"➕ Add ({len(selected_ids)})"):
                    st.session_state["saved_units"].update(selected_ids)
                    st.rerun()
            with b2:
                if st.button(f"🔄 Replace ({len(selected_ids)})"):
                    st.session_state["saved_units"] = set(selected_ids)
                    st.rerun()
            with b3:
                if st.button(f"➖ Remove ({len(selected_ids)})"):
                    st.session_state["saved_units"].difference_update(selected_ids)
                    st.rerun()
            with b4:
                if st.button(f"📄 Details: {last_selected_row['Unit Name']}", type="primary"):
                    show_unit_card(last_selected_row)

    with tab2:
        st.header("Efficiency Comparison")
        chart_df = filtered_df
        if list_mode != "Saved List Only" and len(st.session_state["saved_units"]) > 0:
            if st.checkbox("Show only My Saved List in Chart", value=False):
                chart_df = df[df["unique_id"].isin(st.session_state["saved_units"])]
        c1, c2 = st.columns(2)
        with c1: x_ax = st.selectbox("X Axis", ["Points", "W", "T", "S", "M"], index=0)
        with c2: y_ax = st.selectbox("Y Axis", ["Points", "W", "T", "S", "A", "WS", "I"], index=5)
        fig = px.scatter(chart_df, x=x_ax, y=y_ax, color="Faction", hover_name="Unit Name", hover_data=["Troop Type", "Innate Rules"], size="W", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.header("Value Discovery")
        st.markdown("Analyze the 'True Cost' of units by stripping away the value of their free gear and rules.")
        col_m, col_c = st.columns([1, 3])
        with col_m:
            w_ws = st.slider("WS", 0.5, 3.0, 1.5)
            w_s = st.slider("S", 0.5, 3.0, 2.0)
            w_t = st.slider("T", 0.5, 3.0, 2.0)
            w_w = st.slider("W", 1.0, 5.0, 3.0)
            
            # --- CALCULATIONS ---
            def calc_total_extras(row):
                g, r = calculate_split_values(row)
                return g + r
                
            filtered_df["Extra_Value"] = filtered_df.apply(calc_total_extras, axis=1)
            filtered_df["Naked_Points"] = filtered_df["Points"] - filtered_df["Extra_Value"]
            filtered_df["Naked_Points"] = filtered_df["Naked_Points"].apply(lambda x: max(x, 1.0))
            
            filtered_df["TCV"] = ((filtered_df["WS"] * w_ws) + (filtered_df["S"] * w_s) + (filtered_df["T"] * w_t) + (filtered_df["W"] * w_w) + (filtered_df["A"] * 2.0))
            filtered_df["True_Efficiency"] = (filtered_df["TCV"] / filtered_df["Naked_Points"])

        with col_c:
            st.markdown("#### 💎 True Efficiency Scatter")
            st.caption("Y-Axis: **Stats per Naked Point**. Higher is better.")
            
            fig_val = px.scatter(
                filtered_df, x="Points", y="True_Efficiency", color="Faction", size="Extra_Value",
                hover_name="Unit Name", hover_data=["Extra_Value", "Naked_Points"],
                template="plotly_dark", height=600
            )
            st.plotly_chart(fig_val, use_container_width=True)
            
        st.markdown("#### 🏆 Top 'Freebie' Units")
        top_freebies = filtered_df[["Unit Name", "Faction", "Points", "Extra_Value", "Naked_Points"]].sort_values("Extra_Value", ascending=False).head(10)
        st.dataframe(top_freebies, hide_index=True, use_container_width=True)