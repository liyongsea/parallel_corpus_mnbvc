import json
import argparse
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from text_segmenter import *


def main(detector_name):
    # Instantiate the chosen detector
    if detector_name == 'DetectorA':
        detector = DetectorA(detector_name)
    elif detector_name == 'PunctuationAndCapitalLetterDetector':
        detector = PunctuationAndCapitalLetterDetector(detector_name)
    else:
        raise ValueError(f"Unknown detector name: {detector_name}")

    # Load the validation data from a JSONL file
    with open('validation_small.jsonl', 'r') as f:
        validation_data = [json.loads(line) for line in f]

    # Initialize DataFrame to store TP, FN, FP, TN
    results_df = pd.DataFrame(columns=['TP', 'FN', 'FP', 'TN'])

    # Initialize the lists to collect all predictions and ground truth labels
    all_predictions, all_ground_truth = [], []

    # Iterate over the validation data
    for record in validation_data:

        raw_text = record['raw_text']
        ground_truth = record['is_hard_linebreak']

        # Initialize and process the text with a TextSegmenter
        segmenter = TextSegmenter(raw_text)
        segmenter.split_by_linebreak()

        # Get predictions for current record
        predicted = detector.detect(segmenter.lines)

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
