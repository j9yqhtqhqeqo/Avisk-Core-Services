import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

import tensorflow as tf
from keras import Sequential, layers,models,Input,optimizers, losses

# Prepare Data
input_data = pd.read_csv('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/NN_Input_Revenue.csv')
input_np =input_data.to_numpy()

print(np.shape(input_np))

X_Input = input_np[:,3:-1]
y_input = input_np[:,-1:].astype(float)

scalar = StandardScaler()
X_Scaled = scalar.fit_transform(X_Input)
y_Scaled = y_input/1_000_000_0

X_train,X_val,y_train,y_val = train_test_split(X_Scaled, y_Scaled,test_size=0.2)

revenue_model = Sequential()
revenue_model.add(Input(shape=(78,)))
revenue_model.add(layers.Dense(units=128, activation='relu'))
revenue_model.add(layers.Dense(units=128, activation='relu'))
revenue_model.add(layers.Dense(units=128, activation='relu'))
revenue_model.add(layers.Dense(1))
# revenue_model.summary()

revenue_model.compile(optimizer='adam',loss='mse',metrics=['mae'])

history = revenue_model.fit(x=X_train,y=y_train,batch_size=32,epochs=50,verbose=1)


# # Plot training and validation loss
# plt.figure(figsize=(12, 5))
# plt.subplot(1, 2, 1)
# plt.plot(history['mse'], label='Training Loss')
# plt.plot(history['val_mse'], label='Validation Loss')
# plt.title('Loss Over Epochs')
# plt.xlabel('Epochs')
# plt.ylabel('Loss')
# plt.legend()

# # Plot training and validation MAE
# plt.subplot(1, 2, 2)
# plt.plot(history.history['mae'], label='Training MAE')
# plt.plot(history.history['val_mae'], label='Validation MAE')
# plt.title('MAE Over Epochs')
# plt.xlabel('Epochs')
# plt.ylabel('Mean Absolute Error')
# plt.legend()

plt.tight_layout()
plt.show()


print("Model trained and saved successfully.")
