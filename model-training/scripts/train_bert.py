import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import logging
import os
import random
import re
from torch.utils.data import Dataset, DataLoader, random_split, RandomSampler, SequentialSampler
from torch.utils.tensorboard import SummaryWriter
from transformers import BertTokenizer, BertForSequenceClassification, AdamW, get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from tqdm.auto import tqdm

# =============================================================================
# 1. Configuration & Setup
# =============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("../logs/train_bert.log"),
        logging.StreamHandler()
    ]
)

class TrainConfig:
    # --- Paths and Data --- #
    data_path = '../data/weibo_senti_100k.csv'  # Assumes CSV with 'review' and 'label' columns
    model_name = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'backend-python', 'models', 'chinese-bert-wwm-ext'
    )
    output_dir = '../models/bert_sentiment_model'
    log_dir = '../logs/bert_sentiment_runs'

    # --- Model & Tokenizer --- #
    num_labels = 2  # Example: 1 for Positive, 0 for Negative
    max_length = 128

    # --- Training Parameters --- #
    epochs = 4
    batch_size = 32
    learning_rate = 2e-5
    adam_epsilon = 1e-8
    warmup_steps = 100
    seed = 42
    
    # --- Hardware & Advanced Features --- #
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_gpu = torch.cuda.device_count()
    fp16 = True  # Set to True for mixed precision training
    
    # --- Early Stopping --- #
    early_stopping_patience = 2
    min_delta = 0.001

    # --- Data Splitting --- #
    train_split_ratio = 0.8
    val_split_ratio = 0.1
    # Test split is the remainder

CONFIG = TrainConfig()

# Set seed for reproducibility
def set_seed(seed_value):
    random.seed(seed_value)
    np.random.seed(seed_value)
    torch.manual_seed(seed_value)
    if CONFIG.n_gpu > 0:
        torch.cuda.manual_seed_all(seed_value)

set_seed(CONFIG.seed)

# =============================================================================
# 2. Data Preprocessing
# =============================================================================

class WeiboDataset(Dataset):
    """Custom PyTorch Dataset for Weibo sentiment data."""
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def clean_text(text):
    """Basic text cleaning: remove URLs, special characters, etc."""
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'@\w+', '', text)      # Remove mentions
    text = re.sub(r'#\S+#', '', text)     # Remove hashtags
    text = re.sub(r'\s+', ' ', text).strip() # Remove extra whitespace
    return text

def load_and_prepare_data(config, tokenizer):
    """Loads, cleans, and splits the dataset into DataLoaders."""
    logging.info(f"Loading data from {config.data_path}")
    df = pd.read_csv(config.data_path)
    df = df.dropna(subset=['review', 'label'])
    df['review'] = df['review'].apply(clean_text)
    
    # Data Augmentation placeholder: In a real scenario, you might use techniques
    # like back-translation or synonym replacement here.
    # df_augmented = augment_data(df)
    # df = pd.concat([df, df_augmented])

    dataset = WeiboDataset(
        texts=df.review.to_numpy(),
        labels=df.label.to_numpy(),
        tokenizer=tokenizer,
        max_len=config.max_length
    )

    train_size = int(config.train_split_ratio * len(dataset))
    val_size = int(config.val_split_ratio * len(dataset))
    test_size = len(dataset) - train_size - val_size
    
    train_dataset, val_dataset, test_dataset = random_split(dataset, [train_size, val_size, test_size])

    train_dataloader = DataLoader(train_dataset, sampler=RandomSampler(train_dataset), batch_size=config.batch_size)
    val_dataloader = DataLoader(val_dataset, sampler=SequentialSampler(val_dataset), batch_size=config.batch_size)
    test_dataloader = DataLoader(test_dataset, sampler=SequentialSampler(test_dataset), batch_size=config.batch_size)
    
    logging.info(f"Data loaded: {len(train_dataset)} train, {len(val_dataset)} val, {len(test_dataset)} test samples.")
    return train_dataloader, val_dataloader, test_dataloader

# =============================================================================
# 3. Model & Training Components
# =============================================================================

def build_model(config):
    """Builds the BERT model, tokenizer, and optimizer."""
    logging.info(f"Loading pre-trained model: {config.model_name}")
    tokenizer = BertTokenizer.from_pretrained(config.model_name)
    model = BertForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=config.num_labels,
        output_attentions=False,
        output_hidden_states=False,
    )
    model.to(config.device)
    
    if config.n_gpu > 1:
        model = torch.nn.DataParallel(model) # For multi-GPU training

    optimizer = AdamW(model.parameters(), lr=config.learning_rate, eps=config.adam_epsilon)
    return model, tokenizer, optimizer

class EarlyStopping:
    """Early stops the training if validation loss doesn't improve after a given patience."""
    def __init__(self, patience=7, min_delta=0, checkpoint_path='checkpoint.pt'):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = np.inf
        self.checkpoint_path = checkpoint_path

    def __call__(self, val_loss, model):
        if self.best_loss - val_loss > self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            logging.info(f"Validation loss decreased. Saving model to {self.checkpoint_path}")
            torch.save(model.state_dict(), self.checkpoint_path)
        else:
            self.counter += 1
            if self.counter >= self.patience:
                logging.info("Early stopping triggered.")
                return True
        return False

# =============================================================================
# 4. Training & Evaluation Loops
# =============================================================================

def train_epoch(model, data_loader, optimizer, device, scheduler, scaler, n_examples):
    model.train()
    losses = []
    correct_predictions = 0

    for batch in tqdm(data_loader, desc="Training"):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        optimizer.zero_grad()
        
        with torch.cuda.amp.autocast(enabled=CONFIG.fp16):
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss = outputs.loss
            logits = outputs.logits

        _, preds = torch.max(logits, dim=1)
        correct_predictions += torch.sum(preds == labels)
        losses.append(loss.item())

        if CONFIG.fp16:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
            
        scheduler.step()

    return correct_predictions.double() / n_examples, np.mean(losses)

def eval_model(model, data_loader, device, n_examples):
    model.eval()
    losses = []
    correct_predictions = 0

    with torch.no_grad():
        for batch in tqdm(data_loader, desc="Evaluating"):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            with torch.cuda.amp.autocast(enabled=CONFIG.fp16):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
            
            _, preds = torch.max(outputs.logits, dim=1)
            correct_predictions += torch.sum(preds == labels)
            losses.append(outputs.loss.item())

    return correct_predictions.double() / n_examples, np.mean(losses)

# =============================================================================
# 5. Main Execution
# =============================================================================

def main():
    """Main function to run the training and evaluation pipeline."""
    # --- Setup ---
    if not os.path.exists(CONFIG.output_dir):
        os.makedirs(CONFIG.output_dir)
    if not os.path.exists(CONFIG.log_dir):
        os.makedirs(CONFIG.log_dir)

    writer = SummaryWriter(CONFIG.log_dir)
    model, tokenizer, optimizer = build_model(CONFIG)
    train_loader, val_loader, test_loader = load_and_prepare_data(CONFIG, tokenizer)
    
    total_steps = len(train_loader) * CONFIG.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=CONFIG.warmup_steps, num_training_steps=total_steps
    )
    
    scaler = torch.cuda.amp.GradScaler(enabled=CONFIG.fp16)
    early_stopper = EarlyStopping(
        patience=CONFIG.early_stopping_patience, 
        min_delta=CONFIG.min_delta,
        checkpoint_path=os.path.join(CONFIG.output_dir, 'best_model.pt')
    )

    logging.info("Starting training...")
    # --- Training Loop ---
    for epoch in range(CONFIG.epochs):
        logging.info(f'Epoch {epoch + 1}/{CONFIG.epochs}')
        
        train_acc, train_loss = train_epoch(
            model, train_loader, optimizer, CONFIG.device, scheduler, scaler, len(train_loader.dataset)
        )
        logging.info(f'Train loss {train_loss:.4f}, accuracy {train_acc:.4f}')
        writer.add_scalar('Loss/train', train_loss, epoch)
        writer.add_scalar('Accuracy/train', train_acc, epoch)

        val_acc, val_loss = eval_model(
            model, val_loader, CONFIG.device, len(val_loader.dataset)
        )
        logging.info(f'Validation loss {val_loss:.4f}, accuracy {val_acc:.4f}')
        writer.add_scalar('Loss/val', val_loss, epoch)
        writer.add_scalar('Accuracy/val', val_acc, epoch)

        if early_stopper(val_loss, model):
            break

    # --- Final Evaluation ---
    logging.info("Loading best model for final evaluation on test set.")
    model.load_state_dict(torch.load(os.path.join(CONFIG.output_dir, 'best_model.pt')))
    test_acc, _ = eval_model(model, test_loader, CONFIG.device, len(test_loader.dataset))
    logging.info(f'Test accuracy: {test_acc:.4f}')
    writer.add_hparams(
        {'lr': CONFIG.learning_rate, 'batch_size': CONFIG.batch_size},
        {'test_accuracy': test_acc}
    )

    # --- Save Final Model & Tokenizer ---
    logging.info(f"Saving final model and tokenizer to {CONFIG.output_dir}")
    model_to_save = model.module if hasattr(model, 'module') else model
    model_to_save.save_pretrained(CONFIG.output_dir)
    tokenizer.save_pretrained(CONFIG.output_dir)

    # --- Export to ONNX (Optional) ---
    export_to_onnx(model_to_save, tokenizer, CONFIG)

    writer.close()
    logging.info("Training complete.")

def export_to_onnx(model, tokenizer, config):
    """Exports the model to ONNX format for deployment."""
    logging.info("Exporting model to ONNX...")
    model.eval()
    # Create a dummy input matching the model's expected input shape
    dummy_input_text = "This is a sample text for ONNX export."
    inputs = tokenizer(dummy_input_text, return_tensors="pt", max_length=config.max_length, padding='max_length', truncation=True)
    dummy_input_ids = inputs['input_ids'].to(config.device)
    dummy_attention_mask = inputs['attention_mask'].to(config.device)
    
    onnx_path = os.path.join(config.output_dir, "model.onnx")

    try:
        torch.onnx.export(
            model,
            (dummy_input_ids, dummy_attention_mask),
            onnx_path,
            input_names=['input_ids', 'attention_mask'],
            output_names=['logits'],
            dynamic_axes={'input_ids': {0: 'batch_size'}, 'attention_mask': {0: 'batch_size'}, 'logits': {0: 'batch_size'}},
            opset_version=11,
            export_params=True
        )
        logging.info(f"Model successfully exported to {onnx_path}")
    except Exception as e:
        logging.error(f"Failed to export to ONNX: {e}")

if __name__ == '__main__':
    # --- Advanced Feature Placeholders ---
    # Hyperparameter Search: Use libraries like Optuna or Ray Tune to wrap the main() function.
    # Knowledge Distillation: Requires a smaller 'student' model and a modified loss function.
    # Model Pruning/Quantization: Use torch.quantization or other libraries after training.
    # Distributed Training: For multi-node training, switch from DataParallel to DistributedDataParallel.
    main()
