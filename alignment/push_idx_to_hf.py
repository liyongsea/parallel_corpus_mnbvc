import sys
import os
from typing import Tuple
from pathlib import Path
from argparse import ArgumentParser

import datasets
import pylcs

### 工作路径相关代码
WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可

def cat(*args): 
    return '/'.join(args)

def my_path(*args):
    """相对路径"""
    return cat(WORKDIR_ABSOLUTE, *args)
###

def get_and_cache_dataset():
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(my_path())
        return dataset
    except:
        dataset = datasets.load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED', split='train')
        dataset.save_to_disk(my_path())
        return dataset

def read_secret(relative_path, hint=''):
    """隐私文件缓存，之后用环境变量替换"""
    relative_path += '.secret'
    abs_path = my_path(relative_path)
    if not os.path.exists(abs_path):
        cmd = input(f'[{hint} {relative_path}] The secret file is required, your input will be saved in {abs_path}. \nNow please input:')
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(cmd)
        print(f'Your input is saved to {abs_path}, modify it if it is incorrect.')

    try:
        with open(abs_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(e)
        print(f'please put your token to {relative_path} in the root dir specify in WORKDIR_ABSOLUTE')
        print('current WORKDIR_ABSOLUTE:', WORKDIR_ABSOLUTE)
        raise



if __name__ == "__main__":
    print(sys.argv)
    ap = ArgumentParser(prog=sys.argv[0])
    ap.add_argument('idx_directory', help='directory for idx files')
    args = ap.parse_args()
    ds = get_and_cache_dataset()

    dir = args.idx_directory

    def convert_idx():
        idx_map = {}
        for i in os.listdir():
            if i.endswith('.idx'):
                rec = i.removesuffix('.idx')
                with open(cat(dir, i), 'r', encoding='utf-8') as f:
                    idx_map[rec] = map(int, f.read().split(','))
        data2Bupload = []
        for i in ds.filter(lambda x: x['record'] in idx_map):
            br_rev = [True for _ in i['en'].splitlines()]
            for j in idx_map[i['record']]:
                br_rev[j] = False
            data2Bupload.append({'record': i['record'], 'raw_text': i['en'], 'is_hard_linebreak': br_rev})
        return data2Bupload

    def convert_wr():
        """临时代码，转换手标数据"""
        import json
        from get_labeled_index import lcs_sequence_alignment, get_br_indexes_from_alignmap
        outputmap = {}
        jmap = {}
        for i in os.listdir(dir):
            with open(cat(dir, i, 'output.txt'), 'r', encoding='utf-8') as f:
                outputmap[i] = f.read()
            with open(cat(dir, i, 'is_hard_line_break.json'), 'r', encoding='utf-8') as f:
                jmap[i] = json.load(f)
        data2Bupload = []
        for i in ds.filter(lambda x: x['record'] in outputmap):
            rec = i['record']
            src = i['en']
            align_map, _, _ = lcs_sequence_alignment(src, outputmap[rec])
            br = get_br_indexes_from_alignmap(align_map)
            br_rev = [True for _ in src.splitlines()]
            for j in br:
                br_rev[j] = False
            # assert br_rev == jmap[rec] # 顺便测一下对齐脚本正确性
            data2Bupload.append({'record': i['record'], 'raw_text': i['en'], 'is_hard_linebreak': br_rev})
        return data2Bupload

    data2Bupload = convert_idx()
    hf_tk = read_secret('hf_token')


    # from helper import use_proxy
    # use_proxy()
    data2Bupload = datasets.Dataset.from_list(data2Bupload)
    data2Bupload.push_to_hub(repo_id='EN_PARAGRAPH_GPT_JOINED', split="train", token=hf_tk)
    # data2Bupload.push_to_hub(repo_id='EN_PARAGRAPH_HUMAN_JOINED', split="train", token=hf_tk)

