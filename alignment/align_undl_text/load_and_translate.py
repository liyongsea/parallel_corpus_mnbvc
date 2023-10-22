import os.path
from pathlib import Path
import time
import re
from datasets import load_from_disk
import argostranslate.package
import argostranslate.translate
import os

PATH = r'F:\undl_text_local'

def load_random_clean_docs(ds, l, r):
    # sample_doc = dataset
    sample_doc = ds.select(range(l, r))
    clean_doc = sample_doc.remove_columns(['ar', 'fr', 'ru', 'es', 'de'])
    clean_doc = clean_doc.map(lambda x: {'clean_en': [clean_paragraph(para) for para in re.split('\n\n', x['en'])]})
    clean_doc = clean_doc.map(lambda x: {'clean_zh': [clean_paragraph(para) for para in re.split('\n\n', x['zh'])]})
    # clean_doc = clean_doc.remove_columns(['zh', 'en'])
    return clean_doc


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


def translate(row):
    translation = []
    if not any(row['clean_en']) or not any(row['clean_zh']):
        return {"en2zh": []}
    for para in row['clean_en']:
        if not re.search('[A-Za-z]+', para):
            translation.append(para)
        else:
            try:
                translation.append(argostranslate.translate.translate(para, 'en', 'zh'))
            except Exception as e:
                print(e)
                translation.append(para)
    return {"en2zh": translation}

def install_translator():
    # 经测试开系统代理下包可行
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == 'en' and x.to_code == 'zh', available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())


if __name__ == '__main__':
    # os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'
    # use_proxy()
    # install_translator()
    dataset = load_from_disk(PATH)
    STEP = 10
    OUT = Path(rf'F:\undl_en2zh_{STEP}')
    OUT.mkdir(exist_ok=True)
    for i in range(0, len(dataset), STEP):
        if OUT.joinpath(str(i)).exists():
            print('skip', i)
            continue
        docs = load_random_clean_docs(dataset, i, i + STEP)
        start = time.perf_counter()
        # docs = docs.map(translate, num_proc=2)
        docs = docs.map(translate)
        print('translation time: %d' % (time.perf_counter() - start))
        # docs = docs.add_column('translation', trans_docs)
        docs.save_to_disk(OUT.joinpath(str(i)))
