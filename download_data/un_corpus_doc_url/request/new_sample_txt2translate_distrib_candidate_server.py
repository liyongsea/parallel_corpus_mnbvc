import os
# os.environ['ARGOS_DEVICE_TYPE'] = 'cuda' # 如果使用cuda取消注释这两行
import pickle
from typing import List
import re
import gc

import datasets
from fastapi import FastAPI
from fastapi import HTTPException
from typing import List
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
from pydantic import BaseModel

import const


INSTALLED = {}

# 方案：所有语言往英语翻译
ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')
TARGET_LANG = 'en'

def clean_paragraph(paragraph):
    lines = paragraph.split('\n')
    para = ''
    table = []

    for line in lines:
        line = line.strip()

        # 表格线或其他分割线
        if re.match(r'^\+[-=+]+\+|-+|=+|_+$', line):
            if not para.endswith('\n'):
                para += '\n'
            if len(table) > 0:
                para += '\t'.join(table)
                table = []
        # 表格中的空行
        elif re.match(r'^\|( +\|)+$', line):
            para += '\t'.join(table) + ' '
            table = []
        # 表格中的内容行
        elif re.match(r'^\|([^|]+\|)+$', line):
            if len(table) == 0:
                table = line[1:-2].split('|')
            else:
                arr = line[1:-2].split('|')
                if len(arr) == len(table):
                    table = [table[i].strip() + arr[i].strip() for i in range(len(table))]
                elif len(arr) > len(table):
                    table = [table[i].strip() + arr[i].strip() if i < len(table) else arr[i].strip() for i in range(len(arr))]
                else:
                    table = [table[i].strip() + arr[i].strip() if i < len(arr) else table[i].strip() for i in range(len(table))]
        # 正文内容
        else:
            para += ' ' + line
    if len(table) > 0:
        if not para.endswith('\n'):
            para += '\n'
        para += '\t'.join(table)
    return re.sub(r'[ \t]{2,}', ' ', re.sub(r'\n{2,}', '\n', para)).strip()


dataset = datasets.load_from_disk(const.CONVERT_DATASET_CACHE_DIR)
inner_id2idx = {}
# {ar: str, zh: str, en: str, fr: str, ru: str, es: str, de: str, record: str, inner_id: str}
for p, row in enumerate(dataset):
    inner_id2idx[row['inner_id']] = p # inner_id是为了能够当合法的文件名写到磁盘上

def task_gen():
    for src_lang in ALL_SOURCE_LANGS:
        src_lang_dump = const.TRANSLATION_CACHE_DIR / src_lang
        src_lang_dump.mkdir(exist_ok=True, parents=True)
        for idx, row in enumerate(dataset):
            dump_path = src_lang_dump / f"{row['inner_id']}.pkl" # 每条记录存单文件，如果需要改并发就可以这么改
            if dump_path.exists():
                continue
            src_text = list(filter(bool, (clean_paragraph(x) for x in re.split('\n\n', row[src_lang])))) # \n\n分段，然后每段清理噪声文本，然后滤掉空段
            yield src_lang, src_text, row['inner_id']

        gc.collect()

itr = task_gen()

app = FastAPI(redoc_url=None, docs_url=None, swagger_ui_init_oauth=None, openapi_url=None)
app.add_middleware(GZipMiddleware)

@app.get('/')
async def task_getter(ver: int):
    try:
        src_lang, src_text, inner_id = next(itr)
    except StopIteration:
        print('no task')
        return {'taskid': -1}
    return {
        'taskid': inner_id,
        'src': src_lang,
        'dst': TARGET_LANG,
        'data': src_text
    }

class UplBody(BaseModel):
    taskid: str
    client: str
    src: str
    dst: str
    out: List[str]

@app.post('/upl')
async def task_submit(body: UplBody):
    src_lang_dump = const.TRANSLATION_CACHE_DIR / body.src
    src_lang_dump.mkdir(exist_ok=True, parents=True)
    dump_path = src_lang_dump / f"{body.taskid}.pkl" # 每条记录存单文件，如果需要改并发就可以这么改
    if dump_path.exists():
        raise HTTPException(400, 'taskid already exists')
    with open(dump_path, 'wb') as f:
        pickle.dump(body.out, f)
    return 1

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=const.TRANSLATION_SERVER_PORT)
