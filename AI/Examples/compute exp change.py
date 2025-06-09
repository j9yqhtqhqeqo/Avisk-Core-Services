import pandas as pd

# Load the data (assuming the data is in a CSV file)
# Replace 'file.csv' with the actual filename
file_path = '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/NN_Data_Input/Exp_PCT_CHG_SRC.csv'
df = pd.read_csv(file_path)


# Assuming your dataframe is named df
# First, sort the dataframe by company_name, year, and sector_exposure_path_name
df = df.sort_values(by=['company_name', 'year', 'sector_exposure_path_name'])

# Now, we need to calculate pct_change for each group of company_name and sector_exposure_path_name
df['Exp_Pct_Chg'] = df.groupby(['company_name', 'sector_exposure_path_name'])[
    'Combined_score'].pct_change()

# The pct_change method calculates the percentage change from the prior row, so no need to manually implement the formula.
# pct_change automatically calculates: (current - prior) / prior * 100

# Optional: Convert the pct_change to percentage format by multiplying by 100, if you need it as a percentage (not a decimal)
# df['Exp_Pct_Chg'] = df['Exp_Pct_Chg'] * 100

# If you want to see the updated dataframe:
print(df)

# Save the updated dataset
output_file_path = '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/NN_Data_Input/Exp_PCT_CHG_Updated.csv'
df.to_csv(output_file_path, index=False)

print(f"Updated file saved to {output_file_path}.")
