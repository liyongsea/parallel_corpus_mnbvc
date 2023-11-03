from datetime import datetime
from typing import List
import re
import argostranslate.translate
import argostranslate.package

import time
import requests

API = 'http://4kr.top:7098'
# API = 'http://127.0.0.1:29999'
INSTALLED = {}
# NEED_TARGETS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')

def get_or_install_translator(_from = 'fr', _to = 'en'):
    if tr := INSTALLED.get((_from, _to), None):
        return tr
    try:
        tr = argostranslate.translate.get_translation_from_codes(_from, _to)
        INSTALLED[(_from, _to)] = tr
        return tr
    except Exception as e:
        print(e, 'attemp to install...')
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
        if not re.search('[A-Za-z]+', para):
            translation.append(para)
        else:
            try:
                translation.append(tr.translate(para))
            except Exception as e:
                print(e)
                translation.append(para)
    return translation

if __name__ == '__main__':
    allow_compress = {'accept-encoding':'gzip, deflate, br'}
    # os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'
    while 1:
        while 1:
            try:
                task = requests.get(API, headers=allow_compress).json()
                break
            except Exception as e:
                print(e)
                time.sleep(5)
        print('got', task['taskid'])
        src, dst = task['src'], task['dst']
        tr = get_or_install_translator(src, dst)
        buf = []
        for tid, text in enumerate(task['data']):
            begin = datetime.now()
            buf.append(translate(text, tr))
            print(tid, len(text), 'seconds per line:', (datetime.now() - begin).total_seconds() / (len(text) + 1e-3))
        # print(buf)
        while 1:
            try:
                requests.post(API + '/upl', json={
                    'taskid': task['taskid'],
                    'client': 'argostranslate',
                    'out': buf
                }, headers=allow_compress)
                break
            except Exception as e:
                print(e)
                time.sleep(5)

