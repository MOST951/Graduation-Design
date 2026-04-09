import argparse
import torch
from src.model.model_factory import ModelFactory
from src.inference.model_converter import ModelConverter
from src.utils.config_loader import load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to the model config file.')
    parser.add_argument('--model_path', type=str, required=True, help='Path to the trained PyTorch model.')
    parser.add_argument('--output_path', type=str, required=True, help='Path to save the exported model.')
    parser.add_argument('--format', type=str, choices=['onnx', 'torchscript'], required=True, help='Export format.')
    args = parser.parse_args()

    config = load_config(args.config)
    device = torch.device('cpu') # Exporting is typically done on CPU

    # Load model
    model = ModelFactory.create_model(config['model'])
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.to(device)
    model.eval()

    # Create dummy input for tracing
    dummy_input = {
        'input_ids': torch.randint(0, 1000, (1, 128), device=device),
        'attention_mask': torch.ones(1, 128, device=device)
    }

    # Convert model
    if args.format == 'onnx':
        ModelConverter.to_onnx(model, tuple(dummy_input.values()), args.output_path)
        print(f"Model exported to ONNX at {args.output_path}")
    elif args.format == 'torchscript':
        ModelConverter.to_torchscript(model, args.output_path)
        print(f"Model exported to TorchScript at {args.output_path}")

if __name__ == '__main__':
    main()
