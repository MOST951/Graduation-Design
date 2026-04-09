import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from typing import Dict, Any, List

class Trainer:
    """Handles the model training and validation loops."""

    def __init__(self, model, optimizer, scheduler, device, callbacks: List[Any] = None):
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.callbacks = callbacks if callbacks else []

    def train_epoch(self, data_loader: DataLoader) -> float:
        """Perform one epoch of training."""
        self.model.train()
        total_loss = 0
        for batch in tqdm(data_loader, desc="Training"):
            self.optimizer.zero_grad()
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)

            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs['loss']
            loss.backward()
            self.optimizer.step()
            self.scheduler.step()

            total_loss += loss.item()

        return total_loss / len(data_loader)

    def validate(self, data_loader: DataLoader) -> float:
        """Perform validation on the validation set."""
        self.model.eval()
        total_loss = 0
        with torch.no_grad():
            for batch in tqdm(data_loader, desc="Validation"):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)

                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs['loss']
                total_loss += loss.item()

        return total_loss / len(data_loader)

    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int):
        """Main training loop."""
        for epoch in range(epochs):
            print(f"Epoch {epoch + 1}/{epochs}")
            train_loss = self.train_epoch(train_loader)
            val_loss = self.validate(val_loader)

            print(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            for callback in self.callbacks:
                callback.on_epoch_end(epoch=epoch, logs={'train_loss': train_loss, 'val_loss': val_loss})
                if getattr(callback, 'stop_training', False):
                    print("Early stopping triggered.")
                    return

    def save_checkpoint(self, path: str):
        """Save model checkpoint."""
        torch.save(self.model.state_dict(), path)
