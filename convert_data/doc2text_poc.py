"""
由于其它软件，如LibreOffice转doc为docx的乱码率太高
本步需要一台装有Windows的机器（虚拟机环境亦可，而且利用多核应该考虑多虚拟机并行执行），并且装有Office
采用COM方式调用WORD进行另存为

本脚本假设用户使用的是中文语言环境的WORD，否则需要改动一些pywinauto的字符串搜索依据
"""

from queue import Empty
import os
import re
import traceback
import win32com.client as win32
from win32com.client import constants
import multiprocessing as mp
import psutil
import datetime
import base64
import pywinauto
import time
from pywinauto import Application
from pathlib import Path


temppath = Path('un_convert_temp')
temppath.mkdir(exist_ok=True)

TEMP_DOC = str((temppath / 'temp.doc').absolute())
TEMP_DOC_LOCKFILE = str((temppath / '~$temp.doc').absolute())
TEMP_DOCX = str((temppath / 'temp.docx').absolute())
TEMP_DOCX_LOCKFILE = str((temppath / '~$temp.docx').absolute())

WINWORD_EXE = r'C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE'

INPUT_DIR = Path(r'un_crawl_result')

ERR_DOCX_DIR = Path('un_convert_err')
ERR_DOCX_DIR.mkdir(exist_ok=True)

OUT_DOCX_DIR = Path('un_convert_result')
OUT_DOCX_DIR.mkdir(exist_ok=True)

ACCEPTED = 201
OK = 200
ERR = 500

def eliminate_top_window(app: Application):
    try:
        dialog = app.top_window()
        if dialog.texts() == ['显示修复']:
            dialog.close()
            return True

        for i in dialog.children():
            if "安全模式中启动" in ''.join(i.texts()):
                dialog.N.click()
                return True
            if "是否仍要打开它" in ''.join(i.texts()):
                dialog.Y.click()
                return True
    except RuntimeError as e:
        pass
        # traceback.print_exc()
    return False

def close_top_window(): # 很慢，所以超时才调用
    pids = scan_word()
    app = Application().connect(process=pids[-1])
    while eliminate_top_window(app):
        print('detected top window, closed')
        time.sleep(0.5)


def save_as_docx(qresult: mp.Queue, qtask: mp.Queue):
    """易错工作队列，随时需要处理被杀掉重启的情况"""
    last_time = datetime.datetime.now()
    word = win32.gencache.EnsureDispatch('Word.Application')
    absdoc = os.path.abspath(TEMP_DOC)
    absdocx = os.path.abspath(TEMP_DOCX)

    while 1:
        tid: str
        cont: bytes
        tid, cont = qtask.get()

        qresult.put((ACCEPTED, tid))

        if os.path.exists(TEMP_DOC_LOCKFILE):
            os.remove(TEMP_DOC_LOCKFILE)

        if os.path.exists(TEMP_DOCX_LOCKFILE):
            os.remove(TEMP_DOCX_LOCKFILE)

        try:
            with open(absdoc, 'wb') as f:
                f.write(cont)
                f.truncate()
        except PermissionError:
            print('detected permission error, kill word')
            time.sleep(3)
            kill_word()
            with open(absdoc, 'wb') as f:
                f.write(cont)
                f.truncate()
            word = win32.gencache.EnsureDispatch('Word.Application')

        if os.path.exists(absdocx):
            try:
                os.remove(absdocx)
            except PermissionError:
                print('detected permission error, kill word')
                time.sleep(3)
                kill_word()
                os.remove(absdocx)
                word = win32.gencache.EnsureDispatch('Word.Application')

        doc = None
        def post_error():
            nonlocal doc
            qresult.put((ERR, tid))
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'report error')
            if doc is not None:
                try:
                    doc.Close(False)
                except:
                    pass
                doc = None
        try:
            doc = word.Documents.Open(absdoc)
            doc.SaveAs(absdocx, FileFormat=constants.wdFormatXMLDocument)
            doc.Close(False)
            doc = None
            if os.stat(absdocx).st_size == 0:
                raise KeyError('空文件，视为错误')
            with open(absdocx, 'rb') as f:
                ok_res = f.read()
            qresult.put((OK, tid, ok_res))
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'submit done', tid)
        except win32.pywintypes.com_error as e:
            if 'RPC 服务器不可用。' in str(e):
                print('捕获【RPC 服务器不可用。】，重启word')
                kill_word()
                word = win32.gencache.EnsureDispatch('Word.Application')
                time.sleep(1)
            else:
                print(type(e), e)
                post_error()
        except Exception as e:
            print(type(e), e)
            post_error()
        last_time = datetime.datetime.now()
    qresult.put(None)

def scan_word():
    li = []
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            li.append(pid)
    return li

def kill_word():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            p = psutil.Process(pid)
            p.kill()


if __name__ == '__main__':
    kill_word()
    mgr = mp.Manager()
    q = mgr.Queue()
    qtask = mgr.Queue()



    close_window_tries = 0

    todo = set()
    for rec in os.listdir(INPUT_DIR):
        for fn in os.listdir(INPUT_DIR / rec):
            todo.add(rec + '/' + re.sub(r'\.\w+$', '', fn))

    for rec in os.listdir(OUT_DOCX_DIR):
        for fn in os.listdir(OUT_DOCX_DIR / rec):
            todo.remove(rec + '/' + re.sub(r'\.\w+$', '', fn))

    for rec in os.listdir(ERR_DOCX_DIR):
        for fn in os.listdir(ERR_DOCX_DIR / rec):
            todo.remove(rec + '/' + re.sub(r'\.\w+$', '', fn))

    for rec in os.listdir(INPUT_DIR):
        for fn in os.listdir(INPUT_DIR / rec):
            if rec + '/' + re.sub(r'\.\w+$', '', fn) not in todo:
                continue
            with open(INPUT_DIR / rec / fn, 'rb') as f:
                cont = f.read()
            print(rec + '/' + fn)
            qtask.put((rec + '/' + fn, cont))
    print(len(todo))
    p = mp.Process(target=save_as_docx, args=(q, qtask))
    p.start()
    prvtask = None

    while qtask.qsize() > 0:
        try:
            status, *args = q.get(timeout=20)
            close_window_tries = 0
            if status == ACCEPTED:
                prvtask = args[0]
            elif status == OK:
                tout = OUT_DOCX_DIR / re.sub(r'\.\w+$', '.docx', args[0])
                tout.parent.mkdir(exist_ok=True)
                with open(tout, 'wb') as f:
                    f.write(args[1])
            elif status == ERR:
                terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', args[0])
                terr.parent.mkdir(exist_ok=True)
                with open(terr, 'w') as f:
                    pass
        except Empty:
            if close_window_tries < 2:
                close_window_tries += 1
                close_top_window()
                continue
            p.kill()
            p.join()
            kill_word()
            if prvtask is not None:
                while True:
                    try:
                        terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', prvtask)
                        terr.parent.mkdir(exist_ok=True)
                        with open(terr, 'w') as f:
                            pass
                        print('timeout submit error:', prvtask)
                        break
                    except Exception as e:
                        print(type(e), e, 'network error, retry')
                        time.sleep(40)
            else:
                print('catch error without report:', prvtask)
            p = mp.Process(target=save_as_docx, args=(q, qtask))
            p.start()