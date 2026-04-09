import torch

class ModelConverter:
    """Converts models to different formats for inference."""

    @staticmethod
    def to_onnx(model, dummy_input, onnx_path: str):
        """Convert a PyTorch model to ONNX format."""
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input_ids', 'attention_mask'],
            output_names=['output'],
            dynamic_axes={
                'input_ids': {0: 'batch_size', 1: 'sequence'},
                'attention_mask': {0: 'batch_size', 1: 'sequence'},
                'output': {0: 'batch_size'}
            }
        )

    @staticmethod
    def to_torchscript(model, torchscript_path: str):
        """Convert a PyTorch model to TorchScript format."""
        scripted_model = torch.jit.script(model)
        scripted_model.save(torchscript_path)

    # to_tflite would require a TensorFlow model, so it's omitted for this PyTorch-focused example.
