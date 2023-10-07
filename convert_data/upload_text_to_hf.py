
import os
import pickle
import re
import datasets

BASE_DIR = r'E:\motrixDL\baiduyun\MNBVC'
SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'

WPF_MAP_DIR = BASE_DIR + r'\wpf_mapping.pkl'
DOC_MAP_DIR = BASE_DIR + r'\doc_mapping.pkl'

CONVERTED_TEXT_DIRS = [
    BASE_DIR + r'\docxoutput_text',
    BASE_DIR + r'\docxoutput2_text',
    BASE_DIR + r'\wpf_err_recovered_text',
    BASE_DIR + r'\wpf_libre_converted_text',
]

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket


def read_secret(key: str) -> str:
    v = os.environ[key] = os.environ.get(key) or input(f"Please input {key}:")    
    return v

use_proxy()

# dir_map = {}


# lang_map = {
#     '阿拉伯文': 'ar',
#     '中文': 'zh',
#     '英文': 'en',
#     '法文': 'fr',
#     '俄文': 'ru',
#     '西班牙文': 'es',
#     '德国': 'de',
# }
# record_mapping = {}

# with open(WPF_MAP_DIR, 'rb') as f:
#     wpf_mapping = pickle.load(f)
#     for k, v in wpf_mapping.items():
#         for w in v:
#             dir_map[w[:-4]] = k
# del wpf_mapping

# with open(DOC_MAP_DIR, 'rb') as f:
#     doc_mapping = pickle.load(f)
#     for k, v in doc_mapping.items():
#         for w in v:
#             dir_map[w[:-4]] = k
# del doc_mapping
# # print(dir_map)

# text_scan_pat = re.compile(r'[^\[\]\s]', re.M)
# dataset = []

# for src_dir in CONVERTED_TEXT_DIRS:
#     for i in os.listdir(src_dir):
#         key = i[:-4]
#         if key not in dir_map:
#             continue
#         src = os.path.join(src_dir, i)
#         with open(src, 'r', encoding='utf-8') as f:
#             text = f.read().strip()
        
#         if not text:
#             continue
#         if text == '''Http Status Code: 404

# Reason: File not found or unable to read file''':
#             continue
#         if not re.search(text_scan_pat, text):
#             continue
        
#         rec = dir_map[key]
#         lang = lang_map[key.split('-')[0]]
#         if rec not in record_mapping:
#             record_mapping[rec] = len(record_mapping)
#             dataset.append({
#                 'ar': '',
#                 'zh': '',
#                 'en': '',
#                 'fr': '',
#                 'ru': '',
#                 'es': '',
#                 'de': '',
#                 'record': rec,
#             })
#         dataset[record_mapping[rec]][lang] = text

# with open(BASE_DIR + r'\text_dataset.pkl', 'wb') as f:
#     pickle.dump(dataset, f)

with open(BASE_DIR + r'\text_dataset.pkl', 'rb') as f:
    dataset = pickle.load(f)

def batch_dataset(): yield from dataset

dataset = datasets.Dataset.from_generator(batch_dataset)
dataset.push_to_hub(repo_id='undl_text', split='train', token=read_secret('HF_TOKEN'))

ds = datasets.load_from_disk(r'C:\Users\Administrator\.cache\huggingface\datasets\generator\default-e07f48af7c626364\0.0.0')