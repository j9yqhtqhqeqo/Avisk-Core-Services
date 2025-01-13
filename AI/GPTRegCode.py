import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# Example dataset - replace this with your actual dataset
# X is your input features (193 samples, 77 features)
# y is your target variable (193 samples, 1)
np.random.seed(42)
X = np.random.rand(193, 77)  # Replace with your actual input features
y = np.random.rand(193, 1)   # Replace with your actual target labels

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
model.add(layers.Dense(64, activation='relu'))  # 64 units, ReLU activation
# Third Dense layer
model.add(layers.Dense(32, activation='relu'))  # 32 units, ReLU activation
# Output layer (1 unit for regression)
# No activation function for regression (linear output)
model.add(layers.Dense(1))

# Step 4: Compile the model
model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# Step 5: Train the model
history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_data=(X_val, y_val),
    verbose=1
)

# Optionally, print the model summary
model.summary()

# Step 6: Plot the training and validation loss
plt.figure(figsize=(12, 6))

# Plot loss
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Training and Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss (MSE)')
plt.legend()

# Plot MAE (Mean Absolute Error)
plt.subplot(1, 2, 2)
plt.plot(history.history['mae'], label='Training MAE')
plt.plot(history.history['val_mae'], label='Validation MAE')
plt.title('Training and Validation MAE')
plt.xlabel('Epochs')
plt.ylabel('MAE')
plt.legend()

plt.tight_layout()
plt.show()


data = pd.read_csv(
    '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Financial Data/PreprocessData/NN_Input_Revenue.csv')
np_array = data.to_numpy()
NN_input = np_array[:, 2:]

X = NN_input[:, 2:-1]  # Random data of shape (193, 80)
y = NN_input[:, -1:]     # Random target values of shape (193,)

print(X.shape)
print(y.shape)
