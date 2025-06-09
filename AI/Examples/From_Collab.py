from tensorflow.keras.callbacks import EarlyStopping
import tensorflow as tf
from tensorflow.keras import layers, models
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt


data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/NN_Input_Revenue.csv')
np_array = data.to_numpy()
NN_input = np_array[:, 2:]

X = NN_input[:, 2:-1]
arr = NN_input[:, -1:]

y = arr.astype(float)

y = y / 1_000_000_0


print(X.shape)
print(y.shape)


# Step 1: Normalize the input features using StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Step 2: Split the data into training and validation sets (80% training, 20% validation)
X_train, X_val, y_train, y_val = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42)


# Step 3: Build the TensorFlow model
model = models.Sequential()

# First Dense layer
# 128 units, ReLU activation
model.add(layers.Dense(128, input_shape=(77,), activation='relu'))
# Second Dense layer
model.add(layers.Dense(128, activation='relu'))  # 64 units, ReLU activation
# Third Dense layer
model.add(layers.Dense(64, activation='relu'))  # 32 units, ReLU activation
# # Output layer (1 unit for regression)
# No activation function for regression (linear output)
model.add(layers.Dense(1))

# Step 4: Compile the model
model.compile(optimizer='sgd', loss='mse', metrics=['mae'])

# Step 5: Train the model


early_stopping = EarlyStopping(
    monitor='val_loss', patience=10, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_data=(X_val, y_val),
    callbacks=[early_stopping],
    verbose=1
)
# Step 1: Make predictions on the validation set
y_pred = model.predict(X_val)

# Save the trained model
model.save('DataCompany_Revenue_Regression.h5')

# Plot training and validation loss
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()

# Plot training and validation MAE
plt.subplot(1, 2, 2)
plt.plot(history.history['mae'], label='Training MAE')
plt.plot(history.history['val_mae'], label='Validation MAE')
plt.title('MAE Over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Mean Absolute Error')
plt.legend()

plt.tight_layout()
plt.show()

print("Model trained and saved successfully.")


# Step 2: Compare predicted vs actual values (for the first 10 predictions)
print("Predicted values (first 10 predictions):", y_pred[:10])
print("Actual values (first 10):", y_val[:10])

# Step 3: Plot the predictions vs actual values
plt.figure(figsize=(12, 6))

# Plotting predicted vs actual values
plt.plot(y_val, label='Actual Values', color='blue',
         linestyle='dashed', marker='o')
plt.plot(y_pred, label='Predicted Values', color='red', marker='x')
plt.title('Predicted vs Actual Values')
plt.xlabel('Samples')
plt.ylabel('Values')
plt.legend()

# Show the plot
plt.show()

# Step 4: Evaluate model performance on the validation set (MAE, MSE)
mae = np.mean(np.abs(y_pred - y_val))  # Mean Absolute Error
mse = np.mean((y_pred - y_val) ** 2)  # Mean Squared Error

print(f"Mean Absolute Error (MAE): {mae}")
print(f"Mean Squared Error (MSE): {mse}")
