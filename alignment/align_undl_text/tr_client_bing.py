from typing import List
import re
import time
import requests

API = 'http://localhost:29999'
CD = 20
CHUNK_CHAR = 768
proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

class Bing:
    timestamp_key = None
    token = None
    valid_time = None
    session = requests.session()
    session.headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
        'accept-encoding': 'gzip, deflate, br',
    }
    translator_url = 'https://www.bing.com/translator'
    translate_url = 'https://www.bing.com/ttranslatev3?isVertical=1&&IG=C14796C62F544E239E123D9292F50339&IID=translator.5026'
    cred_pat = re.compile(r"""var params_AbusePreventionHelper = \[(\d+),"([\w\-]+)",(\d+)\];""")
    @classmethod
    def get_cred(cls):
        if cls.timestamp_key is None or cls.timestamp_key + cls.valid_time < int(time.time() * 1000):
            r = cls.session.get(cls.translator_url, proxies=proxies)
            timestamp_key, cls.token, valid_time = cls.cred_pat.search(r.text).groups()
            cls.timestamp_key = int(timestamp_key)
            cls.valid_time = int(valid_time)
        return cls.timestamp_key, cls.token
    
    @classmethod
    def translate(cls, _from, _to, _text):
        buf = []
        for i in range(0, len(_text), CHUNK_CHAR):
            buf.append(cls.trans(_from, _to, _text[i:i+CHUNK_CHAR]))
        return ''.join(buf)

    @classmethod
    def trans(cls, _from, _to, _text):
        while 1:
            cls.get_cred()
            resp = cls.session.post(cls.translate_url, data={
                'fromLang': _from,
                'to': _to,
                'key': cls.timestamp_key,
                'token': cls.token,
                'text': _text,
            }, proxies=proxies)
            if resp.status_code == 200:
                j = resp.json()
                try:
                    return ''.join(map(lambda x: x['text'], j[0]['translations']))
                except Exception as e:
                    print(e, j)
                    time.sleep(CD)
            else:
                print(resp.status_code)
                time.sleep(CD)

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

def translate(text: List[str]):
    translation = []
    for para in text:
        if not re.search('[A-Za-z]+', para):
            translation.append(para)
        else:
            translation.append(Bing.trans(_from='en', _to='zh-Hans', _text=para))
            print(translation[-1])
    return translation

if __name__ == '__main__':
    # use_proxy()
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
            'client': 'bing_free',
            'out': buf
        })