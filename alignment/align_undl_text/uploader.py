import os
from pathlib import Path
import datasets

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

def read_secret(key: str) -> str:
    v = os.environ[key] = os.environ.get(key) or input(f"Please input {key}:")    
    return v

SRC = 'de'
DST = 'en'

DUMP_TRANSLATION_PATH = Path(rf'F:\dump_tr_{SRC}2{DST}')
METHOD2_PREVIEW_DS_PATH = Path(rf'F:\method2_ds_{SRC}2{DST}')

if __name__ == '__main__':
    # ds = datasets.load_from_disk(DUMP_TRANSLATION_PATH)
    # ds.push_to_hub(repo_id=f'undl_{SRC}2{DST}_translation', split='train', token=read_secret('HF_TOKEN'), )
    ds = datasets.load_from_disk(METHOD2_PREVIEW_DS_PATH)
    ds.push_to_hub(repo_id=f'undl_{SRC}2{DST}_aligned_mk2', split='train', token=read_secret('HF_TOKEN'), )
    # use_proxy()

