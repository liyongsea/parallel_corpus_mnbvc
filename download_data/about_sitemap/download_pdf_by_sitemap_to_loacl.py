import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
import urllib.request
import gzip
import io
from bs4 import BeautifulSoup
from lxml import etree
import re
from tqdm import tqdm 
import json
import multiprocessing
import argparse


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}

ERROR_URL_SAVE_PATH = None

def save_error_url(write_text):
    if os.path.isfile(ERROR_URL_SAVE_PATH):
        mode = 'a'
    else:
        mode = 'w'
        
    with open(ERROR_URL_SAVE_PATH, mode) as f:
         f.write(write_text + '\n')

def get_network_pdf(url, headers=HEADERS, retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
  
    try:
        response = session.get(url, headers=HEADERS)
        response.raise_for_status()
    except Exception as e:
        save_error_url(url + "\n" + str(e))
        return None
    
    return response.content


def get_sitemap(gz_url):
    response = urllib.request.urlopen(gz_url)
    compressed_file = io.BytesIO(response.read())
    decompressed_file = gzip.GzipFile(fileobj=compressed_file)
    return decompressed_file.read()


def get_file_url_in_sitemap(sitemap_text):
    root = etree.fromstring(sitemap_text)
    locs = []
    for url in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
        loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        locs.append(loc)
    return locs

def get_sitemap_url_in_sitemap(sitemap_text):
    root = etree.fromstring(sitemap_text)
    locs = []
    for sitemap in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
        loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        locs.append(loc)
    return locs


LANG_LIST = ["ar", "en", "es", "fr", "ru", "zh"]

LANGUAGE_REGEX = re.compile(f"({'|'.join(LANG_LIST)})\.pdf$")

def match_six_countries_file_url(url_list):

    pdf_dict = {}
    for i in range(len(url_list) - len(LANG_LIST) + 1):
        match = True
        for j in range(len(LANG_LIST)):
            if not LANGUAGE_REGEX.search(url_list[i+j].lower()):
                match = False
                break
   
        if match:
            file_name = url_list[i].split("/")[-1].split("-")[0]
            pdf_dict[file_name] = [url_list[i+j] for j in range(len(LANG_LIST))]
            
    return pdf_dict


def check_folder_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def save_pdf_file(file_path, pdf_text):
    if pdf_text:
        with open(file_path, mode='wb') as f:
             f.write(pdf_text)

def save_six_countries_file(file_name, pdf_urls):
    check_folder_exists(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{file_name}")
    for pdf_url in pdf_urls:
        if not os.path.exists(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{file_name}/{pdf_url.split('/')[-1]}"):
            save_pdf_file(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{file_name}/{pdf_url.split('/')[-1]}", get_network_pdf(pdf_url))

def save_six_countries_file_wrapper(args):
    file_name, file_url = args
    save_six_countries_file(file_name, file_url)


DOWNLOAD_PDF_FILE_ROOT_PATH = None
ROOT_SITEMAP_URL = "https://digitallibrary.un.org/sitemap_index.xml.gz"

def main(worker_thread):
    file_name_with_six_countries_file_url = {}

    print("start request sitemap")

    if os.path.exists(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/root.json"):
        with open(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/root.json", mode='r') as f:
            file_name_with_six_countries_file_url = json.load(f)
    else:        
        root_sitemap_text = get_sitemap(ROOT_SITEMAP_URL)
        file_sitemap_urls = get_sitemap_url_in_sitemap(root_sitemap_text)


        for file_sitemap_url in tqdm(file_sitemap_urls):
            files_sitemap = get_sitemap(file_sitemap_url)
            file_urls = get_file_url_in_sitemap(files_sitemap)
            file_name_with_six_countries_file_url.update(match_six_countries_file_url(file_urls))

        check_folder_exists(DOWNLOAD_PDF_FILE_ROOT_PATH)
        with open(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/root.json", mode='w') as f:
            json.dump(file_name_with_six_countries_file_url, f)

    print("start download pdf")
    
    if worker_thread == 1:
        for file_name in tqdm(file_name_with_six_countries_file_url):
            save_six_countries_file(file_name, file_name_with_six_countries_file_url[file_name])

    elif worker_thread == 0:
        args_list = [(file_name, file_name_with_six_countries_file_url[file_name]) for file_name in file_name_with_six_countries_file_url]     
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            for _ in tqdm(pool.imap_unordered(save_six_countries_file_wrapper, args_list), total=len(args_list)):
                pass
    else:
        args_list = [(file_name, file_name_with_six_countries_file_url[file_name]) for file_name in file_name_with_six_countries_file_url]
        with multiprocessing.Pool(processes=worker_thread) as pool:
            for _ in tqdm(pool.imap_unordered(save_six_countries_file_wrapper, args_list), total=len(args_list)):
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker_thread', default=1, type=int, help='并行核数')
    parser.add_argument('--file_save_path', default="./download_pdf", type=str, help='文件保存位置')
    parser.add_argument('--erroe_file_save_path', default="./error_url.txt", type=str, help='报错url文件保存位置')
    args = parser.parse_args()

    ERROR_URL_SAVE_PATH = args.erroe_file_save_path
    DOWNLOAD_PDF_FILE_ROOT_PATH = args.file_save_path

    if args.worker_thread < 0:
        raise ValueError("worker_thread 必须大于等于0")

    main(args.worker_thread)
        