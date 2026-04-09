import pandas as pd
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from typing import Tuple, List, Dict, Any

class WeiboSentimentDataset(Dataset):
    """Custom Dataset for Weibo Sentiment Analysis."""

    def __init__(self, texts: List[str], labels: List[int], tokenizer: Any):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        text = self.texts[idx]
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def load_data(data_path: str) -> pd.DataFrame:
    """Load data from various formats."""
    if data_path.endswith('.csv'):
        return pd.read_csv(data_path)
    elif data_path.endswith('.json'):
        return pd.read_json(data_path, lines=True)
    elif data_path.endswith('.tsv'):
        return pd.read_csv(data_path, sep='\t')
    else:
        raise ValueError(f"Unsupported data format for {data_path}")

def split_dataset(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split the dataset into training, validation, and test sets."""
    train_val_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state)
    train_df, val_df = train_test_split(train_val_df, test_size=test_size, random_state=random_state) # Split train_val further
    return train_df, val_df, test_df
