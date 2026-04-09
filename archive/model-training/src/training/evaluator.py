import torch
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any

class Evaluator:
    """Handles model evaluation and metrics calculation."""

    def __init__(self, model, device):
        self.model = model
        self.device = device

    def evaluate(self, data_loader: DataLoader) -> Dict[str, Any]:
        """Evaluate the model on a given dataset."""
        self.model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)

                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                preds = torch.argmax(outputs['logits'], dim=1)

                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        return self.calculate_metrics(all_labels, all_preds)

    def calculate_metrics(self, labels: np.ndarray, preds: np.ndarray) -> Dict[str, Any]:
        """Calculate various evaluation metrics."""
        accuracy = accuracy_score(labels, preds)
        precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'confusion_matrix': confusion_matrix(labels, preds)
        }

    def plot_confusion_matrix(self, cm: np.ndarray, class_names: List[str]):
        """Plot the confusion matrix."""
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')
        plt.show()
