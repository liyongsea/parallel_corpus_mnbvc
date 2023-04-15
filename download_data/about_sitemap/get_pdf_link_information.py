import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
from lxml import etree
from tqdm import tqdm 
import multiprocessing
import argparse
from bs4 import BeautifulSoup
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}

# default
ERROR_URL_FILE_LOCAL = "./error_urls.txt"


def save_error_url(write_text):
    if os.path.isfile(ERROR_URL_FILE_LOCAL):
        mode = 'a'
    else:
        mode = 'w'
        
    with open(ERROR_URL_FILE_LOCAL, mode) as f:
         f.write(write_text + '\n')


def send_get_html_request_with_retry(url, headers=HEADERS, retries=3, backoff_factor=0.5):
    session = requests.Session()

    #  Create a retry mechanism with the given parameters
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)

    # Mount the adapter to the session for both http and https requests
    session.mount('http://', adapter)
    session.mount('https://', adapter)
  
    try:
        response = session.get(url, headers=headers)

        # Raise an exception if the status code is not successful
        response.raise_for_status()
    except Exception as e:
        save_error_url(url + "\n")
        return None
    
    return response.text


def parse_six_lang_pdf_links(six_lang_pdf_links):
    """Parse all son sitemap link in root sitemap file text

    TODO:  change this function to def analyse_url
        Examples:
            https://digitallibrary.un.org/record/4008528/files/E_2023_SR.7-EN.pdf -> {"record": 4008528, "lang": "en", "type": "pdf"}

    Returns:
        Sitemap link list
   
    """
   
    basis_pdf_url = six_lang_pdf_links[0]

    file_selection_page_url = basis_pdf_url.split("/files")[0]
    file_selection_page_html_text =  send_get_html_request_with_retry(file_selection_page_url)
    
    soup = BeautifulSoup(file_selection_page_html_text, features="lxml")

    return {
        "year_time":int(soup.select(".metadata-details div:last-of-type > .one-row-metadata")[0].get_text()),
        "record": file_selection_page_url.split("/files")[0].split("record/")[-1],
        "urls":six_lang_pdf_links
    }



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_save_dir', default="./download_pdf", type=str, help='文件保存位置')
    parser.add_argument('--downloaded_pdf_url_dir', default="./download_pdf", type=str, help='已经下载的pdf链接所保存的目录')    
    parser.add_argument('--erroe_file_local', default="./error_url.txt", type=str, help='报错url文件保存位置')
    parser.add_argument('--worker_thread', default=0, type=int, help='并行核数')

    args = parser.parse_args()
    ERROR_URL_FILE_LOCAL = args.erroe_file_local

    if not os.path.isfile(f"{args.downloaded_pdf_url_dir}/SixLanguagePDF-URLS.json"):
        raise FileNotFoundError("f'{args.downloaded_pdf_url_dir}/SixLanguagePDF-URLS.json' 文件不存在")

    with open(f"{args.downloaded_pdf_url_dir}/SixLanguagePDF-URLS.json", "r") as f:
        six_lang_pdf_urls = json.load(f)


    with multiprocessing.Pool(processes=args.worker_thread or multiprocessing.cpu_count()) as pool:
        parsed_dict_list = list(tqdm(pool.imap_unordered(parse_six_lang_pdf_links, six_lang_pdf_urls), total=len(six_lang_pdf_urls)))


    parsed_dict_list.sort(key=lambda record_list: record_list["year_time"])
    with open(f"{args.file_save_dir}/SixLanguageURL-Information.json", "w") as f:
         json.dump(parsed_dict_list, f)