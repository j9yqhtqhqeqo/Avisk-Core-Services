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
    # X_Scaled =X

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
        plt.plot(epoch_count, validation_loss, label='Validation Loss')
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.title('Training vs. Validation Loss')
        plt.legend()
        plt.show()


class ESGDataTrainer:

    def __init__(self):
        self.epoch_count = []
        self.training_loss_list = []
        self.training_error_list =[]
        self.validation_loss_list = []
        self.validation_error_list = []
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

    def train_and_validate_house_data(self, train_data, train_labels, validation_data, validation_labels, learning_rate=0.01, epochs=10, batch_size=10, plot_predictions=False, plot_loss=True):

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

        train_dataset = TensorDataset(train_data,train_labels)
        train_data_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True)

        validation_dataset = TensorDataset(validation_data,validation_labels)
        validation_dataloader = DataLoader(
            validation_dataset, batch_size=batch_size)

        for epoch in range(epochs):
            self.epoch_count.append(epoch)
            self.esg_model.train()
            total_training_loss = 0.00
            total_training_error = 0.00

            for batch_data, batch_labels in train_data_loader:
                # Forward pass:
                y_pred = self.esg_model(batch_data)

                # Calculate Loss
                loss = self.loss_fn(y_pred, batch_labels)

                total_training_loss += loss.item()* len(batch_labels)
                training_error = torch.abs(y_pred-batch_labels).mean().item()
                total_training_error += training_error*len(batch_labels)

                # Optimizer
                self.optimizer.zero_grad()

                # Backpropagation
                loss.backward()

                # Perform Gradient descent
                self.optimizer.step()

            avg_training_loss = total_training_loss/len(train_data_loader.dataset)
            avg_training_error = total_training_error / len(train_data_loader.dataset)

            self.training_loss_list.append(avg_training_loss)
            self.training_error_list.append(avg_training_error)

            total_training_loss = 0.0
            total_training_error = 0.0

            # Perform Predictions and capture test loss

            total_validation_loss = 0.00
            total_validation_error = 0.00
            self.esg_model.eval()
            with torch.inference_mode():

                for batch_data, batch_labels in validation_dataloader:
                    prediction_labels = self.esg_model(batch_data)
                    
                    validation_loss = self.loss_fn(
                        prediction_labels, batch_labels)
                    total_validation_loss += validation_loss.item() * len(batch_labels)

                    validation_error = torch.abs(
                        prediction_labels-batch_labels).mean().item()
                    total_validation_error += validation_error*len(batch_labels)
                 
                avg_validation_loss = total_validation_loss /len(validation_dataloader.dataset)
                avg_validation_error = total_validation_error / \
                    len(validation_dataloader.dataset)
                self.validation_loss_list.append(avg_validation_loss)
                self.validation_error_list.append(avg_validation_error)
                total_validation_loss = 0.00
                total_validation_error =0.00


            # print(
            #     f"Epoch {epoch + 1}/{epochs}, "
            #     f"Training Loss: {avg_training_loss:.4f}, Training Error: {
            #         avg_training_error:.4f}, "
            #     f"Validation Loss: {avg_validation_loss:.4f}, Validation Error: {
            #         avg_validation_error:.4f}" )
            
        plotter = Utils()
        if (plot_predictions):
            plotter.plot_predictions_graph(self.train_data, self.train_labels, self.validation_data,
                                           self.validation_labels, self.prediction_labels)
        if (plot_loss):
            plotter.plot_loss_graph(
                self.epoch_count, self.training_loss_list, self.validation_loss_list)

        Test_tensor1 = torch.Tensor([0.2498, 0, 21.89, 0, 0.624, 5.857, 0, 1.6686, 4, 437, 21.2, 392.04, 21.32
                                    ])

        predicted_value = self.make_predictions(Test_tensor1)
        print(predicted_value.item())

        Test_tensor2 = torch.Tensor([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                            ])

        predicted_value = self.make_predictions(Test_tensor2)
        print(predicted_value.item())
    

    def train_and_validate_house_data_nobatch(self, train_data, train_labels, validation_data, validation_labels, learning_rate=0.01, epochs=10, plot_predictions=False, plot_loss=True):
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

            # print(y_pred)
            # print(self.train_labels)

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
                    print('Predicated Value is :' + str(y_pred))
                return y_pred


# X_train, y_train, X_validation, y_validation = get_data()
X_train, y_train, X_validation, y_validation = load_housing_data()

# print(X_train)
# print(y_train)
# print(X_validation)
# print(y_validation)

# esg_data_trainer = ESGDataTrainer()
# esg_data_trainer.train_and_validate_house_data(X_train, y_train, X_validation, y_validation,
#                                     epochs=1000,batch_size=13, learning_rate=0.01, plot_predictions=False, plot_loss=True)

esg_data_trainer = ESGDataTrainer()
esg_data_trainer.train_and_validate_house_data_nobatch(X_train, y_train, X_validation, y_validation,
                                               epochs=1000, learning_rate=0.005, plot_predictions=False, plot_loss=True)
Test_tensor = torch.Tensor([0.2498, 0, 21.89, 0, 0.624, 5.857, 0, 1.6686, 4, 437, 21.2, 392.04, 21.32
                            ])
predicted_value = esg_data_trainer.make_predictions(Test_tensor)
print(predicted_value.item())

# Test_tensor = torch.Tensor([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
#                             ])
# predicted_value = esg_data_trainer.make_predictions(Test_tensor)
# print(predicted_value.item())

# Test_tensor = torch.Tensor([0.22489, 12.5, 7.87, 0, 0.524, 6.377, 94.3, 6.3467, 5, 311, 15.2, 392.52, 20.45
#                             ])
# predicted_value = esg_data_trainer.make_predictions(Test_tensor)

# print(predicted_value.item())
