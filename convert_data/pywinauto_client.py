from queue import Empty
import os
import traceback
import win32com.client as win32
from win32com.client import constants
import multiprocessing as mp
import psutil
import datetime
import requests
import base64
import pywinauto
import time
from pywinauto import Application
# 32位机器必须使用32位python，否则组件会认错

API_HOST = 'http://localhost:29999'
TEMP_DOC = 'temp.doc'
TEMP_DOC_LOCKFILE = '~$temp.doc'
TEMP_DOCX = 'temp.docx'
TEMP_DOCX_LOCKFILE = '~$temp.docx'

WINWORD_EXE = r'C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE'
session = requests.session()
session.headers['accept-encoding'] = 'gzip'

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


def save_as_docx(qresult: mp.Queue):
    last_time = datetime.datetime.now()
    word = win32.gencache.EnsureDispatch('Word.Application')
    absdoc = os.path.abspath(TEMP_DOC)
    absdocx = os.path.abspath(TEMP_DOCX)
    request_retries = 3

    while 1:
        # print('get task', API_HOST + '/')
        while 1:
            try:
                task_resp = session.get(API_HOST + '/')
                request_retries = 3
                break
            except Exception as e:
                print(type(e), e)
                if request_retries == 0:
                    raise
                request_retries -= 1

        tid = task_resp.headers['taskid']
        # print('task_resp', tid, len(task_resp.content))
        qresult.put(tid)

        if os.path.exists(TEMP_DOC_LOCKFILE):
            os.remove(TEMP_DOC_LOCKFILE)

        if os.path.exists(TEMP_DOCX_LOCKFILE):
            os.remove(TEMP_DOCX_LOCKFILE)

        try:
            with open(absdoc, 'wb') as f:
                f.write(task_resp.content)
                f.truncate()
        except PermissionError:
            print('detected permission error, kill word')
            time.sleep(3)
            kill_word()
            with open(absdoc, 'wb') as f:
                f.write(task_resp.content)
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
            resp = session.post(API_HOST + '/uplerr', headers={'taskid': tid})
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'report error', resp.text)
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
            resp = session.post(API_HOST + '/upl', files={'fil': open(absdocx, 'rb')}, headers={'taskid': tid})
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'submit done', resp.text)
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
    p = mp.Process(target=save_as_docx, args=(q,))
    p.start()
    prvtask = None

    close_window_tries = 0

    while 1:
        try:
            prvtask = q.get(timeout=20)
            close_window_tries = 0
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
                        session.post(API_HOST + '/uplerr', data={'task': prvtask}, headers={'taskid': prvtask})
                        print('timeout submit error:', base64.b64decode(prvtask.encode()).decode())
                        break
                    except Exception as e:
                        print(type(e), e, 'network error, retry')
                        time.sleep(40)
            else:
                print('catch error without report:', base64.b64decode(prvtask.encode()).decode())
            p = mp.Process(target=save_as_docx, args=(q,))
            p.start()