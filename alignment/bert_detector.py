import torch
from transformers import BertTokenizer
import torch.nn as nn
import numpy as np

from alignment.text_segmenter import HardLineBreakDetector


device = torch.device('cpu')

class TextClassifier(nn.Module):

    def __init__(self, hidden_size, num_layers, bidirectional, dropout):

        super(TextClassifier, self).__init__()
        self.embedding = nn.Embedding(28996, hidden_size)
        self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers=num_layers, bidirectional=bidirectional, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        if bidirectional:
            self.fc = nn.Linear(2 * hidden_size, 1)
        else:
            self.fc = nn.Linear(hidden_size, 1)

    def forward(self, input_ids):
        embedded = self.embedding(input_ids)
        _, (hidden_state, _) = self.lstm(embedded)

        if self.lstm.bidirectional:
            hidden = self.dropout(torch.cat((hidden_state[-2,:,:], hidden_state[-1,:,:]), dim = 1))
        else:
            hidden = self.dropout(hidden_state[-1,:,:])

        output = self.fc(hidden)
        return output.squeeze()


class HfClassifier:

    def __init__(self, model):
        self.model = model

    def __call__(self, inputs):
        return self.model(inputs).logits.squeeze()[1]
    
    def eval(self):
        self.model.eval()


class BertLineBreakDetector(HardLineBreakDetector):

    def __init__(self, name, model=None, tokenizer=None):
        super().__init__(name)
        self.model = model
        self.tokenizer = tokenizer

    @classmethod
    def from_file(cls, name, model_path, tokenizer_name):
        model = TextClassifier(hidden_size=256, num_layers=1, bidirectional=True, dropout=0.5)
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()

        tokenizer = BertTokenizer.from_pretrained(tokenizer_name, local_files_only=True)

        return cls(name, model, tokenizer)

    def detect(self, lines, threshold=0.5, **kwargs):
        # Ensure model is in eval mode
        self.model.eval()

        predictions = []

        for i in range(len(lines) - 1):
            # Concatenate consecutive lines with '\n'
            text = lines[i] + '\n' + lines[i+1]
    
            # Tokenize the text
            inputs = self.tokenizer(text, truncation=True, padding=True, return_tensors='pt')

            # Move input to appropriate device
            inputs = inputs.to(device)
    
            # Predict
            with torch.no_grad():
                logits = self.model(inputs['input_ids'])

            # Apply sigmoid function for binary classification problem
            probs = torch.sigmoid(logits)

            # Determine if hard or soft break based on threshold
            is_hard_break = probs.item() > threshold
            
            # Append to predictions
            predictions.append(is_hard_break)

        return predictions  

