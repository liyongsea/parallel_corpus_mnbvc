import re
from PyPDF2 import PdfReader
import os
import subprocess
from tqdm import tqdm
import multiprocessing
import argparse
from pathlib import Path


lang_regex = re.compile(r".*-(?P<lang>[A-Za-z]{2})\.pdf")

def match_pdf_name_lang(pdf_name):
    match = lang_regex.match(pdf_name)
    if match:
        lang_code = match.group("lang")
        return lang_code
    return None


def get_pdf_text(file_location):
    with open(file_location, 'rb') as pdf_file:
        try:
            pdf_reader = PdfReader(pdf_file)
        except Exception as e:
            return []
        
        pdf_text_list = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                pdf_text_list.append(text)

        return pdf_text_list


def save_txt_file(path, text_list):
    save_txt = ""
    for text in text_list:
        save_txt += (text + "\n----\n")
    with open(path, 'w') as f:
         f.write(save_txt)


def process_folder(file_name):
    try:
        if "root.json" in file_name:
            return 

        text_save_path = os.path.join(PDF_TEXT_FILE_PATH, file_name)
        Path(text_save_path).mkdir(parents=True, exist_ok=True)

        for pdf_file_name in os.listdir(os.path.join(DOWNLOADED_PDF_PATH, file_name)):
            if not "pdf" in pdf_file_name:
                continue
            
            save_pdf_text_path = f"{text_save_path}/{pdf_file_name.split('-')[0]}-{match_pdf_name_lang(pdf_file_name)}.txt"

            if os.path.exists(save_pdf_text_path):
                continue
                
            pdf_text = get_pdf_text(os.path.join(DOWNLOADED_PDF_PATH, file_name, pdf_file_name))

            if pdf_text:
                save_txt_file(save_pdf_text_path, pdf_text)
                
    except Exception:
        pass

DOWNLOADED_PDF_PATH = None
PDF_TEXT_FILE_PATH = None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--downloaded_pdf_path', default="./download_pdf", type=str, help='下载的pdf文件位置')
    parser.add_argument('--pdf_text_file_path', default="./pdf_text_file", type=str, help='保存的pdf text文件位置')

    args = parser.parse_args()
    DOWNLOADED_PDF_PATH = args.downloaded_pdf_path
    PDF_TEXT_FILE_PATH = args.pdf_text_file_path

    Path(PDF_TEXT_FILE_PATH).mkdir(parents=True, exist_ok=True)

    dir_list = list(os.listdir(DOWNLOADED_PDF_PATH))
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        for _ in tqdm(pool.imap_unordered(process_folder, dir_list), total=len(dir_list)):
            pass
