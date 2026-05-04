import os
import time
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spark.sentiment_analyzer import SentimentLexicon

LABEL_NAMES = ['negative', 'positive', 'neutral']
ID_TO_NAME = {0: 'negative', 1: 'positive', 2: 'neutral'}


def load_test_data():
    data_path = ROOT / 'data' / 'weibo_senti_100k.csv'
    df = pd.read_csv(data_path)
    df = df[['review', 'label']].dropna()
    df['label'] = df['label'].astype(int)
    _, test_df = train_test_split(
        df,
        test_size=0.1,
        stratify=df['label'],
        random_state=42,
    )
    return test_df.reset_index(drop=True)


def print_metrics(title, y_true, y_pred, elapsed_s, extra=None):
    labels = [0, 1, 2]
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average='macro', zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    avg_ms = elapsed_s * 1000 / len(y_true)
    print(f'===== {title} =====')
    print(f'Test size: {len(y_true)}')
    print(f'Overall Accuracy: {acc:.6f}')
    for idx, name in enumerate(LABEL_NAMES):
        print(f'{name}: Precision={p[idx]:.6f}, Recall={r[idx]:.6f}, F1={f1[idx]:.6f}, Support={int(support[idx])}')
    print(f'Macro Precision: {macro_p:.6f}')
    print(f'Macro Recall: {macro_r:.6f}')
    print(f'Macro F1: {macro_f1:.6f}')
    print('Confusion Matrix rows=true cols=pred [negative, positive, neutral]:')
    print(cm)
    print(f'Average inference speed: {avg_ms:.6f} ms/item')
    if extra:
        for k, v in extra.items():
            print(f'{k}: {v}')
    print()


def load_bert():
    model_dir = ROOT / 'models' / 'chinese-bert-wwm-ext'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir), local_files_only=True)
    model.to(device)
    model.eval()
    return tokenizer, model, device


def predict_bert(texts, tokenizer, model, device, batch_size=64, max_length=128):
    preds = []
    confs = []
    start = time.perf_counter()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt',
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            outputs = model(**enc)
            probs = torch.softmax(outputs.logits, dim=-1)
            conf, pred = torch.max(probs, dim=-1)
            preds.extend(pred.detach().cpu().numpy().tolist())
            confs.extend(conf.detach().cpu().numpy().tolist())
    if device.type == 'cuda':
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    return preds, confs, elapsed


def eval_lexicon(texts):
    preds = []
    confs = []
    high = []
    start = time.perf_counter()
    for text in texts:
        label, conf, high_confidence = SentimentLexicon.analyze_3class(str(text))
        preds.append(int(label))
        confs.append(float(conf))
        high.append(bool(high_confidence))
    elapsed = time.perf_counter() - start
    return preds, confs, high, elapsed


def eval_cascade(texts, y_true, tokenizer, model, device,
                  bert_fallback_threshold: float = 0.55):
    preds = []
    lex_direct_true = []
    bert_call_true = []
    low_conf_fallback_count = 0
    bert_time = 0.0
    start = time.perf_counter()
    for text, true_label in zip(texts, y_true):
        lex_label, lex_conf, high_confidence = SentimentLexicon.analyze_3class(str(text))
        lex_label = int(lex_label)
        if high_confidence:
            pred = lex_label
            lex_direct_true.append(int(pred == true_label))
        else:
            bpreds, bconfs, elapsed = predict_bert([str(text)], tokenizer, model, device, batch_size=1, max_length=128)
            bert_time += elapsed
            bert_pred = int(bpreds[0])
            bert_conf = float(bconfs[0])
            if bert_conf < bert_fallback_threshold and lex_label == 2:
                pred = 2
                low_conf_fallback_count += 1
            else:
                pred = bert_pred
            bert_call_true.append(int(pred == true_label))
        preds.append(pred)
    elapsed_total = time.perf_counter() - start
    extra = {
        'Lexicon direct count': len(lex_direct_true),
        'Lexicon direct ratio': f'{len(lex_direct_true) / len(texts):.6f}',
        'Lexicon direct accuracy': f'{(sum(lex_direct_true) / len(lex_direct_true)) if lex_direct_true else 0:.6f}',
        'BERT call count': len(bert_call_true),
        'BERT call ratio': f'{len(bert_call_true) / len(texts):.6f}',
        'BERT call path accuracy': f'{(sum(bert_call_true) / len(bert_call_true)) if bert_call_true else 0:.6f}',
        'BERT low-confidence neutral fallback count': low_conf_fallback_count,
        'bert_fallback_threshold': bert_fallback_threshold,
    }
    return preds, elapsed_total, extra


def main():
    test_df = load_test_data()
    texts = test_df['review'].astype(str).tolist()
    y_true = test_df['label'].astype(int).tolist()
    print('Dataset:', ROOT / 'data' / 'weibo_senti_100k.csv')
    print('Split: test_size=0.1, stratify=label, random_state=42')
    print('Label mapping: {0: negative, 1: positive, 2: neutral}')
    print('Model max_length=128')
    print('Torch CUDA available:', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('Torch CUDA device:', torch.cuda.get_device_name(0))
    print()

    tokenizer, model, device = load_bert()

    bert_preds, _, bert_elapsed = predict_bert(texts, tokenizer, model, device, batch_size=64, max_length=128)
    print_metrics('TEST 1 STANDARD MODE PURE BERT', y_true, bert_preds, bert_elapsed)

    lex_preds, _, _, lex_elapsed = eval_lexicon(texts)
    print_metrics('TEST 2 PURE LEXICON MODE', y_true, lex_preds, lex_elapsed)

    cascade_preds, cascade_elapsed, extra = eval_cascade(texts, y_true, tokenizer, model, device)
    print_metrics('TEST 3 FAST MODE THREE-STAGE CASCADE', y_true, cascade_preds, cascade_elapsed, extra=extra)


if __name__ == '__main__':
    main()
