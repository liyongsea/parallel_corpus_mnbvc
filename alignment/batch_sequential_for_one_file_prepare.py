import datasets
from pathlib import Path
import os

LOCAL_WORK_DIR = Path(f'{os.path.dirname(os.path.abspath(__file__))}/batch_cache')

if __name__ == "__main__":
    dataset = datasets.load_dataset('bot-yaya/un_pdf_random10032_preprocessed', split="train")

    (LOCAL_WORK_DIR / 'text_data').mkdir(exist_ok=True)