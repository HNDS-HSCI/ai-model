import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv, global_mean_pool
from typing import Any

class GraphEncoder(nn.Module):
    """
    Graph Neural Network encoder.
    Converts entity graph to dense embedding.
    ~10M parameters maximum.
    """
    def __init__(self, input_dim=256, hidden_dim=512, output_dim=128, num_layers=4):
        super().__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        # Using 4 layers as per config/prompt
        self.convs = nn.ModuleList([GCNConv(hidden_dim, hidden_dim) for _ in range(num_layers - 2)])
        self.conv_out = GCNConv(hidden_dim, output_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)

    def forward(self, x, edge_index, batch):
        x = self.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        for conv in self.convs:
            x = self.relu(conv(x, edge_index))
        x = self.relu(self.conv_out(x, edge_index))
        return global_mean_pool(x, batch)
