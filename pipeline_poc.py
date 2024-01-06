"""
本代码用于演示我们是如何从数据源进行一步步操作从而得到数据集

出于简洁明了的目的，不会针对各个环节的效率进行优化

实际实践所用代码可以参照https://wiki.mnbvc.org/doku.php/pxyl中留档的代码
"""
import argparse
import json
import subprocess
import sys
import logging

from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ROOT_DIR = Path(__file__).parent


def run_script(script, args):
    subprocess.run([sys.executable, script] + args)


def load_config(config_file: str):
    with open(config_file, 'r') as file:
        return json.load(file)
    

def download(script, args):
    """
    数据源下载，经调研，发现https://documents.un.org/prod/ods.nsf/home.xsp内含有doc格式文件
    """
    run_script(script, args)


def format_conversion(script, args):
    """
    将download下载的数据格式转化成对齐所需要的格式，
    可能会包含以下函数：doc2docx、wpf2docx、docx2txt
    """
    run_script(script, args)


def align(script, args):
    """
    文本对齐，此方法中需要先执行翻译，然后进行对齐
    """
    # run_script(script, args)

    def translate():
        """
        文本翻译
        """


def main(config_file: Path):
    config = load_config(config_file)

    parser = argparse.ArgumentParser(description='总线脚本')
    parser.add_argument('identifier', help='网站标识符，例如 "us_embassy"')
    args, unknown_args = parser.parse_known_args()
    
    script = next((item['script'] for item in config if item['identifier'] == args.identifier), None)
    if not script:
        print(f"未找到标识符为 '{args.identifier}' 的配置。")
        sys.exit(1)
    
    logging.info(f"Downloading '{args.identifier}' data is processing...")
    # download(script["downlaod"], unknown_args)
    logging.info(f"Downloading '{args.identifier}' data is successed!")
    
    logging.info(f"'{args.identifier}' format converting...")
    format_conversion(script["format_conversion"], unknown_args)
    logging.info(f"'{args.identifier}' format converted!")
    
    logging.info(f"'{args.identifier}' is aligning...")
    align(script["algnment"], unknown_args)
    logging.info(f"'{args.identifier}' is align completed!")
    
    print(script)


if __name__ == '__main__':
    # 配置文件的路径
    config_file = ROOT_DIR / 'config.json'

    main(config_file)
