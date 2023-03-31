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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}

error_url_save_path = "./error_url.txt"

def save_error_url(url):
    if os.path.isfile(error_url_save_path):
        mode = 'a'
    else:
        mode = 'w'
        
    with open(error_url_save_path, mode) as f:
         f.write(url + '\n')
            
def get_network_html(url, headers=headers, retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
  
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"链接异常: {url} --- {e}")
        return None
    
    return response.text

def get_network_pdf(url, headers=headers, retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
  
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        save_error_url(url)
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


languages = ["ar", "en", "es", "fr", "ru", "zh"]

language_pattern = "|".join(languages)
language_regex = re.compile(f"({language_pattern})\.pdf$")

def match_six_countries_file_url(url_list):
    
    pdf_dict = {}

    for i in range(len(url_list) - len(languages) + 1):
   
        match = True
        for j in range(len(languages)):
            if not language_regex.search(url_list[i+j].lower()):
                match = False
                break
   
        if match:
            file_name = url_list[i].split("/")[-1].split("-")[0]
            pdf_dict[file_name] = [url_list[i+j] for j in range(len(languages))]
            
    return pdf_dict


def check_folder_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def save_pdf_file(file_path, pdf_text):
    if pdf_text:
        with open(file_path, mode='wb') as f:
             f.write(pdf_text)

def save_six_countries_file(file_name, pdf_urls):
    check_folder_exists(f"{download_pdf_file_root_path}/{file_name}")
    for pdf_url in pdf_urls:
        if not os.path.exists(f"{download_pdf_file_root_path}/{file_name}/{pdf_url.split('/')[-1]}"):
            save_pdf_file(f"{download_pdf_file_root_path}/{file_name}/{pdf_url.split('/')[-1]}", get_network_pdf(pdf_url))

def save_six_countries_file_wrapper(args):
    file_name, file_url = args
    save_six_countries_file(file_name, file_url)


download_pdf_file_root_path = "./download_pdf"
root_url = "https://digitallibrary.un.org"
root_sitemap_url = "https://digitallibrary.un.org/sitemap_index.xml.gz"


if __name__ == '__main__':
    file_name_with_six_countries_file_url = {}

    print("start request sitemap")

    if os.path.exists(f"{download_pdf_file_root_path}/root.json"):
        with open(f"{download_pdf_file_root_path}/root.json", mode='r') as f:
            file_name_with_six_countries_file_url = json.load(f)
    else:        
        root_sitemap_text = get_sitemap(root_sitemap_url)
        file_sitemap_urls = get_sitemap_url_in_sitemap(root_sitemap_text)


        for file_sitemap_url in tqdm(file_sitemap_urls):
            files_sitemap = get_sitemap(file_sitemap_url)
            file_urls = get_file_url_in_sitemap(files_sitemap)
            file_name_with_six_countries_file_url.update(match_six_countries_file_url(file_urls))

        check_folder_exists(download_pdf_file_root_path)
        with open(f"{download_pdf_file_root_path}/root.json", mode='w') as f:
            json.dump(file_name_with_six_countries_file_url, f)

    print("start download pdf")
    args_list = [(file_name, file_name_with_six_countries_file_url[file_name]) for file_name in file_name_with_six_countries_file_url]
        
    with multiprocessing.Pool(processes=multiprocessing.cpu_count() * 4) as pool:
        for _ in tqdm(pool.imap_unordered(save_six_countries_file_wrapper, args_list), total=len(args_list)):
            pass
        