import torch
from torch import nn
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset



print(torch.__version__)
device = "cuda" if torch.cuda.is_available() else 'cpu'
print(device)


def get_data():
        weight = 0.7
        bias = 0.3

        start = 0
        end = 1
        step = 0.02

        X = torch.arange(start=start, end=end, step=step).unsqueeze(dim=1)
        y = weight*X+bias

        # Split Data
        train_split = int(0.8*len(X))
        X_train, y_train = X[:train_split], y[:train_split]
        X_test, y_test = X[train_split:], y[train_split:]

        return X_train, y_train, X_test, y_test

def load_housing_data():

    data = pd.read_csv(
        '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/AI/HousingData.csv', dtype=np.float32)


    housing_dataset = data.rename(columns={'MEDV': 'Price'})

    housing_dataset = housing_dataset.fillna(0)

    # print(housing_dataset)

   

    X = housing_dataset.drop('Price', axis=1).to_numpy()
    y = housing_dataset['Price'].to_numpy()

    standard_scalar = StandardScaler()
    X_Scaled = standard_scalar.fit_transform(X)


    X_train, X_val, y_train, y_val = train_test_split(
        X_Scaled, y, test_size=0.33, random_state=33)
    
    X_train = torch.tensor(X_train, dtype=torch.float32)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.float32)
    return X_train, y_train, X_val, y_val

class LinearRegressionModel(nn.Module):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.weights = nn.Parameter(torch.randn(1,requires_grad=True,dtype=torch.float))
        self.bias = nn.Parameter(torch.randn(1,requires_grad=True, dtype=torch.float))

    def forward(self, x:torch.tensor) -> torch.tensor:
        return self.weights*x + self.bias

class ESGLinearNN(nn.Module):
    def __init__(self):
        model = nn.Sequential(
            nn.Linear(8,24),
            nn.ReLU(),
            nn.Linear(24,12),
            nn.ReLU(),
            nn.Linear(12, 6),
            nn.ReLU(),
            nn.Linear(6,1)
        )

class Utils:
    
    def plot_predictions_graph(self,train_data, train_labels, test_data, test_labels, predictions=None):
        plt.figure(figsize=(10, 7))
        plt.scatter(train_data, train_labels, c='b', s=4, label='Training Data')

        plt.scatter(test_data, test_labels, c='g', s=4, label='Validation Data')

        if (predictions is not None):
            plt.scatter(test_data, predictions, c='r', s=4, label='Predictions')

        plt.legend()
        plt.show()


    def plot_loss_graph(self,epoch_count, training_loss, validation_loss):
        plt.plot(epoch_count, training_loss, label='Training Loss')
        plt.plot(epoch_count, validation_loss, label='Training Data')
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.title('Training vs. Validation Loss')
        plt.legend()
        plt.show()


class ESGDataTrainer:

    def __init__(self):
        self.epoch_count = []
        self.training_loss_list = []
        self.validation_loss_list = []
        self.train_data, self.train_labels, self.validation_data, self.validation_labels, self.prediction_labels = any, any, any, any,any

    def train_and_validate(self, train_data, train_labels, validation_data, validation_labels, learning_rate=0.01, epochs=10, plot_predictions=False, plot_loss=True):
        self.train_data, self.train_labels, self.validation_data, self.validation_labels = train_data, train_labels, validation_data, validation_labels

        self.esg_model = LinearRegressionModel()
        self.loss_fn = nn.L1Loss()
        self.optimizer = torch.optim.SGD(params=self.esg_model.parameters(),
                                         lr=learning_rate)


        ## Instantiate the Model
        torch.manual_seed(42)
        ## Training Loop
        ## Loop through the Data an optimze the parameters
        for epoch in range(epochs):
            self.epoch_count.append(epoch)

            self.esg_model.train()
            # Forward pass:
            y_pred = self.esg_model(self.train_data)

            # Calculate Loss
            loss = self.loss_fn(y_pred, self.train_labels)
            self.training_loss_list.append(loss.detach().numpy())
            
            # Optimizer
            self.optimizer.zero_grad()

            # Backpropagation
            loss.backward()

            # Perform Gradient descent
            self.optimizer.step()

            # Perform Predictions and capture test loss
            self.esg_model.eval()
            with torch.inference_mode():
                self.prediction_labels = self.esg_model(self.validation_data)
                validation_loss = self.loss_fn(
                    self.prediction_labels, self.validation_labels)
                self.validation_loss_list.append(
                    validation_loss.detach().numpy())
                print(f'Running epoch -- {epoch+1}  of {epochs}, training loss ={
                      loss},  validation loss ={validation_loss}')
                print(self.esg_model.state_dict())
       
        plotter = Utils()
        if(plot_predictions):
            plotter.plot_predictions_graph(self.train_data, self.train_labels, self.validation_data,
                             self.validation_labels, self.prediction_labels)
        if(plot_loss):
            plotter.plot_loss_graph(
                self.epoch_count, self.training_loss_list, self.validation_loss_list)

    def train_and_validate_house_data(self, train_data, train_labels, validation_data, validation_labels, learning_rate=0.01, epochs=10, plot_predictions=False, plot_loss=True):
        self.train_data = train_data
        self.train_labels = train_labels
        self.validation_data = validation_data
        self.validation_labels = validation_labels

        # self.esg_model = ESGLinearNN()
        self.esg_model = nn.Sequential(
            nn.Linear(13, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
        self.loss_fn = nn.L1Loss()
        self.optimizer = torch.optim.SGD(params=self.esg_model.parameters(),
                                         lr=learning_rate)
        # Instantiate the Model
        torch.manual_seed(42)

        for epoch in range(epochs):
            self.epoch_count.append(epoch)

            self.esg_model.train()
            # Forward pass:
            y_pred = self.esg_model(self.train_data)

            print(y_pred.shape)
            print(self.train_labels.shape)

            # Calculate Loss
            loss = self.loss_fn(y_pred, self.train_labels)
            self.training_loss_list.append(loss.detach().numpy())

            # Optimizer
            self.optimizer.zero_grad()

            # Backpropagation
            loss.backward()

            # Perform Gradient descent
            self.optimizer.step()

            # Perform Predictions and capture test loss
            self.esg_model.eval()
            with torch.inference_mode():
                self.prediction_labels = self.esg_model(self.validation_data)
                validation_loss = self.loss_fn(
                    self.prediction_labels, self.validation_labels)
                self.validation_loss_list.append(
                    validation_loss.detach().numpy())
                print(f'Running epoch -- {epoch+1}  of {epochs}, training loss ={
                      loss},  validation loss ={validation_loss}')
                # print(self.esg_model.state_dict())


        plotter = Utils()
        if (plot_predictions):
            plotter.plot_predictions_graph(self.train_data, self.train_labels, self.validation_data,
                                           self.validation_labels, self.prediction_labels)
        if (plot_loss):
            plotter.plot_loss_graph(
                self.epoch_count, self.training_loss_list, self.validation_loss_list)


    def make_predictions(self,y_test):
        with torch.inference_mode():
            y_pred = self.esg_model(y_test)
        return y_pred


# X_train, y_train, X_validation, y_validation = get_data()
X_train, y_train, X_validation, y_validation = load_housing_data()

print(X_train.shape)
print(X_validation.shape)
print(y_train.shape)
print(y_validation.shape)

esg_data_trainer = ESGDataTrainer()
esg_data_trainer.train_and_validate_house_data(X_train, y_train, X_validation, y_validation,
                                    epochs=150, learning_rate=0.01, plot_predictions=False, plot_loss=True)
