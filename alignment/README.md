# Softline vs Hardline Detection Performance Evaluation

This module evaluates the performance of a softline vs hardline detection method by comparing its predictions against human-annotated line breaks in a validation dataset. The task is to determine whether a line break in a given text is a hard linebreak (True) or a soft linebreak (False). Accurate detection of hard and soft linebreaks is crucial for various text processing applications, such as formatting, layout analysis, and language generation.

## Problem Description
A line break is a typographical feature that indicates the end of a line and the start of a new line in a text document. In some cases, line breaks represent a hard break, indicating a clear separation between two lines of text. In other cases, line breaks are soft breaks, used for formatting purposes and to improve the readability of the text. The goal of the softline vs hardline detection task is to distinguish between these two types of line breaks accurately.

## Usage
Please make sure you have done
```
pip install -r requirements.txt
```

Then login in wandb. This evaluatoin use wandb to track evaluation result. Join the org https://wandb.ai/mnbvc
```
wandb login
```

Here is an example command to evaluate the performance of the "PunctuationAndCapitalLetterDetector":
```
python evaluate_segmentation.py GptBatchDetector --remove_long_file True --detector_config '{"token_limit": 256}'
```

## Performance Results
The current performance results in terms of accuracy for the available detectors are as follows:

| Detector Name                        | Accuracy |
|--------------------------------------|----------|
| PunctuationAndCapitalLetterDetector  | 0.808260 |
| RuleBasedDetector                    | 0.866769 |
| GptOfflineDetector_t1400             | 0.941427 |
| GptBatchDetector_t256                | 0.96?    |
| GptBatchSequentialDetector_t500      | 0.963088 |


These accuracy values represent the overall correct predictions made by each detector. Higher accuracy values indicate better performance in distinguishing between softline and non-softline instances.

## Validation Dataset - human_joined_en_paragraph_19
The validation dataset used in this evaluation consists of the following characteristics:
- 19 files randomly selected from the unparallel corpus dataset.
- Contains English text only.
- Human-annotated line breaks are provided as the ground truth for evaluation.
The dataset contains two features:
- raw_text: the raw text containing both soft and hard linebreaks
- is_hard_linebreak: the ground truth, a list of boolean values (True for hard line break, False for soft line break)

## Output
The module outputs the following information:
- A results DataFrame showing the TP, FN, FP, and TN for each record in the validation dataset.
- A classification report providing precision, recall, F1-score, and support for softline and non-softline instances.


## batch_sequential_for_one_file.py

example: `python batch_sequential_for_one_file.py --key=sk-xxxxxx --dataset_index=0~10031`


options:

    --api_key API_KEY     openai api key
    --dataset_index DATASET_INDEX  数据集下标，0~10031

