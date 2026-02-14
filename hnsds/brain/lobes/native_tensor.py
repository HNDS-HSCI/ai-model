import math
import random

class NativeTensor:
    """
    INVENTION: A Pure Python Linear Algebra Engine.
    
    This replaces external libraries like NumPy/PyTorch.
    It provides the mathematical foundation for the Neural Brain.
    """
    
    @staticmethod
    def zeros(rows, cols):
        return [[0.0 for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def random(rows, cols):
        # Xavier Initializationish
        limit = math.sqrt(6 / (rows + cols))
        return [[random.uniform(-limit, limit) for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def matmul(A, B):
        """Matrix Multiplication (Dot Product)"""
        rowsA = len(A)
        colsA = len(A[0])
        rowsB = len(B)
        colsB = len(B[0])

        if colsA != rowsB:
            raise ValueError(f"Shape mismatch: {colsA} vs {rowsB}")

        C = NativeTensor.zeros(rowsA, colsB)
        for i in range(rowsA):
            for j in range(colsB):
                sum_val = 0
                for k in range(colsA):
                    sum_val += A[i][k] * B[k][j]
                C[i][j] = sum_val
        return C

    @staticmethod
    def add(A, B):
        """Element-wise Addition"""
        rows = len(A)
        cols = len(A[0])
        C = NativeTensor.zeros(rows, cols)
        for i in range(rows):
            for j in range(cols):
                C[i][j] = A[i][j] + B[i][j]
        return C

    @staticmethod
    def sub(A, B):
        """Element-wise Subtraction"""
        rows = len(A)
        cols = len(A[0])
        C = NativeTensor.zeros(rows, cols)
        for i in range(rows):
            for j in range(cols):
                C[i][j] = A[i][j] - B[i][j]
        return C

    @staticmethod
    def multiply_scalar(A, scalar):
        rows = len(A)
        cols = len(A[0])
        C = NativeTensor.zeros(rows, cols)
        for i in range(rows):
            for j in range(cols):
                C[i][j] = A[i][j] * scalar
        return C

    @staticmethod
    def transpose(A):
        rows = len(A)
        cols = len(A[0])
        C = NativeTensor.zeros(cols, rows)
        for i in range(rows):
            for j in range(cols):
                C[j][i] = A[i][j]
        return C

    @staticmethod
    def apply(A, func):
        """Apply a function element-wise"""
        rows = len(A)
        cols = len(A[0])
        C = NativeTensor.zeros(rows, cols)
        for i in range(rows):
            for j in range(cols):
                C[i][j] = func(A[i][j])
        return C

    # --- Activation Functions ---
    
    @staticmethod
    def sigmoid(x):
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    @staticmethod
    def sigmoid_derivative(x):
        s = NativeTensor.sigmoid(x)
        return s * (1 - s)

    @staticmethod
    def relu(x):
        return max(0.0, x)
    
    @staticmethod
    def relu_derivative(x):
        return 1.0 if x > 0 else 0.0
