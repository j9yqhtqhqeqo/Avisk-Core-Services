import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from keras import Input
from keras import Sequential, Model
from keras.layers import Dense, Layer

input_data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/NN_Input_Revenue.csv')

housing_dataset = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/HousingData.csv')

housing_dataset = housing_dataset.rename(columns={'MEDV': 'Price'})

X = housing_dataset.drop('Price', axis=1)
y = housing_dataset['Price']

X = housing_dataset.fillna(0)
standard_scalar = StandardScaler()
X_Scaled = standard_scalar.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_Scaled, y, test_size=0.33, random_state=33)
print(X_train.shape)

model = tf.keras.Sequential([
    tf.keras.layers.Dense(input_shape=(14,)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(64, activation='linear'),

])
model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(
                  from_logits=True),
              metrics=['accuracy'])

# model.compile(loss ='mean_squared_error', optimizer ='adam', metrics ='mae')
model.summary()
