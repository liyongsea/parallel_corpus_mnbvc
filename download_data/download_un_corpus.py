import os.path
import time
import sys

import requests
import re
from urllib import parse
from urllib.request import *

lang_list = ['zh', 'en', 'fr', 'es', 'ru', 'ar']
root_url = 'https://www.un.org/'
url_status = {}
link_pattern = r'<a href="((?:https?://[^/]*?\.un\.org)?/[^"]*?)"'
media_format_list = ['avi', 'wmv', 'mpeg', 'mp4', 'mov', 'mkv', 'flv', 'f4v', 'm4v', 'rmvb', 'rm', '3gp', 'dat', 'ts',
                     'mts', 'vob', 'bmp', 'jpg', 'png', 'tiff', 'gif', 'pcx', 'tga', 'exif', 'fpx', 'svg', 'psd', 'cdr',
                     'pcd', 'dxf', 'ufo', 'eps', 'ai', 'raw', 'wmf', 'mp3', 'aiff', 'aac']


def initialize_url_status():
    global url_status

    if os.path.exists(base_dir + 'url_status.txt'):
        with open(base_dir + 'url_status.txt', 'r', encoding='utf8') as f:
            lines = f.readlines()
            url_status = {line.split('\t')[0]: int(line.split('\t')[1]) for line in lines}
    else:
        url_status = {root_url + lang: 0 for lang in lang_list}


def save_url_status(curr_url_status):
    lines = [url + '\t' + str(status) + '\n' for url, status in curr_url_status.items()]
    with open(base_dir + 'url_status.txt', 'w', encoding='utf8') as f:
        f.writelines(lines)


def get_paths(url):
    global base_dir

    rel_name = re.sub('/$', '', re.sub(r'^https?://', '', url))
    rel_name = parse.unquote(rel_name)
    paths = rel_name.split('/')

    if paths[0][-7:] != '.un.org':
        return None, None

    rel_path = base_dir

    # 有些url里包含了另一串url，有点类似重定向
    # （例：https://legal.un.org/docs/?path=https://www.icj-cij.org/files/press-releases/0/000-20190711-STA-01-00-EN.pdf）,
    # 此时用/分割可能会有问题，所以这里暂时把后面这串url整体合在一起当文件名来处理了
    for i in range(1, len(paths) - 1):
        if paths[i].find('?') > 0 or paths[i].find('https:') >= 0:
            paths[i] = '/'.join(paths[i:])
            paths = paths[:i + 1]
            break

    try:
        if len(paths) > 1:
            for i in range(len(paths) - 1):
                if not os.path.exists(rel_path + paths[i]):
                    os.mkdir(rel_path + paths[i])
                rel_path += paths[i] + '/'
        else:
            rel_path += paths[0] + '/'
            if not os.path.exists(rel_path):
                os.mkdir(rel_path)
    except Exception as e:
        print("%s: %s" % (time.strftime('%Y-%m-%d %H:%M:%S'), str(e)))
        return None, None

    return rel_path, paths


def save_local(url, content):
    rel_path, paths = get_paths(url)
    if rel_path:
        if len(paths) == 1:
            f_name = 'root.html'
        else:
            f_name = re.sub(r'\r?\n', '', paths[-1]) + '.html'
        f_name = escape(f_name)
        try:
            with open(rel_path + f_name, 'w', encoding='utf8') as f:
                f.write(content)
            return 1
        except Exception as e:
            print("%s: %s" % (time.strftime('%Y-%m-%d %H:%M:%S'), str(e)))
            return -1
    else:
        return -1


def save_file(file_url):
    rel_path, paths = get_paths(file_url)
    if rel_path:
        file_name = paths[-1]
        if file_url.endswith(file_name):
            url_parent = file_url[:file_url.find(file_name)]
        else:
            url_parent = re.sub(r'[^/]*$', '', file_url)
            file_name = parse.unquote(file_url[len(url_parent):])
        try:
            opener = build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                                'like Gecko) Chrome/73.0.3683.86 Safari/537.36')]
            install_opener(opener)
            urlretrieve(url_parent + parse.quote(file_name), rel_path + file_name)
            return 1
        except Exception as e:
            print("%s: %s" % (time.strftime('%Y-%m-%d %H:%M:%S'), str(e)))
            return -1
    else:
        return -1


def escape(c):
    # Windows下文件名无法包含以下几个字符，需要转义
    return c.replace('?', '_QMARK_').replace(':', '_COLON_').replace('|', '_PIPE_').replace('/', '_SLASH_')\
        .replace('*', '_STAR_').replace('"', '_QT_').replace('\\', '_BS_').replace('<', '_LT_').replace('>', '_GT_')


def get_html(url):
    global url_status
    header = {
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/96.0.4664.110 Safari/537.36 "
    }
    try:
        resp = requests.get(url, headers=header, timeout=30)
        html = resp.content.decode('utf8')
        return html
    except Exception as e:
        print("%s: %s" % (time.strftime('%Y-%m-%d %H:%M:%S'), str(e)))
        return None


def is_media(url):
    if url.find('.') > 0:
        tmp = re.sub(r'^.*\.', '', url).lower()
        if tmp in media_format_list:
            return True
    return False


def get_absolute_path(url):
    arr = url.split('/')
    for i in range(len(arr)):
        if arr[i][-2:] == '..':
            if arr[i-1][-7:] == '.un.org':
                url = '/'.join(arr[:i]) + '/' + '/'.join(arr[i+1:])
            else:
                url = '/'.join(arr[:(i-1)]) + '/' + '/'.join(arr[i+1:])
            return url
    return url


# 这个方法比较乱，属于不断碰到问题不断打补丁的情况
def parse_urls(curr_url, html):
    urls = []
    base_url = re.sub(r'(?<=\.un\.org)/.*', '', curr_url)
    matched_urls = re.findall(link_pattern, html)
    for url in matched_urls:
        url = url.strip()
        if url.find('search?') > 0:
            continue
        if url.find('download?') > 0:
            continue
        if url.find('subscribe?') > 0:
            continue
        if is_media(url):
            continue
        if url.find('https://www.un.org/unispal/documents/?') == 0:
            continue
        if url.find('/') == 0:
            url = base_url + url
        if url.find('http://') == 0:
            url = url.replace('http://', 'https://')
        if url[-1] == '/':
            url = url[:-1]
        if url.find('#') > 0:
            url = re.sub(r'#.*', '', url)
        if url.find('../') > 0:
            url = get_absolute_path(url)
        if url.find('.pdf&') > 0:
            url = re.sub(r'(?<=\.pdf)&.*', '', url)
        url = re.sub(r'\r?\n', '', re.sub(r'\|$', '', url))
        url = url.strip().replace(' ', '%20')
        if re.search(r'https://(.*?un\.org)//\1/', url):
            url = re.sub(r'https://(.*?un\.org)//', 'https://', url)
        if re.search(r'asp\?', url):
            url = re.sub(r'(?<=asp)\?.*', '', url)
        if url not in urls:
            urls.append(url)
    return urls


def process():
    has_new = False
    # 每个新url都是一个新key，无法直接在url_status里添加，否则会报错，所以这里临时复制一份url_status用来记录爬取状态及新url
    tmp_url_status = url_status.copy()
    for url in url_status.keys():
        if url_status[url] != 0:
            # 已经爬过的就不爬了
            continue
        if url.lower()[-4:] == '.pdf' or url.lower()[-4:] == '.doc' or url.lower()[-5:] == '.docx':
            # 目前仅下载这3种文件，其余格式的二进制文件基本上没有有效文本暂不考虑了
            status = save_file(url)
            tmp_url_status[url] = status
            save_url_status(tmp_url_status)
            continue
        html = get_html(url)
        if html:
            # 保存网页到本地
            tmp_url_status[url] = save_local(url, html)

            # 从网页中解析所有链接
            urls = parse_urls(url, html)

            if len(urls) > 0:
                for new_url in urls:
                    if new_url in tmp_url_status.keys():
                        continue
                    elif new_url[-1] != '/' and (new_url + '/') in tmp_url_status.keys():
                        continue
                    tmp_url_status[new_url] = 0
                    has_new = True
        else:
            tmp_url_status[url] = -1

        save_url_status(tmp_url_status)

    return has_new


if __name__ == '__main__':
    global base_dir
    try:
        base_dir = sys.argv[1]
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
    except:
        print('参数缺失：需要提供一个目录以便保存下载的网页和文件\ndownload_un_corpus.py <dir> dir为网页和文件下载的目录')
        sys.exit(1)

    initialize_url_status()
    print(time.strftime('%Y-%m-%d %H:%M:%S'))
    start = time.perf_counter()
    has_new_url = process()
    while has_new_url:
        initialize_url_status()
        has_new_url = process()

    print(time.strftime('%Y-%m-%d %H:%M:%S'))
    print(time.perf_counter() - start)
