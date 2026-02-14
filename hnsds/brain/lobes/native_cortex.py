from .native_tensor import NativeTensor
import random
import json
import os

class NativeCortex:
    """
    INVENTION: The Synaptic Neural Network.
    
    A pure Python implementation of a Multi-Layer Perceptron (MLP)
    with Backpropagation.
    """
    def __init__(self, input_size, hidden_size, output_size, learning_rate=0.1):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.learning_rate = learning_rate
        
        # Weights and Biases
        self.W1 = NativeTensor.random(input_size, hidden_size)
        self.B1 = NativeTensor.zeros(1, hidden_size)
        self.W2 = NativeTensor.random(hidden_size, output_size)
        self.B2 = NativeTensor.zeros(1, output_size)
        
        self.synaptic_path = "synaptic_weights.json"
        self.load_weights()

    def forward(self, input_vector):
        """
        Forward Pass: Think.
        Input -> Hidden Layer (Sigmoid) -> Output Layer (Sigmoid)
        """
        # Ensure input is a matrix [1, N]
        if not isinstance(input_vector[0], list):
            self.Z0 = [input_vector] 
        else:
            self.Z0 = input_vector

        # Layer 1
        self.A1 = NativeTensor.matmul(self.Z0, self.W1)
        self.A1 = NativeTensor.add(self.A1, self.B1)
        self.Z1 = NativeTensor.apply(self.A1, NativeTensor.sigmoid)
        
        # Layer 2
        self.A2 = NativeTensor.matmul(self.Z1, self.W2)
        self.A2 = NativeTensor.add(self.A2, self.B2)
        self.Z2 = NativeTensor.apply(self.A2, NativeTensor.sigmoid)
        
        return self.Z2[0] # Return flat list of probabilities

    def train(self, input_vector, target_vector):
        """
        Backward Pass: Learn.
        Backpropagation of Error using Gradient Descent.
        """
        # 1. Perform Forward Pass to get current state
        output = self.forward(input_vector)
        
        target_matrix = [target_vector]
        
        # 2. Calculate Output Error (MSE Derivative)
        # Error = Output - Target
        output_error = NativeTensor.sub(self.Z2, target_matrix)
        
        # 3. Calculate Gradients for Layer 2
        # dCost/dW2 = dCost/dZ2 * dZ2/dA2 * dA2/dW2
        # dZ2/dA2 = sigmoid_derivative(A2)
        d_A2 = NativeTensor.apply(self.A2, NativeTensor.sigmoid_derivative)
        delta_2 = NativeTensor.zeros(len(output_error), len(output_error[0]))
        
        # Element-wise multiply error * derivative
        for i in range(len(delta_2)):
            for j in range(len(delta_2[0])):
                delta_2[i][j] = output_error[i][j] * d_A2[i][j]

        # Gradients
        d_W2 = NativeTensor.matmul(NativeTensor.transpose(self.Z1), delta_2)
        d_B2 = delta_2
        
        # 4. Calculate Gradients for Layer 1
        # Propagate error back: error_l1 = delta_2 * W2.T
        error_l1 = NativeTensor.matmul(delta_2, NativeTensor.transpose(self.W2))
        d_A1 = NativeTensor.apply(self.A1, NativeTensor.sigmoid_derivative)
        
        delta_1 = NativeTensor.zeros(len(error_l1), len(error_l1[0]))
        for i in range(len(delta_1)):
            for j in range(len(delta_1[0])):
                delta_1[i][j] = error_l1[i][j] * d_A1[i][j]

        d_W1 = NativeTensor.matmul(NativeTensor.transpose(self.Z0), delta_1)
        d_B1 = delta_1
        
        # 5. Update Weights (Stochastic Gradient Descent)
        self.W2 = NativeTensor.sub(self.W2, NativeTensor.multiply_scalar(d_W2, self.learning_rate))
        self.B2 = NativeTensor.sub(self.B2, NativeTensor.multiply_scalar(d_B2, self.learning_rate))
        self.W1 = NativeTensor.sub(self.W1, NativeTensor.multiply_scalar(d_W1, self.learning_rate))
        self.B1 = NativeTensor.sub(self.B1, NativeTensor.multiply_scalar(d_B1, self.learning_rate))

        return sum(sum(row) for row in NativeTensor.apply(output_error, lambda x: 0.5*x**2)) # Total Loss

    def save_weights(self):
        data = {
            "W1": self.W1, "B1": self.B1,
            "W2": self.W2, "B2": self.B2
        }
        with open(self.synaptic_path, 'w') as f:
            json.dump(data, f)

    def load_weights(self):
        if os.path.exists(self.synaptic_path):
            try:
                with open(self.synaptic_path, 'r') as f:
                    data = json.load(f)
                    self.W1 = data["W1"]
                    self.B1 = data["B1"]
                    self.W2 = data["W2"]
                    self.B2 = data["B2"]
            except: pass
