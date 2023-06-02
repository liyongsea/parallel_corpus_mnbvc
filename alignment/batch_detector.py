from typing import Tuple
from text_segmenter import HardLineBreakDetector
import utils


class GPTBatchDetector(HardLineBreakDetector):
    def __init__(self, name, token_limit=1400):
        """
        Initialize the GPTBatchDetector with a specific name and token limit.
        """
        super().__init__(name)
        self.token_limit = token_limit

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

        self._batches = batches
        return self._batches

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

            # check if the processing is already done
            output_text, is_hard_line_break = self.read_cache(record_id, i)
            if output_text is None or is_hard_line_break is None:
                # if not, call the gpt_linebreak_detect function
                output_text = gpt_linebreak_detect(raw_text)

                # Compare the hard line breaks in the raw text with the output text
                is_hard_line_break = compare_breaks(raw_text, output_text)

                # Save the processed batch and its detections to disk and cache
                self.write_cache(output_text, is_hard_line_break, record_id, i)

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
        pass

    def detect(self, lines: list[str],**kwargs) -> list[bool]:
        """
        Applies the GPT-3.5 detection technique to the given lines.
        This method first batches the lines, processes the batches, and then post-processes the results.

        Args:
            lines (list[str]): The lines to be detected.

        Returns:
            list[bool]: The detection results.
        """
        batches = self.create_batches(lines)
        processed_batches, detections = self.process_batches(batches)
        post_processed_detections = self.post_process(processed_batches, detections)
        return post_processed_detections

    def write_cache(self, output_text: str, is_hard_line_break: list[bool], record_id: str, batch_index: int):
        filename = self.cache_dir / f'record_{record_id}_processed_batch_{batch_index}.json'
        with filename.open('w') as f:
            json.dump({"output_text": output_text, "is_hard_line_break": is_hard_line_break}, f)
        self.cache[record_id] = filename

    def read_cache(self, record_id: str, batch_index: int) -> Tuple[str, list[bool]]:
        filename = self.cache.get(record_id)
        if filename and filename.exists():
            with filename.open('r') as f:
                data = json.load(f)
            return data.get("output_text"), data.get("is_hard_line_break")
        return None, None


if __name__ == '__main__':
    # Test the GPTRemoteDetector
    detector = GPTBatchDetector('gpt-remote', "./cache_dir")
    # read val_files 432549.txt
    with open('val_files/432549.txt', 'r') as f:
        lines = f.readlines()
    # remove \n in lines
    lines = [line.strip() for line in lines]
    print(lines[:10])

    batches = detector.create_batches(lines)
    print("Number of batches: ", len(batches))
    print("start batch 0")
    print(batches[0])
    print()
    print("start batch 1")
    print(batches[1])

