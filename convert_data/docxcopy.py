import re
import os
import shutil
import pickle
from itertools import chain

BASE_DIR = r'E:\motrixDL\baiduyun\MNBVC'
ERR_LOG_DIR = BASE_DIR + r'\err'
SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'
SAVED_DIR = BASE_DIR + r'\docxoutput'

TASK_CACHE_DIR = BASE_DIR + r'\oswalkcache.pkl'
DOC_GROUP_CACHE_DIR = BASE_DIR + r'\doc_mapping.pkl'
WPF_GROUP_CACHE_DIR = BASE_DIR + r'\wpf_mapping.pkl'

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

doc_mapping = {}
wpf_mapping = {}
for dirpath, dirnames, filenames in os.walk(SOURCE_DIR):
    subdir = os.path.split(dirpath)[-1]
    doc_cur = []
    wpf_cur = []
    for dfn in filenames:
        absfn = os.path.join(dirpath, dfn)
        l = dfn.lower()
        if dfn.startswith("~$"):
            print("~$:", absfn)
            os.remove(absfn)
        elif l.endswith(".tmp"):
            print("tmp:", absfn)
            os.remove(absfn)
        elif l.endswith(".doc"):
            doc_cur.append(dfn)
        elif l.endswith(".wpf"):
            wpf_cur.append(dfn)
        elif l.endswith(".docx"):
            shutil.copy(absfn, saved_path(absfn))
        else:
            print('unknown:', absfn)
    if doc_cur:
        doc_mapping[subdir] = doc_cur
    if wpf_cur:
        wpf_mapping[subdir] = wpf_cur

with open(DOC_GROUP_CACHE_DIR, 'wb') as f:
    pickle.dump(doc_mapping, f)
with open(WPF_GROUP_CACHE_DIR, 'wb') as f:
    pickle.dump(wpf_mapping, f)

print('done', len(doc_mapping), len(chain(doc_mapping.values())), len(wpf_mapping), chain(wpf_mapping.values()))