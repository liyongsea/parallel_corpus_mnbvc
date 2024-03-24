from math import ceil
import requests

import const

FROM_YEAR = 2023 # 输入参数可以改这俩，建议是写一样的，其它文件的常量不要乱动
TO_YEAR = 2023

fl_cache_dir =  const.DOWNLOAD_FILELIST_CACHE_DIR # 我不建议改const里面预定义的目录，如果确实需要改最好是找一个固定的空文件夹把WORKDIR换掉
print('cache file stored in:', fl_cache_dir.absolute())
fl_cache_dir.mkdir(exist_ok=True)

def save_cache(page, data):
    with open(fl_cache_dir / f'{FROM_YEAR}-{TO_YEAR}_{page}.json', 'w') as f:
        f.write(data)

def is_cache_exists(page):
    return (fl_cache_dir / f'{FROM_YEAR}-{TO_YEAR}_{page}.json').exists()

session = requests.session()
headers = {
    "Accept":"*/*",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"zh-CN,zh;q=0.9",
    "Cache-Control":"public, max-age=0",
    "Connection":"keep-alive",
    "Content-Type":"application/json",
    "DNT":"1",
    "Host":"search.un.org",
    "Pragma":"no-cache",
    "Referer":"https://search.un.org/search?sort=ascending&collection=ods&currentPageNumber=1&fromYear=2018&q=*&row=100&toYear=2018",
    "Sec-Fetch-Dest":"empty",
    "Sec-Fetch-Mode":"cors",
    "Sec-Fetch-Site":"same-origin",
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
    "withCredentials":"true",
}
session.headers.update(headers)

i = 1
mLen = 135 # 随意设置的初始值
td = 13416 # 随意设置的初始值

while i < mLen + 1:
    if not is_cache_exists(i):
        nexturl = f'https://search.un.org/api/search?collection=ods&currentPageNumber={i}&fromYear={FROM_YEAR}&q=*&row=100&sort=ascending&toYear={TO_YEAR}&mLen={mLen}&td={td}'
        for retry in range(3):
            resp = session.get(nexturl)
            print(i, resp)
            if resp.status_code == 200:
                j = resp.json()
                td = j['numberDocsFound']
                mLen = ceil(td / 100)
                if i > mLen:
                    print('out of range, done.')
                    print(j)
                    exit(0)
                save_cache(i, resp.text)
                session.headers['X-CSRF-Token'] = j['token']
                break
            else:
                print(resp, 'retry:', retry)
                if retry == 2:
                    print(resp.headers)
                    print(resp.text)
                    print('!!!!!ERROR!!!!!')
                    exit(1)
                session = requests.session()
                session.headers.update(headers)
    i += 1
