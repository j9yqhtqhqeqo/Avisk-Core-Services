import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

input_data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/NN_Input_Revenue.csv')

housing_dataset = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/HousingData.csv')

housing_dataset = housing_dataset.rename(columns={'MEDV': 'Price'})

print(housing_dataset.describe())

X = housing_dataset.drop('Price', axis = 1)
y=housing_dataset['Price']

X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.33,random_state=33)

