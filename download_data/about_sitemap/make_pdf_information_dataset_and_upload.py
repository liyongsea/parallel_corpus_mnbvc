import argparse
import json
from datasets import Dataset

LANG_LIST = ["ar", "en", "zh", "fr", "ru", "es"]

def extract_language_from_url(url):
    """
    Args: url
        Examples: https://digitallibrary.un.org/record/228957/files/A_2890-ZH.pdf

    Returns:
        One of the LANG_LIST or None
    """
    lang_code_lower = url[-6:-4].lower()
    if lang_code_lower not in LANG_LIST:
        return None
    return lang_code_lower


def process(file_saved_dir):
    """
    Args: 
        file_saved_dir: File path saved by script "get_pdf_link_information.py"
        
    Returns:
        Dataset
        
    """
    with open(f"{file_saved_dir}/SixLanguageURL-Information.json","r") as f:
        urls_information = json.load(f)

    url_information_list = {"record":[], "language":[], "year_time":[], "file_name":[], "url":[]}

    for url_information in urls_information:
        for url in url_information["urls"]:
            try:
                pre_inster_url_information = {"record":0, "language":'', "year_time":'', "file_name":'', "url":''}

                url_information["year_time"] = url_information["year_time"]
                url_information["record"] = int(url_information["record"])
                url_information["url"] = url
                url_information["language"] = extract_language_from_url(url)
                url_information["file_name"] = url.split("files/")[1]

                for key in pre_inster_url_information:
                    url_information_list[key].append(pre_inster_url_information[key])

            # 过滤掉不正确的url，大约11个
            except Exception:
                print(url)

    return Dataset.from_dict(url_information_list)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--datasets_repository', type=str, help='huggingface的仓库')
    parser.add_argument('--token', type=str, help='huggingface的token')
    parser.add_argument('--file_saved_dir', default="./download_pdf", type=str, help="由'get_pdf_link_information'脚本保存的json文件的文件夹路径")

    args = parser.parse_args()

    if not (args.datasets_repository or args.token):
        raise ValueError("datasets_repository 或 token 不可为空")

    dataset = process(args.file_saved_dir)

    dataset.push_to_hub(args.datasets_repository, token=args.token)