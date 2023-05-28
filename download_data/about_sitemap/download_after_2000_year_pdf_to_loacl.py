import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
from tqdm import tqdm 
import multiprocessing
import argparse
from pathlib import Path
from datasets import load_dataset
from functools import partial



HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}

def save_error_url(write_text, loacl):
    if os.path.isfile(loacl):
        mode = 'a'
    else:
        mode = 'w'

    with open(loacl, mode) as f:
         f.write(write_text + '\n')


def send_get_pdf_request_with_retry(url, erroe_file_local, headers=HEADERS, retries=3, backoff_factor=0.5):
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
        save_error_url(url + "\n", erroe_file_local)
        return None

    # PDF is binary, so it returns content
    return response.content


def save_pdf_file(url_information, file_save_dir, erroe_file_local):
    print(url_information['record'])
    """
    Args:
        url_information:
            Example: { 
                        "record": 211803, 
                        "language": "ar", 
                        "year_time": 1954, 
                        "file_name": "A_RES_863%28IX%29-AR.pdf", 
                        "url":, "https://digitallibrary.un.org/record/211803/files/A_RES_863%28IX%29-AR.pdf"
                    }
                    
        file_save_dir: Directory where downloaded files are saved
        erroe_file_local: Request URL error to save the local location of the file
    Returns:
        Sitemap text
    """
    file_svae_dir_full_path= f"{file_save_dir}/{url_information['record']}"
    Path(file_svae_dir_full_path).mkdir(parents=True, exist_ok=True)

    # Use the last file name of the URL as the file name
    file_local = os.path.join(file_svae_dir_full_path, url_information['url'].split('/')[-1])
    if os.path.exists(file_local):
        return

    html_text = send_get_pdf_request_with_retry(url_information["url"], erroe_file_local)

    if html_text:
        with open(file_local, mode='wb') as f:
             f.write(html_text)




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_save_dir', default="./download_pdf", type=str, help='文件保存位置')
    parser.add_argument('--erroe_file_local', default="./error_url.txt", type=str, help='报错url文件保存位置')
    parser.add_argument('--worker_thread', default=0, type=int, help='并行核数')

    args = parser.parse_args()

    Path(args.file_save_dir).mkdir(parents=True, exist_ok=True)

    # 在这里统一使用hugging仓库的dataset作为下载
    dataset = load_dataset("ranWang/UN_PDF_RECORD_SET", split="2000year")

    partial_process_row = partial(save_pdf_file, file_save_dir=args.file_save_dir, erroe_file_local=args.erroe_file_local)

    dataset.map(partial_process_row)