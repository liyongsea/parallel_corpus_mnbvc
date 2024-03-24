"""
由于其它软件，如LibreOffice转doc为docx的乱码率太高
本步需要一台装有Windows的机器（虚拟机环境亦可，而且利用多核应该考虑多虚拟机并行执行），并且装有Office
采用COM方式调用WORD进行另存为

本脚本假设用户使用的是中文语言环境的WORD，否则需要改动一些pywinauto的字符串搜索依据

docx转文本需要系统上装有pandoc，并且写入环境变量，即，pandoc应该能够直接命令行调用
"""

import hashlib
import json
from queue import Empty
import os
import re
import multiprocessing as mp
import datetime
import shutil
import time

import psutil
from pywinauto import Application # pywinauto
import win32com.client as win32
from win32com.client import constants
import datasets

import const

workdir = const.CONVERT_DOCX_CACHE_DIR
workdir.mkdir(exist_ok=True)
WINWORD_EXE = const.WINWORD_EXE

TEMP_DOC = str((workdir / 'temp.doc').absolute())
TEMP_DOC_LOCKFILE = str((workdir / '~$temp.doc').absolute())
TEMP_DOCX = str((workdir / 'temp.docx').absolute())
TEMP_DOCX_LOCKFILE = str((workdir / '~$temp.docx').absolute())


INPUT_DIR = const.DOWNLOAD_DOC_CACHE_DIR / 'doc'

ERR_DOCX_DIR = workdir / 'err'
ERR_DOCX_DIR.mkdir(exist_ok=True)

OUT_DOCX_DIR = workdir / 'docx'
OUT_DOCX_DIR.mkdir(exist_ok=True)

OUT_TEXT_DIR = const.CONVERT_TEXT_CACHE_DIR
OUT_TEXT_DIR.mkdir(exist_ok=True)

OUT_DATASET_DIR = const.CONVERT_DATASET_CACHE_DIR
FILEWISE_JSONL_DIR = const.FILEWISE_JSONL_OUTPUT_DIR
FILEWISE_JSONL_DIR.mkdir(exist_ok=True)

DOCX2TEXT_WORKERS = 8

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

def docx2txt_worker(q: mp.Queue):
    while 1:
        ipath, opath = q.get()
        if ipath is None:
            return
        if not os.path.exists(opath):
            r = os.system(f"pandoc -i {ipath} -t plain -o {opath} --strip-comments")
            # print('done', outp)
        else:
            pass
            # print('skip', outp)
    # print(r.read())

if __name__ == '__main__':
    kill_word()
    mgr = mp.Manager()
    q = mgr.Queue()
    qtask = mgr.Queue()

    close_window_tries = 0

    todo = set()
    for rec in os.listdir(INPUT_DIR):
        if rec.startswith('~$'):
            continue
        todo.add(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(OUT_DOCX_DIR):
        todo.remove(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(ERR_DOCX_DIR):
        todo.remove(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(INPUT_DIR):
        fn = INPUT_DIR / rec
        if re.sub(r'\.\w+$', '', rec) not in todo:
            continue
        with open(fn, 'rb') as f:
            cont = f.read()
        print(fn)
        qtask.put((rec, cont))
    print(len(todo))
    p = mp.Process(target=save_as_docx, args=(q, qtask))
    p.start()
    prvtask = None

    print('qsiz:', qtask.qsize())
    print('todo len:', len(todo))
    while len(todo) > 0:
        try:
            status, *args = q.get(timeout=40)
            close_window_tries = 0
            if status == ACCEPTED:
                prvtask = args[0]
            elif status == OK:
                tout = OUT_DOCX_DIR / re.sub(r'\.\w+$', '.docx', args[0])
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
                tout.parent.mkdir(exist_ok=True)
                with open(tout, 'wb') as f:
                    f.write(args[1])
            elif status == ERR:
                terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', args[0])
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
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
                terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', prvtask)
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
                terr.parent.mkdir(exist_ok=True)
                with open(terr, 'w') as f:
                    pass
                print('timeout submit error:', prvtask)
            else:
                print('catch error without report:', prvtask)
            p = mp.Process(target=save_as_docx, args=(q, qtask))
            p.start()

    p.kill()
    p.join()
    kill_word()
    qd2t = mp.Queue()
    ps = [
        mp.Process(target=docx2txt_worker, args=(qd2t,)) for _ in range(DOCX2TEXT_WORKERS)
    ]

    for x in ps:
        x.start()

    for rec in os.listdir(OUT_DOCX_DIR):
        if not (OUT_TEXT_DIR / re.sub(r'\.\w+$', '.txt', rec)).exists():
            qd2t.put((
                (OUT_DOCX_DIR / rec).absolute(),
                (OUT_TEXT_DIR / re.sub(r'\.\w+$', '.txt', rec)).absolute(),
            ))

    for x in ps:
        qd2t.put((None, None))
    
    for x in ps:
        x.join()


    filename_mapping = {
        'es': 'es',
        'ru': 'ru',
        'fr': 'fr',
        'de': 'de',
        'ar': 'ar',
        'zh': 'zh',
        'en': 'en',
        'ot': 'de', # other先默认是德语
    }

    for i in os.listdir(OUT_TEXT_DIR):
        print(i)

    def dataset_generator():
        json_info2langs = {}
        json_info2ds_row = {}
        for rec in os.listdir(OUT_TEXT_DIR): # sample: 2023-2023_1-8=ar.txt
            json_info, lang = rec.removesuffix('.txt').split('=')
            json_info2langs.setdefault(json_info, set()).add(lang)
        
            json_fn, idx = json_info.rsplit('-', 1)
            with open(const.DOWNLOAD_FILELIST_CACHE_DIR / f'{json_fn}.json', 'r') as f:
                data = json.load(f)
                json_info2ds_row[json_info] = {
                    'ar': '',
                    'zh': '',
                    'en': '',
                    'fr': '',
                    'ru': '',
                    'es': '',
                    'de': '',
                    'inner_id': json_info, # 本批脚本自用id
                    'published': data['docs'][int(idx)]['Publication Date'],
                    'symbol': data['docs'][int(idx)]['symbol'],
                    'record': data['docs'][int(idx)]['id'],
                }

        for rec in os.listdir(OUT_TEXT_DIR): # sample: 2023-2023_1-8=ar.txt
            json_info, lang = rec.removesuffix('.txt').split('=')
            json_info2langs[json_info].discard(lang)

            lang = filename_mapping[lang]
            with open(OUT_TEXT_DIR / rec, 'r', encoding='utf-8') as f:
                json_info2ds_row[json_info][lang] = f.read()

            if not json_info2langs[json_info]:
                yield json_info2ds_row.pop(json_info)
    
    dataset = datasets.Dataset.from_generator(dataset_generator)

    shutil.rmtree(OUT_DATASET_DIR, ignore_errors=True)
    dataset.save_to_disk(OUT_DATASET_DIR)

    def save_jsonl(row):
        fn = row['record']
        template = {
            '文件名': fn,
            '是否待查文件': False,
            '是否重复文件': False,
            '段落数': 1,
            '去重段落数': 0,
            '低质量段落数': 0,
            '段落': {
                '行号': 1,
                '是否重复': False,
                '是否跨文件重复': False,
                'zh_text_md5': hashlib.md5(row['zh'].encode('utf-8')).hexdigest(),
                'zh_text': row['zh'],
                'en_text': row['en'],
                'ar_text': row['ar'],
                'nl_text': '',
                'de_text': row['de'],
                'eo_text': '',
                'fr_text': row['fr'],
                'he_text': '',
                'it_text': '',
                'ja_text': '',
                'pt_text': '',
                'ru_text': row['ru'],
                'es_text': row['es'],
                'sv_text': '',
                'ko_text': '',
                'th_text': '',
                'other1_text': '',
                'other2_text': '',
                '拓展字段': r'{}',
                '时间': datetime.datetime.now().strftime("%Y%m%d")
            },
            '拓展字段': r'{}',
            '时间': datetime.datetime.now().strftime("%Y%m%d")
        }
        with open(FILEWISE_JSONL_DIR / (row['inner_id'] + '.jsonl'), 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False)
    dataset.map(save_jsonl)