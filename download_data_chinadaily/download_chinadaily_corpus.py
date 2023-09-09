import json
import os
import re
import argparse
import logging as log
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import chardet
import requests
from bs4 import BeautifulSoup

log.basicConfig(level=log.INFO, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')


class ContentProcessor:
    """对单篇Html文章解析

    Args:
        url(str): 文章的链接
    """
    def __init__(self, url):
        self.url = url
        self.session = SessionManager.get()
        self.html = self.session.get(self.url).text
        self.soup = BeautifulSoup(self.html, 'html.parser')
        self.div_content = self.soup.find('div', attrs={'id': 'Content'})
        self.title = self.soup.find('span', attrs={'class': 'main_title1'})

    def parse_text(self) -> Optional[str]:
        """解析文章正文内容"""
        if self.div_content is not None:
            return '\n'.join(self.div_content.strings)
        return None

    def get_title(self) -> Optional[str]:
        """获得文章标题"""
        try:
            return self.title.text
        except AttributeError as e:
            log.exception(self.url + e)
            return None

    def parse(self) -> Optional[dict]:
        """将中英文内容分离，最终数据格式"""
        cn = []
        en = []
        if (self.parse_text() is not None) and (self.get_title() is not None):
            for text in self.parse_text().split('\n'):
                if re.match('^[a-zA-Z0-9\s\W]+$', text):
                    en.append(text)
                else:
                    cn.append(text)
            return {self.get_title():
                {
                    'cn': char_filter('\n'.join(cn)),
                    'en': char_filter('\n'.join(en))
                }
            }
        return None


def char_filter(str):
    """过滤字符串中不需要的字符

    Args:
        str(str): 要过滤的字符串
    """
    return re.sub(r'\n+', '\n', str.replace('\xa0','')).strip()


class SessionManager:
    """单例模式的请求会话管理"""
    __session = requests.session()
    __session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69'}
    adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
    __session.mount('https://', adapter)
    __session.mount('http://', adapter)

    def __init__(self):
        pass

    @classmethod
    def get(cls) -> requests.Session:
        return cls.__session


def task(urls, save_path, p_idx):
    """爬取并处理数据后保存到文件中

    Args:
        urls(list): 单个分页中所有文章的链接
        save_path(str): 数据保存目录
        p_idx(int or str): 分页索引
    """
    th_list = []
    data = {}
    with ThreadPoolExecutor() as th_pool:
        for url in urls:
            th_list.append(th_pool.submit(ContentProcessor, url))

        for th in th_list:
            r = th.result().parse()
            if r is not None:
                data.update(r)

    # 保存到文件
    with open(os.path.join(save_path, f'page_{p_idx}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    log.info(f'第{p_idx}页爬取结束，共{len(data)}条数据')


if __name__ == '__main__':
    base_url = 'https://language.chinadaily.com.cn/'

    # 分页总数量
    session = SessionManager.get()
    bs = BeautifulSoup(session.get(base_url + '/news_bilingual/').text, 'html.parser')
    page_count = int(bs.select_one('#div_currpage > a:last-child').get('href').split('page_')[1].split('.')[0])
    log.info(f'{page_count} pages of data')

    parser = argparse.ArgumentParser()
    parser.add_argument('--save_path', default='./china_daily_data', type=str)
    args = parser.parse_args()

    # 创建数据目录
    if not os.path.exists(args.save_path):
        os.makedirs(args.save_path)
        log.info(f'Create directory：{args.save_path}')

    with ProcessPoolExecutor() as pr_pool:
        for p_idx in range(1, page_count + 1):
            res = session.get(base_url + f'/news_bilingual/page_{p_idx}.html')
            url_list = list(map(lambda el: el.get('href').replace('//', 'https://'),
                                BeautifulSoup(res.text, 'html.parser').select(
                                    'div.content_left > div.gy_box > a')))  # 取分页中的a标签链接

            # 提交任务进程
            pr_pool.submit(task, url_list, args.save_path, p_idx)
