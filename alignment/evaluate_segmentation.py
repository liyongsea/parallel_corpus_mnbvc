import argparse
from pathlib import Path
import json

import datasets
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from tqdm import tqdm
import wandb

from .text_segmenter import *
from .batch_detector import GPTBatchDetector
from .batch_sequential_detector import GPTBatchSequentialDetector
from .rule_based_detector import RuleBasedDetector
from . import utils


def _get_folder_from_config(config):
    if 'cache_dir' in config:
        cache_dir = config['cache_dir']
    else:
        if config:
            # join all params in config to create the cache dir
            # sort the key to make sure the cache dir is the same
            cache_dir = 'cache_dir_' + '_'.join([f"{k}_{v}" for k, v in sorted(config.items())])
        else:
            cache_dir = 'cache_dir'
    return cache_dir


def main(detector_name, remove_long_file, detector_config):
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
        print("using confing", detector_config)
        token_limit = detector_config.get('token_limit', 1400)
        cache_dir = _get_folder_from_config(detector_config)
        detector = GPTBatchDetector('gpt-remote', cache_dir, token_limit=token_limit)
    elif detector_name == "GptBatchSequentialDetector":
        print("using confing", detector_config)
        token_limit = detector_config.get('token_limit', 1400)
        cache_dir = 'batch_sequential_' + _get_folder_from_config(detector_config)
        detector = GPTBatchSequentialDetector('gpt-remote', cache_dir, token_limit=token_limit, use_proxy=True)
    else:
        raise ValueError(f"Unknown detector name: {detector_name}")

    # Load the validation data from hf
        

    # Create a new wandb Artifact
    run = wandb.run  # get the current run
    artifact = wandb.Artifact(
        name="evaluation_artifacts",
        type="dataset",
        description="JSON files containing raw text, ground truth, predictions and record_id",
        metadata=dict(detector_name=detector_name))  # You can include more metadata as needed


    # Load the validation data from hf
    validation_data = datasets.load_dataset("bot-yaya/human_joined_en_paragraph_19", split="train", ignore_verifications=True)

    if remove_long_file:
        FILE_WORD_TH = 20000
        for record in validation_data:
            raw_text = record['raw_text']
            if len(raw_text.split(' ')) > FILE_WORD_TH:
                print(f"remove {record['record']}, word count: {len(raw_text.split(' '))}")
        validation_data = validation_data.filter(lambda x: len(x['raw_text'].split(' ')) <= FILE_WORD_TH)

    # Initialize DataFrame to store TP, FN, FP, TN
    results_df = pd.DataFrame(columns=['TP', 'FN', 'FP', 'TN', 'record_id','accuracy'])

    # Initialize the lists to collect all predictions and ground truth labels
    all_predictions, all_ground_truth = [], []

    # Iterate over the validation data
    for record in tqdm(validation_data):

        raw_text = record['raw_text']
        ground_truth = record['is_hard_linebreak']
        record_id = record['record']
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

        record_accuracy = (tp + tn) / (tp + tn + fp + fn)

    
        # Create results in a loop and Add this result to the DataFrame
        result_pd_row = pd.DataFrame({'TP': tp, 'FN': fn, 'FP': fp, 'TN': tn, 'accuracy': record_accuracy, 'record_id': record_id}, index=[0])
        results_df = pd.concat([results_df, result_pd_row], ignore_index=True)


        # Collect the ground truth labels and predictions
        all_ground_truth.extend(ground_truth)
        all_predictions.extend(predicted)

        eval_data = {
            "raw_text": raw_text,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "record_id": record_id,
        }

        # Add data to the artifact as a JSON file
        with artifact.new_file(f"{record_id}.json", mode="w") as f:
            json.dump(eval_data, f)

        html_content = utils.create_error_html_visual(raw_text, ground_truth, predicted)
        with artifact.new_file(f"{record_id}.html", mode="w") as f:
            f.write(html_content)
    
    run.log_artifact(artifact)

    # Print DataFrame
    print("Results DataFrame:")
    print(results_df)
    print()

    # Compute and print classification report
    classification_results = classification_report(all_ground_truth, all_predictions, output_dict=True)
    classification_results = pd.DataFrame(classification_results).transpose()
    print("Classification Report:")
    print(classification_results)

    # Log metrics to wandb
    wandb.log({
        "Result per record": wandb.Table(dataframe=results_df),
        "Classification Report": wandb.Table(dataframe=classification_results) # Convert classification report to DataFrame
    })



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate a hard line break detector.')
    parser.add_argument('detector_name', type=str, help='The name of the detector to evaluate (DetectorA or PunctuationAndCapitalLetterDetector)')
    parser.add_argument('--remove_long_file', type=bool, default=False, help='Remove long file, typically 515053')
    parser.add_argument('--detector_config', type=str, default=None, help='json file for detector config')
    parser.add_argument('--run_name', type=str, default=None, help='run name for wandb')

    args = parser.parse_args()
    detector_config = json.loads(args.detector_config) if args.detector_config else {}

    wandb.init(project="text_segmentation", name=args.run_name)
    main(args.detector_name, args.remove_long_file, detector_config)
    wandb.finish()
