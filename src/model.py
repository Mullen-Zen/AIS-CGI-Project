import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

"""
Predicts the number of graduates for a given degree X (4) years in the future using linear regression on historical data from 2016-2024
"""
def predict_future_supply(supply_history, cip_code, current_year=2024, projection_years=4):
    degree_data = supply_history[supply_history['CIP_Code'] == cip_code].sort_values('Year')

    # first make sure there are enough data points
    if len(degree_data) < 2:
        last_val = degree_data['Graduates'].illoc[-1] if not degree_data.empty else 0
        return last_val, 0.0, degree_data # "no growth"
    
    # format data for scikit-learn
    X = degree_data['Year'].values.reshape(-1, 1)
    y = degree_data['Graduates'].values

    # train the linear regression model
    model = LinearRegression()
    model.fit(X, y)

    # predict future graduates
    target_year = current_year + projection_years
    future_X = np.array([[target_year]])
    predicted_grads = model.predict(future_X)[0]

    # calculate growth rate in grads per year
    growth_rate = model.coef_[0]

    # don't predict negative graduates
    return max(0, int(predicted_grads)), growth_rate, degree_data

"""
Finds degrees in the same 2-digit CIP code family that have less job saturation
"""
def get_alternatives(current_cip, master_df, reccomendations=3):
    if current_cip not in master_df['CIP_Code'].values:
        return pd.DataFrame() # no data found
    
    cip_family = current_cip.split('.')[0]
    current_saturation = master_df.loc[master_df['CIP_Code'] == current_cip, 'Saturation_Index'].values[0]

    # filter by:
    alternatives = master_df[
        (master_df['CIP_Code'].str.startswith(cip_family + '.')) &  # same family
        (master_df['CIP_Code'] != current_cip) &                    # not the same degree
        (master_df['Saturation_Index'] < current_saturation) &      # less saturated
        (master_df['Saturation_Index'].notna()) &                   # is a valid saturation value
        (master_df['Saturation_Index'] != 0)                        # is not exactly 0 (only possible with unrealistic outliers)
    ].copy()
    alternatives = alternatives.sort_values('Saturation_Index', ascending=True).head(reccomendations)

    return alternatives

"""
Adds a tag to the dataframe that indicates saturation
"""
def calculate_market_saturation(master_df):
    condititons = [
        (master_df['Saturation_Index'] > 1.5),
        (master_df['Saturation_Index'] < 0.8),
        (master_df['Saturation_Index'].isna())
    ]
    choices = ['Highly Saturated', 'Unsaturated', 'Unknown']

    master_df['Saturation_Tag'] = np.select(condititons, choices, default='Moderately Saturated')

    return master_df

# if __name__ == "__main__":
#     from data_loader import get_master_dataframe
    
#     print("--- Testing Model Logic ---")
#     try:
#         # 1. Load data via loader
#         master_df, history, details = get_master_dataframe()
#         master_df = calculate_market_saturation(master_df)
        
#         # 2. Pick a test degree (e.g., Computer Science 11.0101)
#         test_cip = "11.0101" 
#         if test_cip in master_df['CIP_Code'].values:
#             print(f"\nTesting Analysis for CIP: {test_cip}")
            
#             # Test Future Prediction
#             pred_grads, slope, hist = predict_future_supply(history, test_cip)
#             print(f"Historical Trend Slope: {slope:.2f} grads/year")
#             print(f"Predicted Graduates in 2028: {pred_grads}")
            
#             # Test Recommendations
#             recs = get_alternatives(test_cip, master_df)
#             print("\nRecommended Alternative Paths in same family:")
#             if not recs.empty:
#                 print(recs[['CIP_Code', 'CIP_Title', 'Saturation_Index', 'Saturation_Tag']].to_string(index=False))
#             else:
#                 print("No alternatives found.")
#         else:
#             print(f"Test CIP {test_cip} not found in dataset. Try checking your data files.")

#     except Exception as e:
#         print(f"Testing failed: {e}")