import streamlit as st
import pandas as pd
import json
import glob
import os

@st.cache_data
def load_all_data(folder_path):
    # Define the columns we expect (Prevent KeyError if no data found)
    expected_cols = [
        "Faction", "Unit Name", "Role", "Org Slot", "Points", "Troop Type", 
        "Innate Rules", "Special Rules", "Default Equipment", "Optional Upgrades",
        "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"
    ]
    
    all_rows = []
    
    # Construct absolute path to ensure we find the folder relative to this script
    # This helps if main.py is running from a different working directory
    base_dir = os.path.dirname(os.path.abspath(__file__)) # backend/
    root_dir = os.path.dirname(base_dir) # parent folder
    target_folder = os.path.join(root_dir, folder_path)
    
    json_files = glob.glob(os.path.join(target_folder, "*.json"))
    
    # DEBUG: Print what we found to the logs
    print(f"Looking for data in: {target_folder}")
    print(f"Found {len(json_files)} JSON files.")

    if not json_files:
        # Fallback: Try looking in the current working directory directly
        if os.path.exists(folder_path):
             json_files = glob.glob(os.path.join(folder_path, "*.json"))

    if not json_files:
        return pd.DataFrame(columns=expected_cols)

    for j_file in json_files:
        try:
            with open(j_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            faction = data.get("faction_name", "Unknown")
            
            for unit in data.get("units", []):
                optional_upgrades = [u['name'] for u in unit.get("upgrades", []) if not u.get('is_default')]
                
                for model in unit.get("models", []):
                    stats = model.get("stats", {})
                    
                    point_cost = model.get("cost", 0)
                    if point_cost == 0:
                        point_cost = unit.get("base_points", 0)

                    combined_rules = sorted(list(set(unit.get("rules", []) + model.get("rules", []))))
                    model_weapons = model.get("default_weapons", [])
                    unit_defaults = [u['name'] for u in unit.get("upgrades", []) if u.get('is_default')]
                    full_loadout = sorted(list(set(model_weapons + unit_defaults)))

                    all_rows.append({
                        "Faction": faction,
                        "Unit Name": model.get("name"),
                        "Role": model.get("role", "rank_and_file"),
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
        return pd.DataFrame(columns=expected_cols)

    df = pd.DataFrame(all_rows)
    
    numeric_cols = ["Points", "M", "WS", "BS", "S", "T", "W", "I", "A", "Ld"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
    
    return df