from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
import numpy as np
from typing import Dict

def calculate_metrics(labels: np.ndarray, preds: np.ndarray, probs: np.ndarray = None) -> Dict[str, float]:
    """Calculate a comprehensive set of metrics."""
    accuracy = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
    }

    if probs is not None and len(np.unique(labels)) == 2:
        auc = roc_auc_score(labels, probs[:, 1])
        metrics['auc'] = auc

    return metrics
