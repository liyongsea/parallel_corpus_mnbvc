import os.path
import time
import sys
import concurrent.futures
import requests
import re
from urllib import parse
from urllib.request import build_opener, install_opener, urlretrieve

counter = 0
num_of_threads = 5
lang_list = ['zh', 'en', 'fr', 'es', 'ru', 'ar']
root_url = 'https://www.un.org/'
url_status = {}
tmp_url_status = {}
link_pattern = r'<a href="((?:https?://[^/]*?\.un\.org)?/[^"]*?)"'
media_format_list = ['avi', 'wmv', 'mpeg', 'mp4', 'mov', 'mkv', 'flv', 'f4v', 'm4v', 'rmvb', 'rm', '3gp', 'dat', 'ts',
                     'mts', 'vob', 'bmp', 'jpg', 'png', 'tiff', 'gif', 'pcx', 'tga', 'exif', 'fpx', 'svg', 'psd', 'cdr',
                     'pcd', 'dxf', 'ufo', 'eps', 'ai', 'raw', 'wmf', 'mp3', 'aiff', 'aac']
# url中含该list中的字符串则不处理
excluded_url_pattern_list = ['search?', 'download?', 'subscribe?', 'system/403?', 'sustainabledevelopment.un.org/',
                             'https://www.un.org/unispal/documents/?']
# url符合pattern则做替换
url_clean_pattern_list = [(r'^http://\s*', 'https://'), (r'\r?\n', ''), (r'\s*#.*', ''), (r'(?<=\.pdf)&.*', ''),
                          (r'(?<=asp)\?.*', ''), (r'\.un\.org/../', '.un.org/'), (r'/[^./]*?/../', '/'),
                          (r'\s*[|/?]$', ''), (r'https://(.*?\.un\.org)//\1/', r'https://\1/'), (' ', '%20'),
                          (r'(.*ldcportal/content/[^?\n]*)\?.*', r'\1'), r'\t', '']


def initialize_url_status():
    global url_status, tmp_url_status

    if os.path.exists(base_dir + 'url_status.txt'):
        with open(base_dir + 'url_status.txt', 'r', encoding='utf8') as f:
            lines = f.readlines()
            url_status = {line.split('\t')[0]: int(line.split('\t')[1]) for line in lines}
    else:
        url_status = {root_url + lang: 0 for lang in lang_list}
    tmp_url_status = url_status.copy()


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
        resp = requests.get(url, headers=header, timeout=10)
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


def has_excluded_url_pattern(url):
    if any(excluded_pattern in url for excluded_pattern in excluded_url_pattern_list):
        return True
    else:
        return False


def clean_url(url):
    # if url.find('http://') == 0:
    #     url = url.replace('http://', 'https://')
    # if url[-1] == '/':
    #     url = url[:-1]
    # if url.find('#') > 0:
    #     url = re.sub(r'#.*', '', url)
    # if url.find('.pdf&') > 0:
    #     url = re.sub(r'(?<=\.pdf)&.*', '', url)
    # if url.find('../') > 0:
    #     url = get_absolute_path(url)
    # url = re.sub(r'\r?\n', '', re.sub(r'\|$', '', url))
    # url = url.strip().replace(' ', '%20')
    # if re.search(r'https://(.*?un\.org)//\1/', url):
    #     url = re.sub(r'https://(.*?un\.org)//', 'https://', url)
    # if re.search(r'asp\?', url):
    #     url = re.sub(r'(?<=asp)\?.*', '', url)

    # 以上各种条件下的清洗改为等价的正则替换
    for pattern, repl in url_clean_pattern_list:
        url = re.sub(pattern, repl, url)
    return url


def parse_urls(curr_url, html):
    urls = []
    base_url = re.sub(r'(?<=\.un\.org)/.*', '', curr_url)
    matched_urls = re.findall(link_pattern, html)
    for url in matched_urls:
        url = url.strip()
        if url[0] == '/':
            # 把相对路径改为绝对路径
            url = base_url + url
        if has_excluded_url_pattern(url):
            # 如果url中包含某些字符串则不处理
            continue
        elif is_media(url):
            # 如果是媒体格式的文件则不处理
            continue
        # 清洗url
        url = clean_url(url)
        if url not in urls:
            urls.append(url)
    return urls


def process_url(url, force_to_save):
    global counter, tmp_url_status
    has_new = False
    counter += 1

    if url.lower()[-4:] == '.pdf' or url.lower()[-4:] == '.doc' or url.lower()[-5:] == '.docx':
        # 目前仅下载这3种文件，其余格式的二进制文件基本上没有有效文本暂不考虑了
        status = save_file(url)
        tmp_url_status[url] = status
        return True

    html = get_html(url)
    if html:
        # 保存网页到本地
        status = save_local(url, html)
        tmp_url_status[url] = status

        # 从网页中解析所有链接
        urls = parse_urls(url, html)
        if len(urls) > 0:
            for new_url in urls:
                if re.sub('/$', '', new_url) in tmp_url_status.keys():
                    continue
                tmp_url_status[new_url] = 0
                has_new = True
    else:
        tmp_url_status[url] = -1

    if force_to_save or counter % 100 == 0:
        print('%s - total url: %i, crawled url: %i' %
              (time.strftime('%Y-%m-%d %H:%M:%S'), len(tmp_url_status),
               len([url for url in tmp_url_status.keys() if tmp_url_status[url] != 0])))
        save_url_status(tmp_url_status)

    return has_new


def run_threads(num_threads):
    global url_status

    last_url = list(url_status.keys())[-1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_url, url, url == last_url)
                   for url in url_status.keys() if url_status[url] == 0]
    results = [future.result() for future in futures]

    has_new = any(result for result in results)
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
    has_new_url = run_threads(num_threads=num_of_threads)
    while has_new_url:
        print(time.strftime('%Y-%m-%d %H:%M:%S'))
        initialize_url_status()
        has_new_url = run_threads(num_threads=num_of_threads)

    print(time.strftime('%Y-%m-%d %H:%M:%S'))
    print(time.perf_counter() - start)
