import torch
import torch.nn as nn
import torch.nn.functional as F

class BiLSTMAttention(nn.Module):
    """BiLSTM with Attention for text classification."""

    def __init__(self, vocab_size: int, embedding_dim: int, hidden_dim: int, n_layers: int, 
                 dropout: float, num_labels: int, pretrained_embeddings: torch.Tensor = None):
        super().__init__()
        
        if pretrained_embeddings is not None:
            self.embedding = nn.Embedding.from_pretrained(pretrained_embeddings, freeze=False)
        else:
            self.embedding = nn.Embedding(vocab_size, embedding_dim)
            
        self.lstm = nn.LSTM(embedding_dim, 
                            hidden_dim, 
                            num_layers=n_layers, 
                            bidirectional=True, 
                            dropout=dropout, 
                            batch_first=True)
        
        self.attention = nn.Linear(hidden_dim * 2, 1, bias=False)
        self.fc = nn.Linear(hidden_dim * 2, num_labels)
        self.dropout = nn.Dropout(dropout)

    def forward(self, text, text_lengths):
        embedded = self.dropout(self.embedding(text))
        
        # Pack sequence
        packed_embedded = nn.utils.rnn.pack_padded_sequence(embedded, text_lengths.to('cpu'), batch_first=True, enforce_sorted=False)
        packed_output, (hidden, cell) = self.lstm(packed_embedded)
        
        # Unpack sequence
        output, _ = nn.utils.rnn.pad_packed_sequence(packed_output, batch_first=True)
        
        # Attention mechanism
        attn_weights = F.softmax(self.attention(output).squeeze(-1), dim=1)
        attn_output = torch.bmm(attn_weights.unsqueeze(1), output).squeeze(1)
        
        # Final linear layer
        logits = self.fc(attn_output)
        return logits
