import argparse
import datetime
import os
import sys
from pathlib import Path
import logging as log
import json

log.basicConfig(level=log.INFO, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

from get_urls import main as get_urls
from download_by_urls import main as download_by_urls

def get_weekly_date_ranges_adjusted(start_date_str, end_date_str):
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return []

    result_list = []

    # Adjust start_date to the first day of the week (Monday)
    start_day_of_week = start_date.weekday()  # Monday is 0, Sunday is 6
    start_of_week = start_date - datetime.timedelta(days=start_day_of_week)

    while start_of_week < end_date:
        end_of_week = start_of_week + datetime.timedelta(days=6)  # End of the week

        # Adjust the start and end of the week to be within the given date range
        actual_start = max(start_of_week, start_date)
        actual_end = min(end_of_week, end_date)

        result_list.append(
            (actual_start.strftime("%Y-%m-%d"), actual_end.strftime("%Y-%m-%d"))
        )

        # Move to the next week
        start_of_week = end_of_week + datetime.timedelta(days=1)

    return result_list

def read_json_files(folder_path):
    """
    Reads all .json files in the specified folder and combines the arrays in these files into a single list.

    :param folder_path: Path to the folder containing .json files.
    :return: Combined list of all elements from the JSON arrays in the files.
    """
    combined_data = []
    for file in Path(folder_path).glob("**/*.json"):
        with open(file, 'r') as f:
            try:
                json_data = json.load(f)
                combined_data.extend(json_data)  # Extend the main list with the contents of this file
            except json.JSONDecodeError:
                print(f"Error decoding JSON from file: {file}")
    return combined_data

def transform_json(data_array):
    datasets = []
    for json_data in data_array:
        for item in json_data['url_with_languages']:
            language = item['language']
            for link in item['file_links']:
                if link['type'] == "doc":
                    data = {
                        "链接": link['url'],
                        "文号": json_data['id'],
                        "语言": language
                    }
                    datasets.append(data)
                
    return datasets

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_time", default="2024-01-01", help="Start time")
    parser.add_argument("--end_time", default="2024-01-10", help="End time")
    parser.add_argument("-o","--output_path", default="un_crawl_result", help="输出文件的路径")

    args, _ = parser.parse_known_args()

    # url缓存路径
    TEMP_PATH = Path("un_doc_url_result_temp")
    TEMP_PATH.mkdir(exist_ok=True)

    dates = get_weekly_date_ranges_adjusted(args.start_time, args.end_time)

    log.info(f"Get urls for {args.start_time, args.end_time}...")
    get_urls(dates, TEMP_PATH)
    log.info(f"Get urls for {args.start_time, args.end_time} success...")

    log.info(f"Download file for urls...")
    json_files = read_json_files(TEMP_PATH)
    dataset = transform_json(json_files)
    download_by_urls(dataset, args.output_path)
    log.info(f"Download file for urls success...")