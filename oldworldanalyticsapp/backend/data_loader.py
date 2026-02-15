import streamlit as st
import pandas as pd
import json
import glob
import os

@st.cache_data
def load_all_data(folder_path):
    all_rows = []
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        return pd.DataFrame() 

    for j_file in json_files:
        try:
            with open(j_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            faction = data.get("faction_name", "Unknown")
            
            for unit in data.get("units", []):
                # 1. Upgrades
                optional_upgrades = [u['name'] for u in unit.get("upgrades", []) if not u.get('is_default')]
                
                # 2. Models
                for model in unit.get("models", []):
                    stats = model.get("stats", {})
                    
                    # Cost Logic
                    point_cost = model.get("cost", 0)
                    if point_cost == 0:
                        point_cost = unit.get("base_points", 0)

                    # Rules Merge
                    combined_rules = sorted(list(set(unit.get("rules", []) + model.get("rules", []))))
                    
                    # Equipment Merge
                    model_weapons = model.get("default_weapons", [])
                    unit_defaults = [u['name'] for u in unit.get("upgrades", []) if u.get('is_default')]
                    full_loadout = sorted(list(set(model_weapons + unit_defaults)))

                    all_rows.append({
                        "Faction": faction,
                        "Unit Name": model.get("name"),
                        "Role": model.get("role", "rank_and_file"),  # <--- FIXED: Added this line
                        "Org Slot": unit.get("category", "Special"),
                        "Points": point_cost,
                        "Troop Type": stats.get("Type", "Unknown"),
                        "Innate Rules": ", ".join(combined_rules),
                        "Special Rules": combined_rules,
                        "Default Equipment": ", ".join(full_loadout),
                        "Optional Upgrades": ", ".join(optional_upgrades),
                        "M": stats.get("M", "-"), 
                        "WS": stats.get("WS", "-"), 
                        "BS": stats.get("BS", "-"),
                        "S": stats.get("S", "-"), 
                        "T": stats.get("T", "-"), 
                        "W": stats.get("W", "-"),
                        "I": stats.get("I", "-"), 
                        "A": stats.get("A", "-"), 
                        "Ld": stats.get("LD") or stats.get("Ld", "-")
                    })
        except Exception as e:
            print(f"Error loading {j_file}: {e}")

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    
    # Numeric conversion
    numeric_cols = ["Points", "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
    
    return df