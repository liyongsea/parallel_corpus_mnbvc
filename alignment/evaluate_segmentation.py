import argparse
from pathlib import Path
import json

import datasets
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from tqdm import tqdm

from text_segmenter import *
from batch_detector import GPTBatchDetector
from rule_based_detector import RuleBasedDetector


def main(detector_name, remove_long_file):
    # Instantiate the chosen detector
    if detector_name == 'DetectorA':
        detector = DetectorA(detector_name)
    elif detector_name == 'PunctuationAndCapitalLetterDetector':
        detector = PunctuationAndCapitalLetterDetector(detector_name)
    elif detector_name == 'RuleBasedDetector':
        detector = RuleBasedDetector(detector_name)
    elif detector_name == 'GptOfflineDetector':
        detector = OfflineDetector(detector_name, "bot-yaya/EN_PARAGRAPH_GPT_JOINED")
    elif detector_name == 'GptBatchDetector':
        detector = GPTBatchDetector('gpt-remote', "./cache_dir_maxtoken_500", token_limit=500)
    else:
        raise ValueError(f"Unknown detector name: {detector_name}")

    # Load the validation data from hf
    validation_data = datasets.load_dataset("bot-yaya/human_joined_en_paragraph", split="train", ignore_verifications=True)

    if remove_long_file:
        FILE_WORD_TH = 20000
        for record in tqdm(validation_data):
            raw_text = record['raw_text']
            if len(raw_text.split(' ')) > FILE_WORD_TH:
                print(f"remove {record['record']}, word count: {len(raw_text.split(' '))}")
        validation_data.filter(lambda x: len(x['raw_text'].split(' ')) <= FILE_WORD_TH)

    # Initialize DataFrame to store TP, FN, FP, TN
    results_df = pd.DataFrame(columns=['TP', 'FN', 'FP', 'TN'])

    # Initialize the lists to collect all predictions and ground truth labels
    all_predictions, all_ground_truth = [], []

    # Iterate over the validation data
    for record in tqdm(validation_data):

        raw_text = record['raw_text']
        ground_truth = record['is_hard_linebreak']
        record_id = record['record'] # fill with empty string '' if there is not exists such a record id
        if record_id in {"515053"}:
            continue
        # Initialize and process the text with a TextSegmenter
        segmenter = TextSegmenter(raw_text)
        segmenter.split_by_linebreak()

        # Get predictions for current record
        predicted = detector.detect(segmenter.lines, record_id=record_id) # record_id for gpt cache 

        while len(ground_truth) >= len(segmenter.lines): # temporary fix for the bug in the validation dataset
            ground_truth.pop()
        while len(predicted) >= len(segmenter.lines):
            predicted.pop()

        # Compute confusion matrix for the current record
        tn, fp, fn, tp = confusion_matrix(ground_truth, predicted).ravel()

        # Add result to the DataFrame
        results_df = results_df.append({'TP': tp, 'FN': fn, 'FP': fp, 'TN': tn, 'record_id': record_id}, ignore_index=True)

        # Collect the ground truth labels and predictions
        all_ground_truth.extend(ground_truth)
        all_predictions.extend(predicted)

        tmp_dir = Path("./tmp")
        tmp_dir.mkdir(exist_ok=True)
        eval_data = {
            "raw_text": raw_text,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "record_id": record_id,
        }
        with open(tmp_dir / f"{record_id}.json", "w") as f:
            json.dump(eval_data, f)

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
    parser.add_argument('--remove_long_file', type=bool, default=False, help='Remove long file, typically 515053')
    parser.add_argument('--detector_config', type=str, default=None, help='json file for detector config')

    args = parser.parse_args()
    detector_config = json.loads(parser.detector_config) if parser.detector_config else {}

    main(args.detector_name, args.remove_long_file)
