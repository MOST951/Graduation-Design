from fastapi import FastAPI
from pydantic import BaseModel
from .predictor import Predictor
from transformers import AutoTokenizer

app = FastAPI()

class SentimentRequest(BaseModel):
    text: str

# Load the model and tokenizer at startup
# In a real application, you would load a specific model version
model_path = "path/to/your/model.pt" # or .onnx
tokenizer_name = "bert-base-chinese"
predictor = Predictor(model_path, AutoTokenizer.from_pretrained(tokenizer_name))

@app.post("/predict/")
def predict_sentiment(request: SentimentRequest):
    """Endpoint to predict sentiment of a given text."""
    prediction = predictor.predict(request.text)
    return {"sentiment": int(prediction)}

@app.get("/")
def read_root():
    return {"message": "Weibo Sentiment Analysis API"}
