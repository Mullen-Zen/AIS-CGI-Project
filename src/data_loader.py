import pandas as pd
import numpy as np

"""
Loads and cleans the contents of the data/ directory 
"""
def load_data():
    # Crosswalk matches CIP codes to SOC codes; essentially listing which degrees are relevant to which jobs
    crosswalk = pd.read_excel("/data/CIP2020_SOC2018_Crosswalk.xlsx", dtype=str, sheet_name="CIP-SOC")
    crosswalk = crosswalk.rename(columns={
        "CIP2020Code": "CIP_Code",
        "CIP2020Title": "CIP_Title",
        "SOC2018Code": "SOC_Code", 
        "SOC2018Title": "SOC_Title"
    }) # Column name consistency
    crosswalk["CIP_Code"] = crosswalk["CIP_Code"].astype(str).str.strip()
    crosswalk["SOC_Code"] = crosswalk["SOC_Code"].astype(str).str.strip() # Cleaning

    # Projections contains information on the current and projected employment for each SOC code, as well as predicted changes in job openings
    projections = pd.read_excel("/data/occupation.xlsx", dtype=str, sheet_name="Table 1.2")
    projections = projections.rename(columns={
        "2024 National Employment Matrix code": "SOC_Code",
        "Employment, 2024": "Current_Employment",
        "Employment, 2034": "Projected_Employment",
        "Occupational openings, 2024-34 annual average": "Annual_Openings"
    })
    projections["SOC_Code"] = projections["SOC_Code"].astype(str).str.strip()

    # Completions contains information on the number of awards earned for each SIP code
    completions = pd.read_csv("/data/c2024_a.csv", dtype=str)
    # We only care about bachelor's and master's degrees because the focus is on job readiness
    completions = completions[completions['AWLEVEL'].isin([5, 7])] 
    completions = completions.rename(columns={
        "CIPCODE": "CIP_Code",
        "CTOTALT": "Graduates"
    })
    completions['CIP_Code'] = completions['CIP_Code'].astype(str).str.strip()
    #TODO: multiple completions years for time series aggregation. something like
    # supply_history = ipeds.groupby(['CIP_Code', 'Year'])['Graduates'].sum().reset_index()

    return crosswalk, projections, completions

"""
Merges the three datasets into one DataFrame, indexed by degree (CIP)
"""
def get_master_dataframe():
    crosswalk, projections, completions = load_data()

    # Aggregate demand by degree
    # (crosswalk -> projections)
    merged_demand = pd.merge(crosswalk, projections, on="SOC_CODE", how="left")
    # replace nan values with 0 (no demand)
    cols_to_sum = ["Current_Employment", "Projected_Employment", "Annual_Openings"]
    merged_demand[cols_to_sum] = merged_demand[cols_to_sum].fillna(0)
    # group by CIP code
    cip_demand = merged_demand.groupby("CIP_Code").agg({
        "CIP_Title": "first",
        "Current_Employment": "sum",
        "Projected_Employment": "sum",
        "Annual_Openings": "sum"
    }).reset_index()

    # Get latest supply data (graduates) #TODO: finish this with multiple years' data
    # latest_year = supply_history['Year'].max() #TODO: see above todo here and for the following line
    # current_supply = supply_history[supply_history['Year'] == latest_year].copy()
    current_supply = completions

    # Merge datasets
    master_df = pd.merge(cip_demand, current_supply, on="CIP_CODE", how="inner")

    # Calculate saturation index (bubble scores) for each degree
    master_df["Saturation_Index"] = None #TODO:

    master_df['Job_Growth_Rate'] = (
        (master_df['Projected_Employment'] - master_df['Current_Employment']) / master_df['Current_Employment']
    )

    return master_df, completions, merged_demand

# debug only
if __name__ == "__main__":
    df, history, details = get_master_dataframe()
    print("Master DF Head:")
    print(df.head())