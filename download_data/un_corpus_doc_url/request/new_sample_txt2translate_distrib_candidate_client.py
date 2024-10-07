import os
# os.environ['ARGOS_DEVICE_TYPE'] = 'cuda' # 如果使用cuda取消注释这两行
from datetime import datetime
from typing import List
import argostranslate.translate
import argostranslate.package
import gc

import time
import requests

API = 'http://127.0.0.1:29999'
INSTALLED = {}

def get_or_install_translator(_from = 'fr', _to = 'en'):
    if tr := INSTALLED.get((_from, _to), None):
        return tr
    try:
        tr = argostranslate.translate.get_translation_from_codes(_from, _to)
        INSTALLED[(_from, _to)] = tr
        return tr
    except Exception as e:
        print(e, '\nattempt to install package...')
    # 经测试开系统代理下包可行
    # installed = argostranslate.package.get_installed_packages()
    # print(installed)
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    # print(available_packages)
    for i in filter(lambda x: x.from_code == _from and x.to_code == _to, available_packages):
        print('install', i)
        i.install()
    INSTALLED[(_from, _to)] = argostranslate.translate.get_translation_from_codes(_from, _to)
    return INSTALLED[(_from, _to)]

def translate(text: List[str], tr):
    translation = []
    for para in text:
        translation.append(tr.translate(para.replace('\n', ' ')))
    return translation

if __name__ == '__main__':
    allow_compress = {'accept-encoding':'gzip, deflate, br'}
    while 1:
        while 1:
            try:
                task = requests.get(API + '/?ver=1', headers=allow_compress, timeout=30).json()
                break
            except Exception as e:
                print(e)
                time.sleep(5)
        src, dst = task['src'], task['dst']
        tr = get_or_install_translator(src, dst)
        begin = datetime.now()
        task_len = len(task['data'])
        print(begin, 'got', task['taskid'], task_len)
        buf = translate(task['data'], tr)
        end = datetime.now()
        print(end, task['taskid'], 'seconds per line:', (end - begin).total_seconds() / (task_len + 1e-3))
        # print(buf)
        while 1:
            try:
                requests.post(API + '/upl', json={
                    'taskid': task['taskid'],
                    'client': 'argostranslate',
                    'src': src,
                    'dst': dst,
                    'out': buf
                }, headers=allow_compress, timeout=30)
                gc.collect()
                break
            except Exception as e:
                print(e)
                time.sleep(5)

