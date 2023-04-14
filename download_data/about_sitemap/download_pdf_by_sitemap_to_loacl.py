import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
import urllib.request
import gzip
import io
from lxml import etree
import re
from tqdm import tqdm 
import multiprocessing
import argparse
from pathlib import Path
import datasets

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}

DOWNLOAD_PDF_FILE_ROOT_PATH = None
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
        response = session.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        save_error_url(url + "\n" + str(e))
        return None
    
    return response.content


def save_pdf_file(file_path, pdf_text):
    if pdf_text:
        with open(file_path, mode='wb') as f:
             f.write(pdf_text)


def save_six_countries_file(record_list_row):
    file_save_dir = f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{record_list_row['record']}"
    Path(file_save_dir).mkdir(parents=True, exist_ok=True)
    
    for pdf_url in record_list_row["urls"]:
        if not os.path.exists(f"{file_save_dir}/{pdf_url.split('/')[-1]}"):
            save_pdf_file(f"{file_save_dir}/{pdf_url.split('/')[-1]}", get_network_pdf(pdf_url))



def main(worker_thread, start, end):
    record_list = datasets.load_dataset("ranWang/un_pdf_record_list_set", split="2000").to_dict()["record_list"]
    
    if start >= len(record_list) -1:
        raise ValueError(f"start too long, list long is {len(record_list)}")

    if end == -1:
        end = len(record_list) 
    else:
        end = len(record_list) if end >= len(record_list) else end

    record_list = record_list[start:end-1]
    print("start download pdf")

    if worker_thread == 1:
        for record_list_row in tqdm(record_list):
            save_six_countries_file(record_list_row)

    elif worker_thread == 0:   
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            for _ in tqdm(pool.imap_unordered(save_six_countries_file, record_list), total=len(record_list)):
                pass
    else:
        with multiprocessing.Pool(processes=worker_thread) as pool:
            for _ in tqdm(pool.imap_unordered(save_six_countries_file, record_list), total=len(record_list)):
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker_thread', default=1, type=int, help='并行核数')
    parser.add_argument('--file_save_path', default="./download_pdf", type=str, help='文件保存位置')
    parser.add_argument('--erroe_file_save_path', default="./error_url.txt", type=str, help='报错url文件保存位置')
    parser.add_argument('--start', default=0, type=int, help='下载开始的位置')
    parser.add_argument('--end', default=-1, type=int, help='下载结束的位置')

    args = parser.parse_args()

    ERROR_URL_SAVE_PATH = args.erroe_file_save_path
    DOWNLOAD_PDF_FILE_ROOT_PATH = args.file_save_path

    if args.worker_thread < 0:
        raise ValueError("worker_thread 必须大于等于0")
    if args.start < 0:
        raise ValueError("start 必须大于等于0")

    main(args.worker_thread, args.start, args.end)