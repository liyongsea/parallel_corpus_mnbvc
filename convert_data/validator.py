import re
import shutil
import time
import string
import datasets
from pathlib import Path
import pickle
import os

BASE_DIR = Path(r'F:')
TASK_SOURCE = BASE_DIR / 'undl_text_local'
DS = datasets.load_from_disk(TASK_SOURCE)
OUTSTAT = BASE_DIR / 'stat.pkl'
OUTSTATTXT = BASE_DIR / 'stat.txt'
SRC = 'de'
DST = 'en'
TH = 0.4

FIXDOCX = BASE_DIR / 'fixdocx'
FIXDOCX_SOURCEDOC = FIXDOCX / 'doc'
FIXDOCX_DSTDOCX = FIXDOCX / 'docx'

DOC_BASEDIR = Path(r"E:\motrixDL\baiduyun\MNBVC")
DOC_SOURCE = DOC_BASEDIR / "MNBVC—UN文件"
DOC_MAP = DOC_BASEDIR / "doc_mapping.pkl"
WPF_MAP = DOC_BASEDIR / "wpf_mapping.pkl"
REV_MAP = DOC_BASEDIR / "rev_mapping.pkl" # 文件名到文件号及语言的映射

ALL_THIS_LANG_PAT = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': re.compile(r'[\u0600-\u06ff]'),
    'zh': re.compile(r'[\u3006\u3007\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002ebef\U00030000-\U0003134f]'),
    'fr': re.compile(r'[À-Ÿ]'),
    'es': re.compile(r'[áéíóúñÁÉÍÓÚÑüÜ]'),
    'ru': re.compile(r'[А-Яа-яЁёъь]'),
    'en': re.compile(r'[A-Za-z]'),
    'de': re.compile(r'[ÄäÖöÜüß]'),
}

ALL_THIS_LANG_TH = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': 0.2,
    'zh': 0.2,
    'fr': 0.1,
    'es': 0.1,
    'ru': 0.2,
    'de': 0.1,
}

LANG_OCC_PAT = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': re.compile('[' + re.escape(string.punctuation) + r'\s\u0600-\u06ff\w]'),
    'zh': re.compile('[' + re.escape(string.punctuation) + r'\s\w\u3006\u3007\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002ebef\U00030000-\U0003134f]'),
    'fr': re.compile('[' + re.escape(string.punctuation) + r'\s\wÀ-Ÿ]'),
    'es': re.compile('[' + re.escape(string.punctuation) + r'\s\wáéíóúñÁÉÍÓÚÑüÜ]'),
    'ru': re.compile('[' + re.escape(string.punctuation) + r'\s\wА-Яа-яЁёъь]'),
    'en': re.compile('[' + re.escape(string.punctuation) + r'\s\w]'),
    'de': re.compile('[' + re.escape(string.punctuation) + r'\s\wÄäÖöÜüß]'),
}

LANG_OCC_TH = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': 0.6,
    'zh': 0.6,
    'fr': 0.8,
    'es': 0.8,
    'ru': 0.8,
    'de': 0.8,
    'en': 0.8,
}

lang_map = {
    'ar':'阿拉伯文',
    'zh':'中文',
    'en':'英文',
    'fr':'法文',
    'ru':'俄文',
    'es':'西班牙文',
    'de':'德国',
}

lang_rev_map = {
    '阿拉伯文':'ar',
    '中文':'zh',
    '英文':'en',
    '法文':'fr',
    '俄文':'ru',
    '西班牙文':'es',
    '德国':'de',
}

stat = []
stattxt = []

def detect_other_lang(row):
    for k, _ in ALL_THIS_LANG_PAT.items():
        for lang, pat in ALL_THIS_LANG_PAT.items():
            if lang == k or lang == 'en':
                continue
            a = pat.findall(row[k])
            rate = len(a) / (len(row[k]) + 1e-3)
            if rate > ALL_THIS_LANG_TH[lang]:
                r = (row['record'], k, lang, rate)
                print(r)
                stat.append(r)
                stattxt.append(' '.join(map(str, r)))
                break

def check_this_lang_rate(row):
    for k, pat in LANG_OCC_PAT.items():
        a = pat.findall(row[k])
        rate = len(a) / (len(row[k]) + 1e-3)
        if rate < LANG_OCC_TH[k]:
            r = (row['record'], k, k, rate)
            print(r)
            stat.append(r)
            stattxt.append(' '.join(map(str, r)))
            break

def get_error_text():
    # DS.map(detect_other_lang)
    DS.map(check_this_lang_rate)
    with open(OUTSTAT, 'wb') as f:
        pickle.dump(stat, f)
    with open(OUTSTATTXT, 'w') as f:
        f.write('\n'.join(sorted(stattxt)))

sufpat = re.compile(r'\.[a-zA-Z]+$')

def construct_rev_index():
    with open(DOC_MAP, 'rb') as f:
        doc_map = pickle.load(f)
    with open(WPF_MAP, 'rb') as f:
        wpf_map = pickle.load(f)
    
    rev_map = {}
    for mp in [doc_map, wpf_map]:
        for rec, langs in mp.items():
            for fi in langs:
                lang, _ = fi.split('-')
                iso_code = lang_rev_map[lang]
                fjkey = sufpat.sub('', fi, 1)
                rev_map[fjkey] = (rec, iso_code)
    with open(REV_MAP, 'wb') as f:
        pickle.dump(rev_map, f)

def copy_err():
    FIXDOCX_SOURCEDOC.mkdir(parents=True, exist_ok=True)
    FIXDOCX_DSTDOCX.mkdir(parents=True, exist_ok=True)
    with open(OUTSTAT, 'rb') as f:
        stat = pickle.load(f)

    OUTDIRS = [
        DOC_BASEDIR / 'docxoutput',
        DOC_BASEDIR / 'docxoutput2',
        DOC_BASEDIR / 'wpf_err_recovered',
        DOC_BASEDIR / 'wpf_libre_converted',
    ]

    with open(DOC_MAP, 'rb') as f:
        doc_map = pickle.load(f)
    with open(WPF_MAP, 'rb') as f:
        wpf_map = pickle.load(f)
    
    for r in stat:
        rec, src, dst, rate = r
        pf = lang_map[src]
        for mp in [doc_map, wpf_map]:
            if rec in mp:
                for fi in mp[rec]:
                    if fi.startswith(pf):
                        shutil.copy(DOC_SOURCE / rec / fi, FIXDOCX_SOURCEDOC / fi)
                        fjkey = sufpat.sub('.docx', fi, 1)
                        print('copy src', DOC_SOURCE / rec / fi)
                        for fj in OUTDIRS:
                            if (fj / fjkey).exists():
                                shutil.copy(fj / fjkey, FIXDOCX_DSTDOCX / fjkey)
                                print('copy dst', fj / fjkey)
                                break
                        break

def drop_dup():
    DONEDIRS = [
        FIXDOCX / 'convert_err',
        FIXDOCX / 'convert_encode_err',
        FIXDOCX / 'no_err',
        FIXDOCX / 'spider_err',
        FIXDOCX / 'spider_pdf',
        FIXDOCX / 'spider_other',
        FIXDOCX / 'spider_html',
        DOC_BASEDIR / 'err',
    ]
    done = set()
    for d in DONEDIRS:
        for f in os.listdir(d):
            key = sufpat.sub('', f, 1)
            done.add(key)
    for f in os.listdir(FIXDOCX_SOURCEDOC):
        key = sufpat.sub('', f, 1)
        if key in done:
            print('drop', f)
            os.remove(FIXDOCX_SOURCEDOC / f)

    for f in os.listdir(FIXDOCX_DSTDOCX):
        key = sufpat.sub('', f, 1)
        if key in done:
            print('drop', f)
            os.remove(FIXDOCX_DSTDOCX / f)
        # else:
            # done.add(key)

def scan_pdf():
    import magic
    for doc in os.listdir(FIXDOCX_SOURCEDOC):
        docpath = FIXDOCX_SOURCEDOC / doc
        typ = magic.from_buffer(docpath.read_bytes(), mime=True)
        if typ.endswith('pdf'):
            print('pdf:', doc)
            shutil.move(docpath, FIXDOCX / 'spider_pdf' / doc)
        elif typ == 'text/html':
            print('html:', doc, docpath.read_bytes())
            shutil.move(docpath, FIXDOCX / 'spider_html' / doc)
        elif typ != 'application/msword' and typ != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            print(typ, doc)

def semiauto_word_classification():
    import pyautogui
    import keyboard
    # while 1:
        # c = keyboard.read_key()
        # print(c)
    for i in os.listdir(FIXDOCX_SOURCEDOC):
        print(FIXDOCX_SOURCEDOC / i)
        os.startfile(FIXDOCX_SOURCEDOC / i)
        while 1:
            print('listening keys...')
            c = keyboard.read_key()
            if not keyboard.is_pressed(c):
                continue
            print(c)
            if c == 'f12':
                time.sleep(0.3)
                pyautogui.hotkey('alt', 't')
                time.sleep(0.3)
                pyautogui.press('down')
                pyautogui.press('up')
                pyautogui.press('up')
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.3)
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.3)
                pyautogui.write(r'F:\fixdocx\correct_docx')
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.3)
                pyautogui.hotkey('alt', 's')
            elif c == 's':
                time.sleep(0.5)
                shutil.move(FIXDOCX_SOURCEDOC / i, FIXDOCX / 'spider_err' / i)
                break
            elif c == 'n':
                time.sleep(0.5)
                shutil.move(FIXDOCX_SOURCEDOC / i, FIXDOCX / 'no_err' / i)
                break
            elif c == 'c':
                time.sleep(0.5)
                shutil.move(FIXDOCX_SOURCEDOC / i, FIXDOCX / 'convert_err' / i)
                break
        # if c == 'f12':

def compare_directory_files():
    d1 = FIXDOCX / 'convert_err'
    d2 = FIXDOCX / 'correct_docx'
    s2 = set(map(lambda x: sufpat.sub('', x, 1), os.listdir(d2)))
    for f in os.listdir(d1):
        fn = sufpat.sub('', f, 1)
        if fn not in s2:
            print('+', f)
        else:
            s2.discard(fn)
    for f in s2:
        print('-', f)

def docx2text():
    SOURCE_DOCX_DIR = FIXDOCX / 'correct_docx'
    OUT = FIXDOCX / 'correct_text'
    for i in os.listdir(SOURCE_DOCX_DIR):
        filepath = SOURCE_DOCX_DIR / i
        outpath = OUT / (sufpat.sub('', i, 1) + '.txt')
        cmd = f"pandoc -i {filepath} -t plain -o {outpath} --strip-comments"
        print(cmd)
        r = os.popen(cmd)
        print(r.read())

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

def get_patch_file_id():
    DROP_DIRS = [
        FIXDOCX / 'blank_file',
        FIXDOCX / 'convert_encode_err',
        FIXDOCX / 'no_err',
        FIXDOCX / 'spider_encrypt',
        FIXDOCX / 'spider_err',
        FIXDOCX / 'spider_html',
        FIXDOCX / 'spider_other',
        FIXDOCX / 'spider_pdf',
        FIXDOCX / 'tex_error',
    ]
    REWORK_DIRS = FIXDOCX / 'correct_text'
    import argostranslate.translate
    import argostranslate.package

    with open(REV_MAP, 'rb') as f:
        rev_map = pickle.load(f)
    drops = set()
    reworks = {}
    for d in DROP_DIRS:
        for f in os.listdir(d):
            key = sufpat.sub('', f, 1)
            drops.add(rev_map[key])
    for p, f in enumerate(os.listdir(REWORK_DIRS)):
        key = sufpat.sub('', f, 1)
        with open(REWORK_DIRS / f, 'r', encoding='utf-8') as ff:
            ffc = ff.read()
        record, isocode = rev_map[key]
        tr = argostranslate.translate.get_translation_from_codes(isocode, 'en')
        cleaned = list(filter(bool, (clean_paragraph(para) for para in re.split('\n\n', ffc))))
        print(p, len(ffc), record, isocode)
        reworks[(record, isocode)] = (
            ffc, cleaned, list(map(lambda x: tr.translate(x.replace('\n', ' ')), cleaned))
        )
        print(str(reworks[(record, isocode)][2])[:200])
    print(drops, reworks)
    with open(FIXDOCX / 'drops_reworks.pkl', 'wb') as f:
        pickle.dump((drops, reworks), f)
    return drops, reworks

if __name__ == "__main__":
    # get_error_text()
    # construct_rev_index()
    # copy_err()
    # scan_pdf()
    # drop_dup()
    # semiauto_word_classification()
    # compare_directory_files()
    # docx2text()
    get_patch_file_id()