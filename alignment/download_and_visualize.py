
import datetime
from itertools import chain
import os
import time
import json
from typing import Tuple
import traceback
import datasets

from pathlib import Path
from datasets.dataset_dict import DatasetDict

WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可
RETRY_TIME = 5
SLEEP_TIME = 0

def cat(*args): 
    return '/'.join(args)

def my_path(*args):
    """相对路径"""
    return cat(WORKDIR_ABSOLUTE, *args)

def dump_to_file(row):
    raw = row['raw_text']
    rec = row['record']
    br_rev = row['is_hard_linebreak']
    buf = []
    for p, i in enumerate(raw.splitlines()):
        if p == 0:
            buf.append(i)
        elif br_rev[p - 1]:
            buf.append(i)
        else:
            buf[-1] += ' ' + i

    with open(my_path('dump', f'{rec}.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(buf))


if __name__ == "__main__":
    Path(my_path('dump')).mkdir(exist_ok=True)
    from helper import use_proxy
    use_proxy()
    dataset = datasets.load_dataset('bot-yaya/EN_PARAGRAPH_GPT_JOINED', split='train')
    # dataset = datasets.load_dataset('bot-yaya/EN_PARAGRAPH_HUMAN_JOINED', split='train')
    dataset.map(dump_to_file)
        
    
