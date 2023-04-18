import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
from tqdm import tqdm 
import multiprocessing
import argparse
from pathlib import Path
from datasets import load_dataset


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


def save_pdf_file(url_information):
    if os.path.exists(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{url_information['record']}"):
        return

    html_text = send_get_html_request_with_retry(url_information["url"])

    if html_text:
        with open(f"{DOWNLOAD_PDF_FILE_ROOT_PATH}/{url_information['record']}/{url_information['url'].split('/')[-1]}", mode='wb') as f:
             f.write(html_text)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_save_dir', default="./download_pdf", type=str, help='文件保存位置')
    parser.add_argument('--erroe_file_local', default="./error_url.txt", type=str, help='报错url文件保存位置')
    parser.add_argument('--worker_thread', default=0, type=int, help='并行核数')
    parser.add_argument('--start', default=0, type=int, help='开始下载的位置')
    parser.add_argument('--end', default=-1, type=int, help='结束下载的位置')

    args = parser.parse_args()
    ERROR_URL_FILE_LOCAL = args.erroe_file_local
    DOWNLOAD_PDF_FILE_ROOT_PATH = args.file_save_dir

    Path(args.file_save_dir).mkdir(parents=True, exist_ok=True)

    # 在这里统一使用hugging仓库的dataset作为下载
    dataset = load_dataset("ranWang/UN_PDF_RECORD_SET", split="2000year")

    if args.start >= len(dataset):
        raise ValueError(f"start to long, max is {len(dataset)}")

    if args.end == -1:
        args.end = len(dataset)


    url_information_list = dataset.to_dict()
    with multiprocessing.Pool(processes=args.worker_thread or multiprocessing.cpu_count()) as pool:
        for _ in tqdm(pool.imap_unordered(save_pdf_file, url_information_list[args.start:args.end]), total=len(dataset[args.start:args.end])):
            pass
