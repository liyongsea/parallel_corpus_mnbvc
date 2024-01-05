import datasets


class TextSegmenter:
    """
    This class processes and segments raw text based on line breaks. 

    Attributes:
        raw_text (str): The raw text to be segmented.
        lines (list of str): The raw_text split by line breaks. Each element represents a line in the text.
        line_breaks (list of bool): A list of boolean values where each value indicates if a corresponding line 
                                     in 'lines' ends with a hard line break. `True` means a hard line break and `False` 
                                     implies a soft line break.

    """

    def __init__(self, raw_text):
        """
        Initialize the TextSegmenter class with raw_text

        Args:
            raw_text (str): The raw text to be segmented.
        """
        self.raw_text = raw_text
        self.lines = []
        self.line_breaks = []

    def split_by_linebreak(self):
        """
        Splits the raw text by line break. The result is stored in the `lines` attribute.
        """

        self.lines = self.raw_text.split('\n')

    def apply_hard_line_break_processing(self, detector):
        """
        Apply a chosen hard line break detector to the raw lines. The result is stored in the `line_breaks` attribute.

        Args:
            detector (object): The detector object that contains a detect method. 
                               This method should take a list of lines as input and return a list of booleans, 
                               where `True` signifies a hard line break.
        """
        self.line_breaks = detector.detect(self.lines)

    def transform(self):
        """
        Transforms the raw text to the expected output using the detected line breaks.

        Returns:
            list of str: A list where each item is a segment of the text. Segments are separated by hard line breaks ('\n'), 
                         and lines within segments are separated by soft line breaks (' ').
        """
        segments = []
        segment = ''

        for i, line in enumerate(self.lines):
            # Add line to segment, separating it with a space or newline character based on whether it's a hard break
            separator = '\n' if self.line_breaks[i] else ' '
            segment += (separator + line)

            if self.line_breaks[i]:
                # Remove the first character because it will be a '\n' that we don't want
                segments.append(segment[1:])
                segment = ''

        if segment:  # Add the last segment if it's not empty
            segments.append(segment[1:])
        
        return segments


class HardLineBreakDetector:
    def __init__(self, name):
        """
        Initialize the HardLineBreakDetector with a specific name
        """
        self.name = name

    def detect(self, lines: list[str],**kwargs) -> list[bool]:
        """
        Apply the specific detection technique to the given lines
        Returns a list of boolean values (True for hard line break, False for soft line break)
        of length len(lines) - 1
        """
        pass


class DetectorA(HardLineBreakDetector):
    def detect(self, lines: list[str], **kwargs) -> list[bool]:
        print(lines)
        return [line.startswith('–') for line in lines[1:]]


class PunctuationAndCapitalLetterDetector(HardLineBreakDetector):
    def detect(self, lines: list[str], **kwargs) -> list[bool]:
        breaks = []
        for i in range(len(lines) - 1):
            if lines[i].endswith(('.', ';')) or lines[i + 1][0].isupper() or lines[i + 1].startswith('–'):
                breaks.append(True)  # Hard break
            else:
                breaks.append(False)  # Soft break
        return breaks


class OfflineDetector(HardLineBreakDetector):
    def __init__(self, name, dataset_name="bot-yaya/EN_PARAGRAPH_GPT_JOINED"):
        """
        Use an in-memory dataset to detect hard line breaks (mainly for performance testing purposes)
        Args:
            name: name of the detector
            dataset_name: name of the dataset to use. The dataset should contains features:
                - record: the record id
                - is_hard_linebreak: a list of boolean values (True for hard line break, False for soft line break)
                Dataset available:
                - bot-yaya/EN_PARAGRAPH_GPT_JOINED: detection using GPT3.5           
        """
        super().__init__(name)
        self.records = {}

        ds = datasets.load_dataset(dataset_name, split="train")
        for i in ds:
            rec = i['record']
            self.records[rec] = i['is_hard_linebreak']
    
    def detect(self, lines: list[str], record_id: str, **kwargs) -> list[bool]:
        result = self.records.get(record_id, None)
        if result is not None:
            return result
        else:
            raise ValueError("Record %s not found in dataset" % record_id)


if __name__ == "__main__":
    raw_text = """– To strengthen or develop norms at the global, regional and national levels that
would reinforce and further coordinate efforts to prevent and combat the illicit
trade in small arms and light weapons in all its aspects;
– To develop agreed international measures to prevent and combat illicit arms
trafficking in and manufacturing of small arms and light weapons and to
reduce excessive and destabilizing accumulations and transfers of such
weapons throughout the world;"""

    segmenter = TextSegmenter(raw_text)
    segmenter.split_by_linebreak()

    print("Number of lines", len(segmenter.lines))  # Should print 6
    detectorA = DetectorA('DetectorA')
    segmenter.apply_hard_line_break_processing(detectorA)
    print(segmenter.line_breaks)  # Should print [False, False, True, False, False, False]

    detectorB = PunctuationAndCapitalLetterDetector('PunctuationAndCapitalLetterDetector')
    segmenter.apply_hard_line_break_processing(detectorB)
    print(segmenter.line_breaks)  # Should print the output based on the new detector's logic
