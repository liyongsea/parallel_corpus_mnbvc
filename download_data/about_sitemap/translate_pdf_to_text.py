from PyPDF2 import PdfReader
import os
import subprocess
from tqdm import tqdm
import multiprocessing
import argparse
from pathlib import Path
from functools import partial


def get_pdf_text(file_location):
    """
    Args:
       file localtion, for example: "./download_pdf/638050/CEDAW_C_SWE_CO_7-ZH.pdf"

    Returns:
        List split by page
    """
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


def save_txt_file(save_file_loaction, text_list):
    """
    save txt file Split with "\n----\n"

    Args:
       List split by page
    """
    with open(save_file_loaction, 'w') as f:
         f.write("\n----\n".join(text_list))


def process_folder(record, input_dir_path, output_dir_path):
    if ".json" in record:
        return 

    text_save_path = os.path.join(output_dir_path, record)
    Path(text_save_path).mkdir(parents=True, exist_ok=True)

    try:
        for pdf_file_name in os.listdir(os.path.join(input_dir_path, record)):
            if not "pdf" in pdf_file_name:
                continue
            
            save_pdf_text_path = f"{text_save_path}/{pdf_file_name.replace('.pdf','.txt')}"

            if os.path.exists(save_pdf_text_path):
                continue
                
            pdf_text = get_pdf_text(os.path.join(input_dir_path, record, pdf_file_name))

            if pdf_text:
                save_txt_file(save_pdf_text_path, pdf_text)

    except Exception:
        print(record)
                

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--downloaded_pdf_path', default="./download_pdf", type=str, help='下载的pdf文件位置')
    parser.add_argument('--pdf_text_save_dir_path', default="./pdf_text", type=str, help='保存的pdf text文件位置')

    args = parser.parse_args()

    Path(args.pdf_text_save_dir_path).mkdir(parents=True, exist_ok=True)

    dir_list = os.listdir(args.downloaded_pdf_path)

    partial_process_row = partial(process_folder, input_dir_path=args.downloaded_pdf_path, output_dir_path=args.pdf_text_save_dir_path)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        for _ in tqdm(pool.imap_unordered(partial_process_row, dir_list), total=len(dir_list)):
            pass
