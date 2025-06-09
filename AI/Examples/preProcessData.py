import pandas as pd

# Load your dataset
df = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/Reg_Analysis/NN_Stage0_Stk_Chg_Pct.csv')

# Create a new column 'sector_exposure_id' with unique integer values for each unique sector_exposure_path_name
df['sector_exposure_id'] = pd.factorize(df['sector_exposure_path_name'])[0]

# Function to normalize stock price change


def compute_normalized_stock_price_change(group):
    total_score = group['Compnay_EI'].sum()
    if total_score == 0:
        group['Normalized_Stock_Price_Change'] = 0
    else:
        group['Normalized_Stock_Price_Change'] = (
            group['CHG_PER_STOCK_PRICE'] *
            group['Compnay_EI'] / total_score
        )
    return group


# Grouping by company_name, year, and sector_exposure_path_name
df = df.groupby(['company_name', 'year']).apply(
    compute_normalized_stock_price_change)

# Save the updated DataFrame to a CSV file
output_file = '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/Reg_Analysis/EI_Stk_Pct_Chg.csv'
df.to_csv(output_file, index=False)

print(f"Results saved to {output_file}")
