from typing import Tuple
import itertools
from pathlib import Path
import json

from alignment.text_segmenter import HardLineBreakDetector
import alignment.utils as utils


class GPTBatchDetector(HardLineBreakDetector):
    def __init__(self, name, cache_dir, token_limit=1400, use_proxy=False):
        super().__init__(name)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        self.token_limit = token_limit
        self.use_proxy = use_proxy

    def create_batches(self, lines: list[str]) -> list[list[str]]:
        """
        Splits the input lines into batches, each containing as many lines as possible 
        while keeping the total number of tokens under 1400. This function uses an 
        approximation that 75 words is equal to 100 tokens. Adds an overlap of one line between batches.

        Args:
            lines (list[str]): The list of lines to be batched.

        Returns:
            list[list[str]]: The batched lines.
        """
        batches = []
        batch = []
        token_count = 0

        for i, line in enumerate(lines):
            words = line.split()
            # Estimate the token count for the current line
            line_token_count = len(words) * (100 / 75)
            # Check if adding this line would exceed the token limit
            if token_count + line_token_count > self.token_limit:
                # If so, finish the current batch and start a new one
                # Add the current line to the previous batch (overlap) and the new batch
                if batch:
                    batch.append(line)
                    batches.append(batch)
                batch = [line]
                token_count = line_token_count
            else:
                # Otherwise, add the line to the current batch
                batch.append(line)
                token_count += line_token_count

        # Add the last batch if it's not empty
        if batch:
            batches.append(batch)
        return batches

    def gpt_linebreak_detection_request(self, raw_text: str, record_id: str, batch_index: int) -> str:
        """
        Sends a request to the GPT-3.5 API to detect hard line breaks in the given text.
        Use record_id and batch_index to cache the output.

        Args:
            raw_text (str): The raw text to be processed.
            record_id (int): The unique id of the record.
            batch_index (int): The index of the batch.

        Returns:
            str: The processed text.
        """
        filename = self.cache_dir / f'record_{record_id}_processed_batch_{batch_index}.json'
        if not filename.exists():
            output_text = utils.gpt_detect_hard_line_breaks(raw_text, use_proxy=self.use_proxy)
            with filename.open('w') as f:
                json.dump(output_text, f)
        else:
            with filename.open('r') as f:
                output_text = json.load(f)
        output_text = output_text.replace('\n\n', '\n')
        if '\n\n' in output_text:
            print(record_id, batch_index)
        return output_text

    def process_batches(self, batches: list[list[str]], record_id: str) -> Tuple[list[str], list[bool]]:
        """
        Processes each batch of lines by sending them to the GPT-3.5 API and then 
        saving the results to disk and cache.

        Args:
            batches (list[list[str]]): The batched lines to be processed.
            record_id (str): The unique id of the record.

        Returns:
            Tuple[list[str], list[bool]]: The processed lines and their corresponding boolean detections.
        """
        processed_batches = []
        detections = []

        for i, batch in enumerate(batches):
            raw_text = "\n".join(batch)

            output_text = self.gpt_linebreak_detection_request(raw_text, record_id, i)
            # Compare the hard line breaks in the raw text with the output text
            is_hard_line_break = utils.compute_near_linebreak_match(raw_text, output_text, margin=10)

            processed_batches.append(output_text)
            detections.extend(is_hard_line_break)

        return processed_batches, detections

    def post_process(self, processed_batches: list[str], detections: list[bool]) -> list[bool]:
        """
        Performs post-processing on the processed lines and their detections to 
        handle overlaps between batches.

        Args:
            processed_batches (list[str]): The processed lines.
            detections (list[bool]): The boolean detections corresponding to the lines.

        Returns:
            list[bool]: The post-processed boolean detections.
        """
        # concate detections as one list
        post_processed_detections = list(itertools.chain.from_iterable(detections))
        return post_processed_detections

    def detect(self, lines: list[str], record_id: str, **kwargs) -> list[bool]:
        """
        Applies the GPT-3.5 detection technique to the given lines.
        This method first batches the lines, processes the batches, and then post-processes the results.

        Args:
            lines (list[str]): The lines to be detected.
            record_id (int): The unique id of the record. Use to cache the output of GPT

        Returns:
            list[bool]: The detection results.
        """
        batches = self.create_batches(lines)
        processed_batches, detections = self.process_batches(batches, record_id)
        # post_processed_detections = self.post_process(processed_batches, detections)
        return detections


if __name__ == '__main__':
    # Test the GPTBatchDetector
    detector = GPTBatchDetector('gpt-remote', "./cache_dir")
    # read val_files 432549.txt
    record_id = '453500'
    with open(f'{record_id}.txt', 'r') as f:
        lines = f.readlines()
    lines = [line.strip() for line in lines]

    post_processed_detections = detector.detect(lines, record_id)
    print(post_processed_detections)
    print(len(post_processed_detections), len(lines))
