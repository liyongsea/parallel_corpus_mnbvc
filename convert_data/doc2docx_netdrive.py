import re
import os
import win32com.client as win32
from win32com.client import constants
from pathlib import Path
import shutil
import multiprocessing as mp
import psutil
import pickle

BASE_DIR = r'E:\doc2docxWD'
ERR_LOG_DIR = BASE_DIR + r'\err'
SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'
SAVED_DIR = BASE_DIR + r'\docxoutput'

TASK_CACHE_DIR = BASE_DIR + r'\oswalkcache.pkl'
GROUP_CACHE_DIR = BASE_DIR + r'\dirmappingcache.pkl'

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

def save_as_docx(file_location):
    doc = None
    try:
        # 获取文件的绝对路径，在Windows下调用客户端时必须使用绝对路径，否则无法打开
        file_abs = os.path.abspath(file_location)

        # 将文件扩展名更改为.docx
        new_file_abs = saved_path(file_abs)

        if os.path.exists(new_file_abs):
            return
        
        if ".docx" in file_abs:
            # 也可以使用copy
            shutil.move(file_abs, new_file_abs)
            return

        # 创建一个用于打开Word文档的客户端对象，需要下载WPS或者Office(Microsoft Word)
        word = win32.gencache.EnsureDispatch('Word.Application')

        # 打开指定路径的文档
        doc = word.Documents.Open(file_abs)
        doc.Activate()
        

        # 将当前活动文档保存为.docx格式
        word.ActiveDocument.SaveAs(new_file_abs, FileFormat=constants.wdFormatXMLDocument)
        
        # 关闭打开的文档资源
        doc.Close(False)
        doc = None
    except:
        with open(err_path(file_abs), 'w') as f:
            pass
        if doc is not None:
            doc.Close(False)



if __name__ == '__main__':
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

    begins_from = 130000
    task_slice = li[begins_from:]

    for idx, (subdir, filenames) in enumerate(task_slice):
        # print(len(li) - 1 - idx, len(task_slice), filenames)
        print(begins_from + idx, len(li), filenames)
        for dfn in filenames:
            absfn = os.path.join(SOURCE_DIR, subdir, dfn)
            if dfn.lower().endswith(".doc"):
                if not os.path.exists(saved_path(absfn)) and not os.path.exists(err_path(absfn)):
                    # q1.put(absfn)
                    proc = mp.Process(target=save_as_docx, args=(absfn,))
                    proc.start()
                    proc.join(timeout=10)
                    if proc.is_alive():
                        proc.terminate()
                        proc.join()
                        with open(err_path(absfn), 'w') as f:
                            pass
                        for process in psutil.process_iter(attrs=['pid', 'name']):
                            if process.info['name'] == "WINWORD.EXE":
                                pid = process.info['pid']
                                p = psutil.Process(pid)
                                # p.terminate()  # 终止进程
                                p.kill()
                                print('killed', pid, process.info['name'])
    # for _ in consumers: q1.put(None)
    # for x in consumers: x.join()