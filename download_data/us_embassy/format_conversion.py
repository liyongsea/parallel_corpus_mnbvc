import argparse
import logging
import datasets

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')

def convert_dataset_row(row):
    for lang in row:
        row[lang] = row[lang].splitlines()
    return row

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='美国大使馆数据转化成对齐所需要的格式脚本')
    parser.add_argument('--downloaded_data_file', default="data.csv", help='输出csv的文件名')
    
    args = parser.parse_args()
    
    downloaded_data_file = args.downloaded_data_file
    
    dataset = datasets.Dataset.from_csv(downloaded_data_file)
    
    dataset.save_to_disk("./us_embassy_converted")
    
    