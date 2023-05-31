# Softline Detection Performance Evaluation

This module evaluates the performance of a softline detection method by comparing its predictions against human-annotated line breaks in a validation dataset. The performance metrics include TP (true positives), FN (false negatives), FP (false positives), TN (true negatives), and a classification report.

## Usage
Here is an example command to evaluate the performance of the "PunctuationAndCapitalLetterDetector":
```
python evaluate_segmentation.py PunctuationAndCapitalLetterDetector
```

## Performance Results
The current performance results in terms of accuracy for the available detectors are as follows:

| Detector Name                        | Accuracy |
|--------------------------------------|----------|
| PunctuationAndCapitalLetterDetector  | 0.78     |
| GptOfflineDetector                   | 0.93     |

These accuracy values represent the overall correct predictions made by each detector. Higher accuracy values indicate better performance in distinguishing between softline and non-softline instances.

## Validation Dataset - EN_PARAGRAPH_HUMAN_JOINED
The validation dataset used in this evaluation consists of the following characteristics:
- 17 files randomly selected from the unparallel corpus dataset.
- Contains English text only.
- Human-annotated line breaks are provided as the ground truth for evaluation.

## Output
The module outputs the following information:
- A results DataFrame showing the TP, FN, FP, and TN for each record in the validation dataset.
- A classification report providing precision, recall, F1-score, and support for softline and non-softline instances.


