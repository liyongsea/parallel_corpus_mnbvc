# from https://github.com/bear01/Multi_API_translation_Webcrawler/blob/master/API/Wc_Bing.py
import urllib.request
import urllib.parse
import requests
import traceback
import re


cred_pat = re.compile(r"""var params_AbusePreventionHelper = \[(\d+),"([\w\-]+)",(\d+)\];""")
session = requests.session()
session.headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
    'accept-encoding': 'gzip, deflate, br',
}
translator_url = 'https://cn.bing.com/translator'
translate_url = 'https://cn.bing.com/ttranslatev3?isVertical=1&&IG=C14796C62F544E239E123D9292F50339&IID=translator.5026'
def translate(from_lan = 'en', to_lan = 'zh-Hans', content=''):
    r = session.get(translator_url)
    # print(r.text)
    rt = r.text
    timestamp_key, token, valid_time = cred_pat.search(rt).groups()
    timestamp_key = int(timestamp_key)
    valid_time = int(valid_time)
    resp = session.post(translate_url, data={
        'fromLang': from_lan,
        'to': to_lan,
        'key': timestamp_key,
        'token': token,
        'text': content,
    })
    print(resp.text)
    return ''.join(map(lambda x: x['text'], resp.json()[0]['translations']))
    

if __name__ == "__main__":
    print(translate('en', 'zh-Hans', '''Who am i'''))