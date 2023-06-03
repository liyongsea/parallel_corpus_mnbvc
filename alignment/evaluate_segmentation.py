import argparse

import datasets
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from tqdm import tqdm

from text_segmenter import *
from batch_detector import GPTBatchDetector


def main(detector_name):
    # Instantiate the chosen detector
    if detector_name == 'DetectorA':
        detector = DetectorA(detector_name)
    elif detector_name == 'PunctuationAndCapitalLetterDetector':
        detector = PunctuationAndCapitalLetterDetector(detector_name)
    elif detector_name == 'GptOfflineDetector':
        detector = OfflineDetector(detector_name, "bot-yaya/EN_PARAGRAPH_GPT_JOINED")
    elif detector_name == 'GptBatchDetector':
        detector = GPTBatchDetector('gpt-remote', "./cache_dir")
    else:
        raise ValueError(f"Unknown detector name: {detector_name}")

    # Load the validation data from hf
    validation_data = datasets.load_dataset("bot-yaya/EN_PARAGRAPH_HUMAN_JOINED", split="train")


    # Initialize DataFrame to store TP, FN, FP, TN
    results_df = pd.DataFrame(columns=['TP', 'FN', 'FP', 'TN'])

    # Initialize the lists to collect all predictions and ground truth labels
    all_predictions, all_ground_truth = [], []

    validation_data = validation_data.select(range(5))
    # Iterate over the validation data
    for record in tqdm(validation_data):

        raw_text = record['raw_text']
        ground_truth = record['is_hard_linebreak']
        record_id = record['record'] # fill with empty string '' if there is not exists such a record id


        # Initialize and process the text with a TextSegmenter
        segmenter = TextSegmenter(raw_text)
        segmenter.split_by_linebreak()

        # Get predictions for current record
        predicted = detector.detect(segmenter.lines, record_id=record_id) # record_id for gpt cache 

        # temporary fix for the bug in the validation dataset
        if len(ground_truth) == len(predicted) + 1:
            ground_truth = ground_truth[:-1]

        # Compute confusion matrix for the current record
        tn, fp, fn, tp = confusion_matrix(ground_truth, predicted).ravel()

        # Add result to the DataFrame
        results_df = results_df.append({'TP': tp, 'FN': fn, 'FP': fp, 'TN': tn}, ignore_index=True)

        # Collect the ground truth labels and predictions
        all_ground_truth.extend(ground_truth)
        all_predictions.extend(predicted)

    # Print DataFrame
    print("Results DataFrame:")
    print(results_df)
    print()

    # Compute and print classification report
    print("Classification Report:")
    print(classification_report(all_ground_truth, all_predictions))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate a hard line break detector.')
    parser.add_argument('detector_name', type=str, help='The name of the detector to evaluate (DetectorA or PunctuationAndCapitalLetterDetector)')

    args = parser.parse_args()

    main(args.detector_name)
