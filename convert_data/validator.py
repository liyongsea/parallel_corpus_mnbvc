import re
import shutil
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

IS_ALL_THIS_LANG = {
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

THIS_LANG_TH = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': 0.2,
    'zh': 0.2,
    'fr': 0.1,
    'es': 0.1,
    'ru': 0.2,
    'de': 0.1,
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

def map_func(row):
    for k, _ in IS_ALL_THIS_LANG.items():
        for lang, pat in IS_ALL_THIS_LANG.items():
            if lang == k or lang == 'en':
                continue
            a = pat.findall(row[k])
            rate = len(a) / (len(row[k]) + 1e-3)
            if rate > THIS_LANG_TH[lang]:
                r = (row['record'], k, lang, rate)
                print(r)
                stat.append(r)
                stattxt.append(' '.join(map(str, r)))
                break

def get_error_text():
    DS.map(map_func)
    with open(OUTSTAT, 'wb') as f:
        pickle.dump(stat, f)
    with open(OUTSTATTXT, 'w') as f:
        f.write('\n'.join(stattxt))

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


if __name__ == "__main__":
    # copy_err()
    # scan_pdf()
    drop_dup()