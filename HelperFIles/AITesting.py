import pandas as pd

# Sample data (paste your dataset here)

data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/TriangulationData.csv')

# Initialize the result list
results = []

# Process data year by year
for year in data['year'].unique():
    # Filter data for the current year
    year_data = data[data['year'] == year]
# Initialize the result list
results = []

# Group the data by company_name and year
grouped = data.groupby(['company_name', 'year'])

for (company, year), group in grouped:
    # Initialize a dictionary for each company-year combination
    result = {
        "company_name": company,
        "year": year
    }

    # Transform rows into columns
    for _, row in group.iterrows():
        for col in data.columns[3:]:
            new_header = f"{row['sector_exposure_path_name']} - {col}"
            result[new_header] = row[col]

    # Append the result dictionary to the results list
    results.append(result)

# Convert the results list into a DataFrame
result_df = pd.DataFrame(results)

result_df.fillna(0, inplace=True)
# Save the result to a CSV file (optional)

result_df.to_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/Formatted_TriangulationData.csv', index=False)

# Display the result
print(result_df)


# import pandas as pd

# # Sample data (replace with your uploaded dataset)
# data = pd.DataFrame({
#     'company_name': ['ANTERO RESOURCES Corp', 'ANTERO RESOURCES Corp'],
#     'year': [2013, 2013],
#     'sector_exposure_path_name': [
#         'Associated Energy Costs',
#         'Provisioning services (Raw Materials, Nutrients, Food, Energy)'
#     ],
#     'Sector_EI': [100, 91],
#     'Compnay_EI': [115, 105],
#     'Sector_EM': [79, 100],
#     'Company_EM': [102, 114],
#     'Sector_IM': [72, 100],
#     'Company_IM': [0, 0]
# })

# # Initialize the result with company_name and year
# result = {
#     # Keep the first company_name
#     "company_name": data['company_name'].iloc[0],
#     "year": data['year'].iloc[0]                  # Keep the first year
# }

# # Transform the dataset into a single row for other columns
# for index, row in data.iterrows():
#     # Skip 'company_name', 'year', and 'sector_exposure_path_name'
#     for col in data.columns[3:]:
#         new_header = f"{row['sector_exposure_path_name']} - {col}"
#         result[new_header] = row[col]

# # Convert the result into a DataFrame
# result_df = pd.DataFrame([result])

# result_df.to_csv('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/transformeddata.csv', index=False)

# # Display the result
# print(result_df)




# import pandas as pd

# # Sample data (replace this with your actual data)
# data = pd.read_csv(
#     '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/AIRegresssionData2.csv')


# # Transform the dataset into a single row
# result = {}

# for index, row in data.iterrows():
#     for col in data.columns[1:]:
#         new_header = f"{row['sector_exposure_path_name']} - {col}"
#         result[new_header] = row[col]

# # Convert the result into a DataFrame
# result_df = pd.DataFrame([result])

# # Save the result (optional)
# # 
# result_df.to_csv('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/transformeddata.csv', index=False)

# # Display the result
# print(data)
# print(result_df)




# import pandas as pd

# # Load the data (replace 'file.csv' with your actual file path)
# data = pd.read_csv(
#     '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/AIRegresssionData2.csv')


# print(data.head)
# # Create new headers by combining 'sector_exposure_path_name' and column names
# data_melted = pd.melt(
#     data,
#     id_vars=['company_name', 'year'],  # Columns to keep fixed
#     value_vars=['Sector_EI', 'Compnay_EI', 'Sector_EM',
#                 'Company_EM', 'Sector_IM', 'Company_IM'],  # Columns to combine
#     var_name='Metric',  # New column name for metrics
#     value_name='Value'  # New column name for values
# )

# print(data_melted.head)
# # # Combine 'sector_exposure_path_name' and 'Metric' for new headers
# # data_melted['New_Header'] = data_melted['sector_exposure_path_name'] + \
# #     " - " + data_melted['Metric']

# # # Pivot the data to create columns with new headers
# # reshaped_data = data_melted.pivot_table(
# #     index=['company_name', 'year'],  # Index columns
# #     columns='New_Header',  # New column headers
# #     values='Value',  # Values for the new columns
# #     aggfunc='first'  # Handle duplicates if any
# # )

# # # Reset the index to flatten the DataFrame
# # reshaped_data = reshaped_data.reset_index()

# # # Save the reshaped data to a new file (optional)
# # reshaped_data.to_csv('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/ProcessedAIRegData.csv', index = False)

# # # Display the reshaped data
# # print(reshaped_data.head())
