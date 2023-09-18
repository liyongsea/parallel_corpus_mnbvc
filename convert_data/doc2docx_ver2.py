# 换了个枚举写法，比原来效率更快
from queue import Empty
import re
import os
import win32com.client as win32
from win32com.client import constants
from pathlib import Path
import multiprocessing as mp
import psutil
import pickle
import datetime

BASE_DIR = r'E:\motrixDL\baiduyun\MNBVC'
ERR_LOG_DIR = BASE_DIR + r'\err'
SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'
SAVED_DIR = BASE_DIR + r'\docxoutput'

TASK_CACHE_DIR = BASE_DIR + r'\oswalkcache.pkl'
GROUP_CACHE_DIR = BASE_DIR + r'\dirmappingcache.pkl'

TIMEOUT = 7

FROM = 0
TO = 166779
STEP = 1

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

def save_as_docx(_from: int, _to: int, _step: int, cont_flg: bool, cont_cursor: int, q: mp.Queue):
    last_time = datetime.datetime.now()
    word = win32.gencache.EnsureDispatch('Word.Application')
    with open(TASK_CACHE_DIR, 'rb') as f:
        li = pickle.load(f)
    
    for idx in range(_from, _to, _step):
        subdir, filenames = li[idx]
        curr_time = datetime.datetime.now()
        print(idx, len(li), (curr_time - last_time).total_seconds(), filenames)
        last_time = curr_time

        if cont_flg:
            cont_flg = False
            fnid = cont_cursor
        else:
            fnid = 0

        for fnid in range(fnid, len(filenames)):
            q.put((idx, fnid))
            dfn = filenames[fnid]
            absfn = os.path.join(SOURCE_DIR, subdir, dfn)
            if not os.path.exists(saved_path(absfn)) and not os.path.exists(err_path(absfn)):
                doc = None
                try:
                    file_abs = os.path.abspath(absfn)
                    new_file_abs = saved_path(file_abs)
                    doc = word.Documents.Open(file_abs)
                    doc.SaveAs(new_file_abs, FileFormat=constants.wdFormatXMLDocument)
                    doc.Close(False)
                    doc = None
                except Exception as e:
                    print(e, file_abs)
                    with open(err_path(file_abs), 'w') as f:
                        pass
                    if doc is not None:
                        doc.Close(False)
                        doc = None
    q.put(None)

def kill_word():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            p = psutil.Process(pid)
            p.kill()

def entrance(FROM=FROM, TO=TO, STEP=STEP):
    Path(ERR_LOG_DIR).mkdir(exist_ok=True)
    Path(SOURCE_DIR).mkdir(exist_ok=True)
    Path(SAVED_DIR).mkdir(exist_ok=True)

    if not os.path.exists(TASK_CACHE_DIR):
        lw = list(os.walk(SOURCE_DIR))
        li = []
        mapping = {}
        for dirpath, dirnames, filenames in lw:
            subdir = os.path.split(dirpath)[-1]
            cur = [subdir, []]
            for dfn in filenames:
                if dfn.startswith("~$"):
                    pass
                    # absfn = os.path.join(dirpath, dfn)
                    # print("remove:", absfn)
                    # os.remove(absfn)
                elif dfn.lower().endswith(".doc"):
                    cur[1].append(dfn)
            li.append(cur)
            if cur[1]:
                mapping[subdir] = cur[1]
        del lw
        with open(TASK_CACHE_DIR, 'wb') as f:
            pickle.dump(li, f)
        with open(GROUP_CACHE_DIR, 'wb') as f:
            pickle.dump(mapping, f)
    else:
        with open(TASK_CACHE_DIR, 'rb') as f:
            li = pickle.load(f)
    print(len(li))

    mgr = mp.Manager()
    q = mgr.Queue()
    cur = FROM
    cursor = 0
    proc = mp.Process(target=save_as_docx, args=(cur, TO, STEP, False, 0, q))
    proc.start()
    while 1:
        try:
            res = q.get(block=True, timeout=TIMEOUT)
            if res is None:
                break
            elif isinstance(res, tuple):
                cur, cursor = res

        except Empty:
            proc.kill()
            proc.join()
            kill_word()
            subdir, filenames = li[cur]
            absfn = os.path.join(SOURCE_DIR, subdir, filenames[cursor])
            with open(err_path(absfn), 'w') as f:
                pass
            print('kill at task:', cur, cursor, absfn)
            cursor += 1
            proc = mp.Process(target=save_as_docx, args=(cur, TO, STEP, True, cursor, q))
            proc.start()



if __name__ == '__main__':
    entrance()