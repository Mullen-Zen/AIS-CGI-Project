import pandas as pd
import numpy as np
import glob
import os
import re

"""
Loads and cleans the contents of the data/ directory 
"""
def load_data():
    # Crosswalk matches CIP codes to SOC codes; essentially listing which degrees are relevant to which jobs
    crosswalk_path = os.path.join("data", "CIP2020_SOC2018_Crosswalk.xlsx")
    crosswalk = pd.read_excel(crosswalk_path, dtype=str, sheet_name="CIP-SOC")
    
    crosswalk = crosswalk.rename(columns={
        "CIP2020Code": "CIP_Code",
        "CIP2020Title": "CIP_Title",
        "SOC2018Code": "SOC_Code", 
        "SOC2018Title": "SOC_Title"
    })

    crosswalk["CIP_Code"] = crosswalk["CIP_Code"].astype(str).str.strip()
    crosswalk["SOC_Code"] = crosswalk["SOC_Code"].astype(str).str.strip()

    # Projections contains information on the current and projected employment for each SOC code, as well as predicted changes in job openings
    projections_path = os.path.join("data", "occupation.xlsx")
    # skip title row
    projections = pd.read_excel(projections_path, dtype=str, sheet_name="Table 1.2", header=1)
    # normalize headers
    projections.columns = projections.columns.str.strip()

    # rename columns to match standard keys
    projections = projections.rename(columns={
        "2023 National Employment Matrix code": "SOC_Code", 
        "2024 National Employment Matrix code": "SOC_Code", 
        "Employment, 2023": "Current_Employment",
        "Employment, 2024": "Current_Employment",
        "Employment, 2033": "Projected_Employment",
        "Employment, 2034": "Projected_Employment",
        "Occupational openings, 2023-33 annual average": "Annual_Openings",
        "Occupational openings, 2024-34 annual average": "Annual_Openings",
        "Occupational openings, 2024–34 annual average": "Annual_Openings"
    })

    if "SOC_Code" in projections.columns:
        projections["SOC_Code"] = projections["SOC_Code"].astype(str).str.strip()

    numeric_cols = ["Current_Employment", "Projected_Employment", "Annual_Openings"]
    for col in numeric_cols:
        if col in projections.columns:
            projections[col] = pd.to_numeric(projections[col], errors='coerce').fillna(0)


    path_pattern = os.path.join("data", "c20*_a.csv")
    all_files = glob.glob(path_pattern)

    supply_frames = []

    if not all_files:
        fallback = os.path.join("data", "c2024_a.csv")
        if os.path.exists(fallback):
            all_files = [fallback]
        else:
            raise FileNotFoundError("Completions data files not found in the data directory.")
        
    for filename in all_files:
        match = re.search(r'c(\d{4})_a', os.path.basename(filename), re.IGNORECASE)
        year = int(match.group(1)) if match else 2024 # Default if parsing fails

        try:
            df = pd.read_csv(filename, dtype=str)
            
            # Normalize headers
            df.columns = df.columns.str.strip()

            if 'AWLEVEL' in df.columns:
                df = df[df['AWLEVEL'].isin(['5', '7'])]

            df = df.rename(columns={
                "CIPCODE": "CIP_Code",
                "CTOTALT": "Graduates"
            })

            df['CIP_Code'] = df['CIP_Code'].astype(str).str.strip()
            df['Graduates'] = pd.to_numeric(df['Graduates'], errors='coerce').fillna(0)
            df['Year'] = year

            # Aggregate by CIP within this year (summing across all universities)
            df_agg = df.groupby(["CIP_Code", "Year"])['Graduates'].sum().reset_index()
            supply_frames.append(df_agg)

        except Exception as e:
            print(f"Skipping file {filename} due to one or more error(s): {e}")

    if supply_frames:
        supply_history = pd.concat(supply_frames, ignore_index=True)
    else:
        # Return empty structure if no data found to prevent crash
        supply_history = pd.DataFrame(columns=["CIP_Code", "Year", "Graduates"])

    return crosswalk, projections, supply_history

"""
Merges the three datasets into one DataFrame, indexed by degree (CIP)
"""
def get_master_dataframe():
    crosswalk, projections, supply_history = load_data()
    print("Loaded data")

    if supply_history.empty:
        print("No supply history data found. Returning empty master dataframe.")
        return pd.DataFrame(), supply_history, pd.DataFrame()

    # Aggregate demand by degree
    print("Merging crosswalk and projections")
    merged_demand = pd.merge(crosswalk, projections, on="SOC_Code", how="left")
    print("Merged crosswalk and projections")

    cols_to_sum = ["Current_Employment", "Projected_Employment", "Annual_Openings"]
    merged_demand[cols_to_sum] = merged_demand[cols_to_sum].fillna(0)
    
    # group by CIP code
    cip_demand = merged_demand.groupby("CIP_Code").agg({
        "CIP_Title": "first",
        "Current_Employment": "sum",
        "Projected_Employment": "sum",
        "Annual_Openings": "sum",
        "SOC_Code": "count"
    }).rename(columns={"SOC_Code": "Mapped_Job_Count"}).reset_index()

    latest_year = supply_history['Year'].max()
    current_supply = supply_history[supply_history['Year'] == latest_year].copy()
    print(f"Years of supply data found: {sorted(supply_history['Year'].unique())}")

    # Merge datasets
    master_df = pd.merge(cip_demand, current_supply, on="CIP_Code", how="inner")


    # Calculate metrics
    # Growth rate = (Projected - Current) / Current
    # the denominator of this formula is smoothed by adding 1 to each value to avoid zero division
    master_df['Job_Growth_Rate'] = (
        (master_df['Projected_Employment'] - master_df['Current_Employment']) / (master_df['Current_Employment'] + 1.0)
    )

    # Saturation index (bubble score) = Graduates / Annual Openings
    # If Annual Openings is 0 (or very close to it), Saturation is set to NaN.
    # This prevents degrees with "0 openings" from appearing as infinitely saturated.
    master_df['Saturation_Index'] = np.where(
        master_df['Annual_Openings'] > 0, 
        master_df['Graduates'] / master_df['Annual_Openings'], 
        np.nan
    )

    return master_df, supply_history, merged_demand

if __name__ == "__main__":
    try:
        df, history, details = get_master_dataframe()
        print("Data loaded successfully")
        if not history.empty:
            print(f"History Years Found: {sorted(history['Year'].unique())}")
            print(f"Total Degrees Analyzed: {len(df)}")
            if not df.empty:
                print("\nSample Data (Top 5 Saturated):")
                # Filter out NaNs to show true saturation bubbles
                valid_df = df.dropna(subset=['Saturation_Index'])
                print(valid_df.sort_values("Saturation_Index", ascending=False)[['CIP_Code', 'Graduates', 'Annual_Openings', 'Saturation_Index']].head())
    except Exception as e:
        print(f"Error: {e}")