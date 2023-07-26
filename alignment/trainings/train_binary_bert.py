import argparse

import numpy as np
import datasets
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    TrainingArguments,
    Trainer
)
import evaluate


def load_dataset():
    """
    Load the dataset to be used in training.
    """
    return datasets.load_dataset('liyongsea/un_linebreak-5000')


def load_model():
    """
    Load the model to be used in training.
    """
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-cased')
    model = DistilBertForSequenceClassification.from_pretrained(
        'distilbert-base-cased', num_labels=2)
    return tokenizer, model


def compute_metrics(eval_pred):
    """
    Compute the evaluation metric.
    """
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    metric = evaluate.load("accuracy")
    return metric.compute(predictions=predictions, references=labels)



def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Train a model with Hugging Face Transformers")
    parser.add_argument("--output_dir", type=str, default="trainer_shuffle", 
                        help="Directory to save the trained model and associated files")
    args = parser.parse_args()

    # Load the dataset
    pair_ds = load_dataset()

    # Load the tokenizer and model
    tokenizer, model = load_model()


    def tokenize_function(examples):
        """
        Apply tokenization to the dataset.
        """
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=64)


    # Tokenize the dataset
    tokenized_datasets = pair_ds.map(tokenize_function, batched=True)

    # Shuffle and select subsets of the dataset for training and evaluation
    small_train_dataset = tokenized_datasets["train"].shuffle(42)
    small_eval_dataset = tokenized_datasets["test"].shuffle(42).select(range(2000))

    # Define the training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir, evaluation_strategy="steps", num_train_epochs=2,
        save_strategy="steps", weight_decay=0.01, learning_rate=2e-5,
        eval_steps=3000, save_steps=6000,
    )

    # Initialize the Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=small_train_dataset,
        eval_dataset=small_eval_dataset,
        compute_metrics=compute_metrics,
    )

    # Train the model
    trainer.train()
  
if __name__ == "__main__":
    main()
