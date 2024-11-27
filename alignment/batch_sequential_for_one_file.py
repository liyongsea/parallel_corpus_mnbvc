import argparse
import os
import json
from pathlib import Path
import logging
import datasets
from .batch_sequential_detector import GPTBatchSequentialDetector


logging.basicConfig(level=logging.INFO)

LOCAL_WORK_DIR = Path(f'{os.path.dirname(os.path.abspath(__file__))}/batch_cache')
LOCAL_WORK_DIR.mkdir(exist_ok=True)

DATASET_CACHE_DIR = LOCAL_WORK_DIR / 'dataset'
DATASET_CACHE_DIR.mkdir(exist_ok=True)

DETECTOR_CACHE_DIR = LOCAL_WORK_DIR / 'batch_sequential_cache_dir'
DETECTOR_CACHE_DIR.mkdir(exist_ok=True)

DONE_DIR = LOCAL_WORK_DIR / 'done'
DONE_DIR.mkdir(exist_ok=True)


def get_and_cache_dataset(path='ranWang/un_pdf_random_preprocessed', split='train'):
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(DATASET_CACHE_DIR)
    except:
        dataset = datasets.load_dataset(path, split=split)
        dataset.save_to_disk(DATASET_CACHE_DIR)
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', type=str, help='openai api key')
    parser.add_argument('--dataset_index', type=int, help='直接给下标吧，0~15293')

    args = parser.parse_args()

    if args.dataset_index != 0 and not args.dataset_index:
        raise ValueError("dataset_index must input")
    
    if not args.api_key:
        raise ValueError("api_key must input")
    
    single_file_data = get_and_cache_dataset()[args.dataset_index]
    record = single_file_data['record']


    os.environ['OPENAI_API_KEY'] = args.api_key

    detector = GPTBatchSequentialDetector('', cache_dir=DETECTOR_CACHE_DIR.absolute(), use_proxy=False, ignore_leading_noise_lines=True) # 如果需要用反代这里use_proxy改True
    is_hard_linebreak: list[bool] = detector.detect(single_file_data['en'].splitlines(), record_id=record)

    with (DONE_DIR / f'{record}.list').open('w') as f:
        json.dump(is_hard_linebreak, f)
