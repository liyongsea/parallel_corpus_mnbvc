import argparse
import re
import logging as log
import csv
from xml.dom.minidom import parseString
from concurrent.futures import ProcessPoolExecutor

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

log.basicConfig(level=log.INFO, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')


class SessionManager:
    """单例模式的请求会话管理"""
    __session = requests.session()
    __session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69'}
    adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
    __session.mount('https://', adapter)
    __session.mount('http://', adapter)

    def __init__(self):
        pass

    @classmethod
    def instance(cls) -> requests.Session:
        return cls.__session


def task(url):
    session = SessionManager.instance()
    res = session.get(url)
    soup = BeautifulSoup(res.text, 'lxml')
    # 正文
    text = "\n".join([ct.text for ct in soup.select('main div.row p')]).strip()
    # 英文url
    en_url = soup.select_one('#language-switch option[lang="en-US"]').attrs['value']

    en_res = session.get(en_url)
    en_soup = BeautifulSoup(en_res.text, 'html.parser')
    en_text = "\n".join([et.text for et in en_soup.select('main div.row p p')]).strip()

    # 过滤空字符串
    if text == "" or en_text == "":
        return None

    return text, en_text


if __name__ == '__main__':
    log.info(f'install sitemap...')
    index_sitemap = SessionManager.instance().get('https://china.usembassy-china.org.cn/sitemap_index.xml')
    dom = parseString(index_sitemap.content.decode('utf-8'))
    
    # 帖子sitemap-url集合
    post_sitemap_urls = []
    for el in dom.documentElement.getElementsByTagName('loc'):
        url = el.firstChild.nodeValue
        if 'post-sitemap' in url:
            post_sitemap_urls.append(url)

    # 中文帖子的url集合
    post_zh_urls = set()
    for post_sitemap in post_sitemap_urls:
        url_sitemap = SessionManager.instance().get(post_sitemap)
        urlset_dom = parseString(url_sitemap.content.decode('utf-8'))

        for el in urlset_dom.documentElement.getElementsByTagName('loc'):
            post_url = el.firstChild.nodeValue
            # 筛出中文的链接
            if re.match(r'https://china.usembassy-china.org.cn/zh/.*', post_url):
                post_zh_urls.add(post_url)

    log.info(f'URL Total: {len(post_zh_urls)}')
    
    # TODO: debug，减少数据量
    post_zh_urls = list(post_zh_urls)[:2]

    parser = argparse.ArgumentParser(description='美国大使馆数据下载')
    parser.add_argument('--downloaded_data_file', default="data.csv", help='输出csv的文件名')

    args = parser.parse_args()

    # 分发任务
    # 由于该站频繁访问会给拦截，所以跑慢点吧
    with ProcessPoolExecutor(max_workers=3) as pool:
        result = pool.map(task, post_zh_urls)
        with open(args.downloaded_data_file, 'w', encoding='utf-8') as csv_fp:
            csv_obj = csv.writer(csv_fp)
            csv_obj.writerow(('zh', 'en'))
            progress = tqdm(result, total=len(post_zh_urls))
            for o in progress:
                if o:
                    csv_obj.writerow(o)
                    csv_fp.flush()
