import os
os.environ['ARGOS_DEVICE_TYPE'] = 'cuda' # 如果使用cuda取消注释这两行
from datetime import datetime
from pathlib import Path
import pickle
import shutil
from typing import List
import re
import time
import gc

import argostranslate.translate
import argostranslate.package
import requests
import datasets

import const

INSTALLED = {}

# 方案：所有语言往英语翻译
ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')
TARGET_LANG = 'en'
TEMPDIR_TRANSLATION = const.TRANSLATION_CACHE_DIR # 中间翻译暂存，支持重启
OUTPUT_DIR_TRANSLATION = const.TRANSLATION_OUTPUT_DIR # datasets输出


def get_or_install_translator(_from = 'fr', _to = 'en'):
    if tr := INSTALLED.get((_from, _to), None):
        return tr
    try:
        tr = argostranslate.translate.get_translation_from_codes(_from, _to)
        INSTALLED[(_from, _to)] = tr
        return tr
    except Exception as e:
        print(e, '\nattempt to install package...')
    # 经测试开系统代理下包可行
    # installed = argostranslate.package.get_installed_packages()
    # print(installed)
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    # print(available_packages)
    for i in filter(lambda x: x.from_code == _from and x.to_code == _to, available_packages):
        print('install', i)
        i.install()
    INSTALLED[(_from, _to)] = argostranslate.translate.get_translation_from_codes(_from, _to)
    return INSTALLED[(_from, _to)]

def translate(text: List[str], tr):
    translation = []
    for para in text:
        translation.append(tr.translate(para.replace('\n', ' '))) # WORD转出文本单个段落内仍有换行，由于argostranslate内部会切分换行，应该提前消掉令句子连贯
    return translation

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


def main():
    # {ar: str, zh: str, en: str, fr: str, ru: str, es: str, de: str, record: str, inner_id: str}
    dataset = datasets.load_from_disk(const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR) # 形如 https://huggingface.co/datasets/bot-yaya/undl_text 的输入
    # dataset = datasets.load(r'bot-yaya/undl_text') # 或者从hf下载
    # dataset = dataset.select(range(2))
    for src_lang in ALL_SOURCE_LANGS:
        translator = get_or_install_translator(src_lang, TARGET_LANG)
        src_lang_dump = TEMPDIR_TRANSLATION / src_lang
        src_lang_dump.mkdir(exist_ok=True, parents=True)
        for idx, row in enumerate(dataset):
            dump_path = src_lang_dump / f"{row['inner_id']}.pkl" # 每条记录存单文件，如果需要改并发就可以这么改
            if dump_path.exists():
                continue
            src_text = list(filter(bool, (clean_paragraph(x) for x in re.split('\n\n', row[src_lang])))) # \n\n分段，然后每段清理噪声文本，然后滤掉空段
            print(f"{row['inner_id']} {src_lang} -> {TARGET_LANG}, paragraph count={len(src_text)}")
            begin = datetime.now()
            dst_text = translate(src_text, translator)
            print(f"seconds per paragraph: {(datetime.now() - begin).total_seconds() / (len(dst_text) + 1e-3)}")
            with dump_path.open('wb') as f:
                pickle.dump(dst_text, f)

        def dataset_generator():
            for idx, row in enumerate(dataset):
                dump_path = src_lang_dump / f"{row['inner_id']}.pkl"
                with dump_path.open('rb') as f:
                    yield {
                        f'clean_{TARGET_LANG}': list(filter(bool, (clean_paragraph(x) for x in re.split('\n\n', row[TARGET_LANG])))),
                        f'clean_{src_lang}': list(filter(bool, (clean_paragraph(x) for x in re.split('\n\n', row[src_lang])))),
                        f"{src_lang}2{TARGET_LANG}":pickle.load(f),
                        'record': row['record'],
                        'inner_id': row['inner_id'],
                    }
        output_dir = OUTPUT_DIR_TRANSLATION / f"{src_lang}2{TARGET_LANG}"
        output_dir.mkdir(exist_ok=True, parents=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        translated_dataset = datasets.Dataset.from_generator(dataset_generator)
        translated_dataset.save_to_disk(output_dir) # 输出：每种语言对对应一个dataset，结构见dataset_generator

        gc.collect()

if __name__ == '__main__':
    main()
