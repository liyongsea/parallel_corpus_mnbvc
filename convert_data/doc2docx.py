import re
import os
import win32com.client as win32
from win32com.client import constants
from pathlib import Path
import shutil
import multiprocessing as mp
import psutil

# import timeout_decorator # windows下不可用，缺少系统信号

WORKER_CNT = 8

ERR_LOG_DIR = r'E:\motrixDL\baiduyun\MNBVC\err'
SOURCE_DIR = r'E:\motrixDL\baiduyun\MNBVC\MNBVC—UN文件'
SAVED_DIR = r'E:\motrixDL\baiduyun\MNBVC\docxoutput'

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

# @timeout_decorator.timeout(10)
def save_as_docx(file_location):
    doc = None
    word = None
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
        word.Quit()
        word = None
    except:
        with open(err_path(file_abs), 'w') as f:
            pass
        if doc is not None:
            doc.Close(False)
        if word is not None:
            word.Quit()



def task_wrapper(q1: mp.Queue):
    while 1:
        absfn = q1.get()
        if absfn is None:
            return
        proc = mp.Process(target=save_as_docx, args=(absfn,))
        proc.start()
        proc.join(timeout=10)
        if proc.is_alive():
            proc.terminate()
            proc.join()
            with open(err_path(absfn), 'w') as f:
                pass
        # save_as_docx(absfn)

if __name__ == '__main__':
    # mng = mp.Manager()
    # q1 = mng.Queue(maxsize=WORKER_CNT)
    # consumers = [
    #     mp.Process(target=task_wrapper,
    #         args=(q1,)
    #     ) for _ in range(WORKER_CNT)
    # ]
    # for x in consumers: x.start()

    # 创建输出目录的文件夹
    Path(SAVED_DIR).mkdir(exist_ok=True)

    li = list(os.walk(SOURCE_DIR))
    print(len(li))

    task_slice = li

    for idx, (dirpath, dirnames, filenames) in enumerate(task_slice):
        print(idx, len(task_slice), filenames)
        for dfn in filenames:
            absfn = os.path.join(dirpath, dfn)
            if dfn.startswith("~$"):
                print("remove:", absfn)
                os.remove(absfn)
            elif dfn.lower().endswith(".doc"):
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