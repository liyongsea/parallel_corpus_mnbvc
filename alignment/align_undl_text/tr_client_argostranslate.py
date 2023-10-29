from typing import List
import re
import argostranslate.package
import argostranslate.translate
import time
import requests

API = 'http://4kr.top:7098'
# API = 'http://127.0.0.1:29999'
INSTALLED = set()
# NEED_TARGETS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')

def install_translator(_from = 'fr', _to = 'en'):
    if (_from, _to) in INSTALLED:
        return
    # 经测试开系统代理下包可行
    installed = argostranslate.package.get_installed_packages()
    # print(installed)
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    # print(available_packages)
    for i in filter(lambda x: x.from_code == _from and x.to_code == _to, available_packages):
        if i in installed:
            # print('skip', i)
            INSTALLED.add((_from, _to))
            continue

        print('install', i)
        i.install()
        INSTALLED.add((_from, _to))

def translate(text: List[str], src, dst):
    translation = []
    for para in text:
        if not re.search('[A-Za-z]+', para):
            translation.append(para)
        else:
            try:
                translation.append(argostranslate.translate.translate(para, src, dst))
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
        install_translator(src, dst)
        buf = []
        for tid, text in enumerate(task['data']):
            print(tid, len(text))
            buf.append(translate(text, src, dst))
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

