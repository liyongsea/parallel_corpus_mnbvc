import argparse
import re
import datasets
import sys
import os

from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

from get_urls import get_weekly_date_ranges_adjusted, main as get_urls
from download_by_urls import main as download_by_urls


TEMP_DIR = Path("un_crawl_temp")
TEMP_DIR.mkdir(exist_ok=True)


def extract_language(s):
    match = re.search(r'Open(.+?)WordDocument', s)
    if match:
        return match.group(1)  # 返回语言部分
    return None  # 如果没有找到匹配，返回 None


LANGUAGE_MAP = {
    "Chinese": "中文",
    "Arabic": "阿拉伯文",
    "French": "法文",
    "English": "英文", 
    "Spanish": "西班牙文",
    "Russian": "俄文",
}

def get_urls_dataset(folder_path: Path):
    # 获取文件夹中的所有文件
    files = folder_path.glob("*")

    dataset_list = {"文号": [], "语言": [], "链接": []}
  
    for file in files:
        with open(file, 'r') as file:
            lines = file.readlines()

            for line in lines:
                if 'WordDocument,' in line:
                    row = line.split(",")
                    language = extract_language(row[2])
                    zh_language = LANGUAGE_MAP.get(language, None)

                    if zh_language:
                        dataset_list["文号"].append(row[1])
                        dataset_list["语言"].append(zh_language)
                        dataset_list["链接"].append(row[3].strip())

    dataset = datasets.Dataset.from_dict(dataset_list)
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_time", default="2000-01-01", help="Start time")
    parser.add_argument("--end_time", default="2024-01-01", help="End time")
    parser.add_argument("-o","--output_path", default="un_crawl_result", help="输出文件的路径")

    args = parser.parse_args()

    output_path = args.output_path
    Path(output_path).mkdir(exist_ok=True)

    start_time = args.start_time
    end_time = args.end_time
    dates = get_weekly_date_ranges_adjusted(start_time, end_time)

    get_urls(dates, TEMP_DIR)
    print("Download completed!")

    print("Start generate urls dataset...")
    dataset = get_urls_dataset(TEMP_DIR)
    
    print("Start download file...")
    download_by_urls(dataset, output_path)
