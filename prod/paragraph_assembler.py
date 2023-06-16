import argparse
import datasets
import json
import time
import random
import os
from filelock import FileLock


RECORD_INDEX_MAP_FILE_LOACATION = f"{os.path.dirname(os.path.abspath(__file__))}/record_index_map.json"
LOCK_FILE_LOCATION = f"{os.path.dirname(os.path.abspath(__file__))}/record_index_map.json.lock"

class ParagraphAssembler:

    def __init__(self, test=False):
        
        if test:
            self.record, self.dataset_row = self.get_dataset_row()
            print(f"{self.record} start")
            self.done_in_json_settings_file()
            print(f"{self.record} success")
        

    def done_in_json_settings_file(self):
        """
        In the json file set the current file is done

        """
        with FileLock(LOCK_FILE_LOCATION):
            with open(RECORD_INDEX_MAP_FILE_LOACATION, "r+") as f:
                try:
                    record_index_map = json.load(f)
                except:
                    time.sleep(random.uniform(0, 5))
                    return

                record_index_map[self.record]["completed"] = True

                f.seek(0)
                f.truncate()
                json.dump(record_index_map, f)
                f.flush()

    def get_dataset_row(self):
        """
        Get unused rows in datasets

        Returns: 
            record: file record number
            dataset_row: dict('zh', 'en', 'fr', 'es', 'ru', 'record')

        """
        with FileLock(LOCK_FILE_LOCATION):
            with open(RECORD_INDEX_MAP_FILE_LOACATION, "r+") as f:
                try:
                    record_index_map = json.load(f)
                except:
                    time.sleep(random.uniform(0, 5))
                    return

                prepare_dataset_index = None
                for record in record_index_map:
                    completed = record_index_map[record]["completed"]
                    processing = record_index_map[record]["processing"]

                    if not (completed or processing):
                        prepare_dataset_index = record_index_map[record]["index"]
                        record_index_map[record]["processing"] = True
                        break

                f.seek(0)
                f.truncate()
                json.dump(record_index_map, f)
                f.flush()

                dataset = datasets.load_dataset("ranWang/un_pdf_text_data_test")["randomTest10000"]
                return record, dataset[prepare_dataset_index]

    def start(self, key):
        pass

    def post_process(self):
        pass

    def batch_post_process(self):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', type=str, default=False, help='openai api key')
    parser.add_argument('--test', type=str, default=False, help='是否测试此脚本')

    args = parser.parse_args()
    key = args.key

    paragraphAssembler = ParagraphAssembler(args.test)
