import os
import json
import random
import shutil
os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'

import datasets


import const

# ALL_SOURCE_LANGS = ('zh','ar','fr','es','ru')
ALL_SOURCE_LANGS = ('zh',)
DST_DOC_PATH = const.ALIGN_OUTPUT_DIR / '源doc样例'

if __name__ == "__main__":
    for lang in ALL_SOURCE_LANGS:
        with open(const.ALIGN_OUTPUT_DIR / f'{lang}2en_dumpall_sorted.jsonl', 'r') as f:
            li = f.read().splitlines()
            print(len(li))
            li = [json.loads(line) for line in li if len(line) > 10000]
        print(len(li))
        record_set = set()
        for i, item in enumerate(li):
            record = item['record']
            record = record[:record.rfind('_')]
            print(record, len(item['src_text']))
            record_set.add(record)
        for lite_filename in os.listdir(const.DOWNLOAD_FILELIST_CACHE_DIR):
            filename = const.DOWNLOAD_FILELIST_CACHE_DIR / lite_filename
            with open(filename, 'r') as f:
                fcontent = f.read()
                fjson = json.loads(fcontent)
                for doc_idx, doc in enumerate(fjson['docs']):
                    if doc['symbol'] in record_set: # and doc['body'] != 'No full text found!'
                        filelist_idx = int(lite_filename.removeprefix('2023-2023_').removesuffix('.json'))
                        print('found:', doc['symbol'], 'in', filelist_idx, doc_idx, f"2023-2023_{filelist_idx}-{doc_idx}={lang}.doc")
                        try:
                            shutil.copy(const.DOWNLOAD_DOC_CACHE_DIR / 'doc' / f"2023-2023_{filelist_idx}-{doc_idx}={lang}.doc", DST_DOC_PATH / f"2023-2023_{filelist_idx}-{doc_idx}={lang}.doc")
                            shutil.copy(const.CONVERT_TEXT_CACHE_DIR / f"2023-2023_{filelist_idx}-{doc_idx}={lang}.txt", DST_DOC_PATH / f"2023-2023_{filelist_idx}-{doc_idx}={lang}.txt")
                            shutil.copy(const.DOWNLOAD_DOC_CACHE_DIR / 'doc' / f"2023-2023_{filelist_idx}-{doc_idx}=en.doc", DST_DOC_PATH / f"2023-2023_{filelist_idx}-{doc_idx}=en.doc")
                            shutil.copy(const.CONVERT_TEXT_CACHE_DIR / f"2023-2023_{filelist_idx}-{doc_idx}=en.txt", DST_DOC_PATH / f"2023-2023_{filelist_idx}-{doc_idx}=en.txt")
                        except Exception as e:
                            print('copy error:', e)
                # for record in record_set:
                #     if fcontent.find(record) != -1:
                #         print(record, '=>', filename)




"""
A/78/587/ADD.1 25556
A/78/27 6468
A/78/5/ADD.1 6924
S/2023/833 2585
A/77/6/ADD.1 2953
A/77/6/ADD.1 2453
A/77/6/ADD.1 2476
A/77/6/ADD.1 2371
A/77/6/ADD.1 2242
A/78/7/ADD.13 8146
6924: A/78/5/ADD.1 in 1 26 2023-2023_1-26=zh.doc 表格问题
found: A/77/6/ADD.1 in 1 41 2023-2023_1-41=zh.doc
6468: A/78/27 in 1 50 2023-2023_1-50=zh.doc 英文表格问题
found: S/2023/833 in 100 93 2023-2023_100-93=zh.doc
25556: A/78/587/ADD.1 in 104 2 2023-2023_104-2=zh.doc 表格问题
8146: A/78/7/ADD.13 in 104 17 2023-2023_104-17=zh.doc 中文很多英文很少，同样是表格问题



开会目标：
  1. 确定原始代码改不改，如果改的话最好重做一份数据
    # 2星期 -> 处理原始数据
    # 数据统计和Review -> 1月
    # 00 ~ 24 -> 

  2. 处理得不够好的数据，另外做脚本特殊处理还是怎么做
    # 处理得不够好的数据单独加一步，特殊处理表格
    


  3. 数据Review，之前没人做过，要不要做Review，把现有的管线能改进的地方改进了，再接着做论文
  4. 我们怎么知道改了代码或者做了特判的数据会比之前好？需要如何做统计，做什么样的统计才能证明改了之后会更好？


"""