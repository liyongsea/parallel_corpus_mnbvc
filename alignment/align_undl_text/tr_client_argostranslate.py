from typing import List
import re
import argostranslate.package
import argostranslate.translate
import os
import requests

API = 'http://localhost:29999'

def translate(text: List[str]):
    translation = []
    for para in text:
        if not re.search('[A-Za-z]+', para):
            translation.append(para)
        else:
            try:
                translation.append(argostranslate.translate.translate(para, 'en', 'zh'))
            except Exception as e:
                print(e)
                translation.append(para)
    return translation

if __name__ == '__main__':
    # os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'
    while 1:
        task = requests.get(API).json()
        print('got', task['taskid'])
        buf = []
        for tid, text in enumerate(task['data']):
            print(tid, len(text))
            buf.append(translate(text))
        # print(buf)
        requests.post(API + '/upl', json={
            'taskid': task['taskid'],
            'client': 'argostranslate',
            'out': buf
        })