import argparse
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from src.data.dataset_builder import WeiboSentimentDataset, load_data, split_dataset
from src.model.model_factory import ModelFactory
from src.training.evaluator import Evaluator
from src.utils.config_loader import load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to the config file.')
    parser.add_argument('--model_path', type=str, required=True, help='Path to the trained model.')
    args = parser.parse_args()

    config = load_config(args.config)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load data
    df = load_data(config['dataset']['path'])
    _, _, test_df = split_dataset(df)

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config['model']['model_name'])

    # Dataset and Dataloader
    test_dataset = WeiboSentimentDataset(test_df['text'].tolist(), test_df['label'].tolist(), tokenizer)
    test_loader = DataLoader(test_dataset, batch_size=config['training']['batch_size'])

    # Model
    model = ModelFactory.create_model(config['model'])
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.to(device)

    # Evaluator
    evaluator = Evaluator(model, device)
    metrics = evaluator.evaluate(test_loader)

    print("Evaluation Metrics:")
    for key, value in metrics.items():
        if key != 'confusion_matrix':
            print(f"  {key}: {value:.4f}")
    
    print("\nConfusion Matrix:")
    print(metrics['confusion_matrix'])
    # evaluator.plot_confusion_matrix(metrics['confusion_matrix'], class_names=['negative', 'positive'])

if __name__ == '__main__':
    main()
