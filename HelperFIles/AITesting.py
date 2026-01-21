import pandas as pd
import numpy as np

# Sample data (paste your dataset here)

data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/TriangulationData.csv')

print(data.head())

# Convert pandas DataFrame to numpy array
data_array = data.to_numpy()

print("\nData converted to numpy array:")
print("Array shape:", data_array.shape)
print("Array dtype:", data_array.dtype)
print("\nFirst few rows of the numpy array:")
print(data_array[:5])

# If you want only numeric columns as numpy array
numeric_data = data.select_dtypes(include=[np.number])
numeric_array = numeric_data.to_numpy()

print("\nNumeric data only:")
print("Numeric array shape:", numeric_array.shape)
print("Numeric array dtype:", numeric_array.dtype)
print("\nFirst few rows of the numeric numpy array:")
print(numeric_array[:5])

# ====== WORKING WITH TEXT DATA IN NUMPY ARRAYS ======

print("\n" + "="*50)
print("EXAMPLES OF STORING TEXT DATA IN NUMPY ARRAYS")
print("="*50)

# 1. Creating a simple text array
text_array = np.array(['Apple', 'Banana', 'Cherry', 'Date'])
print("\n1. Simple text array:")
print("Array:", text_array)
print("Data type:", text_array.dtype)
print("Shape:", text_array.shape)

# 2. Creating a 2D text array
text_2d = np.array([
    ['Apple', 'Red', 'Sweet'],
    ['Banana', 'Yellow', 'Sweet'],
    ['Lemon', 'Yellow', 'Sour']
])
print("\n2. 2D text array:")
print("Array:\n", text_2d)
print("Data type:", text_2d.dtype)
print("Shape:", text_2d.shape)

# 3. Extract text columns from your DataFrame
if 'company_name' in data.columns:
    company_names = data['company_name'].to_numpy()
    print("\n3. Company names from your data:")
    print("First 5 company names:", company_names[:5])
    print("Data type:", company_names.dtype)

# 4. Mixed data types (NumPy will convert everything to strings)
mixed_array = np.array(['Company A', 2023, 'Financial', 100.5])
print("\n4. Mixed data (converted to strings):")
print("Array:", mixed_array)
print("Data type:", mixed_array.dtype)

# 5. Specifying string length
fixed_length_array = np.array(['Apple', 'Banana'], dtype='U10')  # Unicode string, max 10 chars
print("\n5. Fixed-length string array:")
print("Array:", fixed_length_array)
print("Data type:", fixed_length_array.dtype)

# 6. Creating structured array with text and numbers
structured_dtype = np.dtype([
    ('company', 'U50'),    # Unicode string, max 50 chars
    ('year', 'i4'),        # 4-byte integer
    ('revenue', 'f8')      # 8-byte float
])

structured_array = np.array([
    ('Apple Inc', 2023, 394.3),
    ('Microsoft', 2023, 211.9),
    ('Google', 2023, 307.4)
], dtype=structured_dtype)

print("\n6. Structured array with text and numbers:")
print("Array:", structured_array)
print("Company names:", structured_array['company'])
print("Years:", structured_array['year'])
print("Revenues:", structured_array['revenue'])

# 7. Working with text columns from your DataFrame
text_columns = data.select_dtypes(include=['object'])
if not text_columns.empty:
    print("\n7. Text columns from your DataFrame:")
    for col in text_columns.columns:
        col_array = text_columns[col].to_numpy()
        print(f"{col}: {col_array[:3]}...")  # Show first 3 values
        print(f"  Data type: {col_array.dtype}")

# # Initialize the result list
# results = []

# # Process data year by year
# for year in data['year'].unique():
#     # Filter data for the current year
#     year_data = data[data['year'] == year]
# # Initialize the result list
# results = []

# # Group the data by company_name and year
# grouped = data.groupby(['company_name', 'year'])

# for (company, year), group in grouped:
#     # Initialize a dictionary for each company-year combination
#     result = {
#         "company_name": company,
#         "year": year
#     }

#     # Transform rows into columns
#     for _, row in group.iterrows():
#         for col in data.columns[3:]:
#             new_header = f"{row['sector_exposure_path_name']} - {col}"
#             result[new_header] = row[col]

#     # Append the result dictionary to the results list
#     results.append(result)

# # Convert the results list into a DataFrame
# result_df = pd.DataFrame(results)

# result_df.fillna(0, inplace=True)
# # Save the result to a CSV file (optional)

# result_df.to_csv(
#     '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/Formatted_TriangulationData.csv', index=False)

# # Display the result
# print(result_df)


# # import pandas as pd

# # # Sample data (replace with your uploaded dataset)
# # data = pd.DataFrame({
# #     'company_name': ['ANTERO RESOURCES Corp', 'ANTERO RESOURCES Corp'],
# #     'year': [2013, 2013],
# #     'sector_exposure_path_name': [
# #         'Associated Energy Costs',
# #         'Provisioning services (Raw Materials, Nutrients, Food, Energy)'
# #     ],
# #     'Sector_EI': [100, 91],
# #     'Compnay_EI': [115, 105],
# #     'Sector_EM': [79, 100],
# #     'Company_EM': [102, 114],
# #     'Sector_IM': [72, 100],
# #     'Company_IM': [0, 0]
# # })

# # # Initialize the result with company_name and year
# # result = {
# #     # Keep the first company_name
# #     "company_name": data['company_name'].iloc[0],
# #     "year": data['year'].iloc[0]                  # Keep the first year
# # }

# # # Transform the dataset into a single row for other columns
# # for index, row in data.iterrows():
# #     # Skip 'company_name', 'year', and 'sector_exposure_path_name'
# #     for col in data.columns[3:]:
# #         new_header = f"{row['sector_exposure_path_name']} - {col}"
# #         result[new_header] = row[col]

# # # Convert the result into a DataFrame
# # result_df = pd.DataFrame([result])

# # result_df.to_csv('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/transformeddata.csv', index=False)

# # # Display the result
# # print(result_df)


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
