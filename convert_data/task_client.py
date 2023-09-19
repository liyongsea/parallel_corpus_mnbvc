from queue import Empty
import os
import win32com.client as win32
from win32com.client import constants
import multiprocessing as mp
import psutil
import datetime
import requests

API_HOST = 'http://localhost:29999'
TEMP_DOC = 'temp.doc'
TEMP_DOC_LOCKFILE = '~$temp.doc'
TEMP_DOCX = 'temp.docx'
TEMP_DOCX_LOCKFILE = '~$temp.docx'

def save_as_docx(qresult: mp.Queue):
    last_time = datetime.datetime.now()
    word = win32.gencache.EnsureDispatch('Word.Application')
    session = requests.session()
    absdoc = os.path.abspath(TEMP_DOC)
    absdocx = os.path.abspath(TEMP_DOCX)

    while 1:
        print('get task', API_HOST + '/')
        task_resp = session.get(API_HOST + '/')

        tid = task_resp.headers['taskid']
        print('task_resp', tid, len(task_resp.content))
        qresult.put(tid)
        with open(absdoc, 'wb') as f:
            f.write(task_resp.content)
            f.truncate()

        if os.path.exists(absdocx):
            os.remove(absdocx)
        if os.path.exists(TEMP_DOC_LOCKFILE):
            os.remove(TEMP_DOC_LOCKFILE)

        doc = None
        try:
            doc = word.Documents.Open(absdoc)
            doc.SaveAs(absdocx, FileFormat=constants.wdFormatXMLDocument)
            doc.Close(False)
            doc = None
            resp = session.post(API_HOST + '/upl', files={'fil': open(absdocx, 'rb')}, headers={'taskid': tid})
        except Exception as e:
            print(e)
            resp = session.post(API_HOST + '/uplerr', headers={'taskid': tid})
            if doc is not None:
                doc.Close(False)
                doc = None
        curr_time = datetime.datetime.now()
        print(tid, (curr_time - last_time).total_seconds(), resp.text)
        last_time = curr_time
    qresult.put(None)

def kill_word():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            p = psutil.Process(pid)
            p.kill()


if __name__ == '__main__':
    mgr = mp.Manager()
    q = mgr.Queue()
    p = mp.Process(target=save_as_docx, args=(q,))
    p.start()
    prvtask = None
    while 1:
        try:
            prvtask = q.get(timeout=10)
            print(prvtask)
        except Empty:
            p.kill()
            p.join()
            kill_word()
            if prvtask is not None:
                requests.post(API_HOST + '/uplerr', data={'task': prvtask})
            print('error:', prvtask)
            p = mp.Process(target=save_as_docx, args=(q,))
            p.start()