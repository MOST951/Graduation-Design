import pytest
import pandas as pd
from src.data.dataset_builder import load_data, split_dataset

@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        'text': ['I love this!', 'I hate this!', 'It is okay.', 'Another positive.', 'Another negative.'],
        'label': [1, 0, 0, 1, 0]
    })

def test_load_data(tmp_path):
    # Test loading from CSV
    csv_path = tmp_path / "test.csv"
    sample_dataframe().to_csv(csv_path, index=False)
    df = load_data(str(csv_path))
    assert not df.empty
    assert len(df) == 5

def test_split_dataset(sample_dataframe):
    train_df, val_df, test_df = split_dataset(sample_dataframe, test_size=0.2)
    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0
