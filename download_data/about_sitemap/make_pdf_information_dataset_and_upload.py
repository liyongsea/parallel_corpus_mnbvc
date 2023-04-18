import argparse
import json
from datasets import Dataset

LANG_LIST = ["ar","en","zh","fr","ru","es"]

def extract_language_from_url(url):
    lang_code_lower = url[-6:-4].lower()
    if lang_code_lower not in LANG_LIST:
        return None
    return lang_code_lower


def process(file_save_dir):
    with open(f"{file_save_dir}/SixLanguageURL-Information.json","r") as f:
        urls_information = json.load(f)

    url_information_list = {"record":[], "language":[], "year_time":[], "file_name":[], "url":[]}

    for url_information in urls_information:
        for url in url_information["urls"]:
            url_information_list["year_time"].append(url_information["year_time"])
            url_information_list["record"].append(int(url_information["record"]))
            url_information_list["url"].append(url)
            url_information_list["language"].append(extract_language_from_url(url))
            url_information_list["file_name"].append(url.split("files/")[1])


    return Dataset.from_dict(url_information_list)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--datasets_warehouse', type=str, help='huggingface的仓库')
    parser.add_argument('--token', type=str, help='huggingface的token')
    parser.add_argument('--file_saved_dir', default="./download_pdf", type=str, help="由'get_pdf_link_information'脚本保存的json文件的文件夹路径")

    args = parser.parse_args()

    if not (args.datasets_warehouse or args.token):
        raise ValueError("datasets_warehouse 或 token 不可为空")

    dataset = process(args.file_saved_dir)

    dataset.push_to_hub(args.datasets_warehouse, token=args.token)