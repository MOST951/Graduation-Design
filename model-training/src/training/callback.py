import torch
from torch.utils.tensorboard import SummaryWriter
import numpy as np
from typing import Dict

class Callback:
    """Base class for callbacks."""
    def on_epoch_end(self, epoch: int, logs: Dict):
        pass

class EarlyStopping(Callback):
    """Stop training when a monitored metric has stopped improving."""
    def __init__(self, monitor: str = 'val_loss', patience: int = 3, min_delta: float = 0):
        self.monitor = monitor
        self.patience = patience
        self.min_delta = min_delta
        self.wait = 0
        self.best_score = np.inf
        self.stop_training = False

    def on_epoch_end(self, epoch: int, logs: Dict):
        score = logs.get(self.monitor)
        if score is None:
            return

        if score < self.best_score - self.min_delta:
            self.best_score = score
            self.wait = 0
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.stop_training = True

class ModelCheckpoint(Callback):
    """Save the model after every epoch."""
    def __init__(self, filepath: str, monitor: str = 'val_loss', model = None):
        self.filepath = filepath
        self.monitor = monitor
        self.model = model
        self.best_score = np.inf

    def on_epoch_end(self, epoch: int, logs: Dict):
        score = logs.get(self.monitor)
        if score is None:
            return

        if score < self.best_score:
            self.best_score = score
            print(f"Saving model with {self.monitor} of {score:.4f}")
            torch.save(self.model.state_dict(), self.filepath)

class TensorBoardCallback(Callback):
    """Log metrics to TensorBoard."""
    def __init__(self, log_dir: str):
        self.writer = SummaryWriter(log_dir)

    def on_epoch_end(self, epoch: int, logs: Dict):
        for key, value in logs.items():
            self.writer.add_scalar(key, value, epoch)

    def __del__(self):
        self.writer.close()
