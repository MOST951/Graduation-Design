import torch
import onnxruntime
import numpy as np
from typing import List, Union
import shap

class Predictor:
    """Makes predictions using a trained model."""

    def __init__(self, model_path: str, tokenizer: any, device: str = 'cpu', onnx: bool = False):
        self.tokenizer = tokenizer
        self.device = device
        self.onnx = onnx

        if self.onnx:
            self.session = onnxruntime.InferenceSession(model_path)
        else:
            self.model = torch.load(model_path, map_location=device)
            self.model.eval()

    def predict(self, text: str) -> int:
        """Predict sentiment for a single text."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        
        if self.onnx:
            onnx_inputs = {k: v.cpu().numpy() for k, v in inputs.items()}
            logits = self.session.run(None, onnx_inputs)[0]
            pred = np.argmax(logits, axis=1)[0]
        else:
            with torch.no_grad():
                outputs = self.model(**inputs)
                pred = torch.argmax(outputs['logits'], dim=1).item()
        return pred

    def predict_batch(self, texts: List[str]) -> List[int]:
        """Predict sentiment for a batch of texts."""
        return [self.predict(text) for text in texts]

    def explain_prediction(self, text: str):
        """Explain a prediction using SHAP."""
        def f(x):
            inputs = self.tokenizer(x.tolist(), return_tensors="pt", padding=True, truncation=True).to(self.device)
            with torch.no_grad():
                logits = self.model(**inputs)['logits']
            return torch.softmax(logits, dim=-1).cpu().numpy()

        explainer = shap.Explainer(f, self.tokenizer)
        shap_values = explainer([text])
        shap.plots.text(shap_values)
