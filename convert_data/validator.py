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

def copy_err():
    FIXDOCX_SOURCEDOC.mkdir(parents=True, exist_ok=True)
    FIXDOCX_DSTDOCX.mkdir(parents=True, exist_ok=True)
    with open(OUTSTAT, 'rb') as f:
        stat = pickle.load(f)

    DOC_BASEDIR = Path(r"E:\motrixDL\baiduyun\MNBVC")
    DOC_SOURCE = DOC_BASEDIR / "MNBVC—UN文件"
    DOC_MAP = DOC_BASEDIR / "doc_mapping.pkl"
    WPF_MAP = DOC_BASEDIR / "wpf_mapping.pkl"

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

if __name__ == "__main__":
    # get_error_text()
    # copy_err()
    # scan_pdf()
    # drop_dup()
    # semiauto_word_classification()
    compare_directory_files()
