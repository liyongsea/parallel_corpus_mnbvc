"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""

import argparse as ap
import threading as th
import pandas as pd
import requests as re
import time
import os
import numpy

from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue
from threading import Thread
from datasets import load_dataset
from functools import partial

# 'dabaisuv/UN_Documents_2000_2023'

class CookieManager:
    def __init__(self):
        self.session = re.session()
        self.cookie_refresh_interval = 600  # 设定每隔1分钟（600秒）刷新一次cookie
        self.last_refresh_time = time.time() - self.cookie_refresh_interval - 1  # 使得第一次请求能够获取cookie

    def get_cookie(self):
        current_time = time.time()
        if current_time - self.last_refresh_time > self.cookie_refresh_interval:
            self.refresh_cookie()
            self.last_refresh_time = current_time
        return self.session.cookies

    def refresh_cookie(self):
        response = self.session.post(url="https://documents.un.org/prod/ods.nsf/home.xsp", timeout=30)
        if response.status_code != 200:
            raise ValueError("cookie请求失败。状态码: {}".format(response.status_code))

def get_dataset(link):
    dataset = load_dataset(link)
    return dataset

def get_tuple(dataset,n):#————取字典第n条内容建立一个元组————
    url = dataset["train"][n]['链接']#取url
    code = dataset["train"][n]['文号']#取文号
    if code is None:
        print(f"Warning: '文号' value is None for index {n}")
        return None

    code = code.replace("/","_")
    code = code.replace("\\", "_")
    langue=dataset["train"][n]['语言']#取名
    tuple_u_n=(url,code,langue)
    return tuple_u_n

def mkdir(path):#————创建目录文件夹————
    path=path.strip()
    path=path.rstrip("\\")
    Path(path).mkdir(exist_ok=True)

# def get_cookie():#————自动获取cookie————
#     sesObject = re.session()#创建session对象以保持cookie
#     reqRes = sesObject.post(url="https://documents.un.org/prod/ods.nsf/home.xsp")#进入主页面获取cookie
#     cook = sesObject.cookies
#     return(cook)

def is_valid_content(content):# 将二进制内容转为字符串来检查是否包含HTTP或BODY标签
    content_str = content.decode('utf-8', errors='ignore')  # 将二进制内容转为字符串
    if '<!doctype html public ' in content_str.lower() and '<html>' in content_str.lower() and '<head>' in content_str.lower():
        print('false')
        return False
    return True

def run(tuple_start,cookie_n,save_path):#————下载线程————
    urln = tuple_start[0]
    code_n = tuple_start[1]
    langue_n = tuple_start[2]
    try:
        d_file(urln, code_n, langue_n, cookie_n, save_path)
    except ValueError:
        print(urln,"下载失败")
        raise



def d_file(urln, code_n, langue_n, cookie_n, save_path):  # ————下载单个文档————

    file_extension = os.path.splitext(urln)[-1].lower()

    # 确保文件后缀为 .wpf 或 .doc
    if file_extension not in ['.wpf', '.doc']:
        raise ValueError(f"{file_extension}路径无效")

    nameFile = langue_n + "-" + urln[-12:]
    menu_path = os.path.join(save_path, code_n)
    namePath = os.path.join(menu_path, nameFile)

    res = re.get(urln, cookies=cookie_n)

    if is_valid_content(res.content) == False:
        raise ValueError
    else:
        mkdir(menu_path)
        with open(namePath, 'wb') as f:
            f.write(res.content)  # 写入doc
            res.raw.close()
    return

#————————————主程序————————————
if __name__ == '__main__':

#从命令行获取存储路径
    parser = ap.ArgumentParser(description="用以指定地址存储")#parser创建了arg_parser对象,字符串在生成的帮助信息中显示
    parser.add_argument("-o","--output_file",help="输出文件的路径")#添加一个--output_file的位置参数，--说明其为可选参数，简写为-o
    args= parser.parse_args()
    save_path=args.output_file
    # save_path="E:\MNBVC"
    print("输出路径",save_path)

#获取cookie
    cookie_manager = CookieManager()
    try:
        cookie_n=cookie_manager.get_cookie()
    except ValueError:
        print("cookie请求失败.")
#从网页上获取链接数据
    link = 'dabaisuv/UN_Documents_2000_2023'
    dataset = get_dataset(link)

    num_row = len(dataset["train"]['链接'])  #测试行数20
    print("链接获取完成")


#多线程尝试
    queue = Queue()#下载任务队列

    for i in range(0,num_row): #构造一个行数个的任务队列（测试20个）
        tuple_UN = get_tuple(dataset,i)
        if tuple_UN is not None:
            queue.put(tuple_UN)#向任务队列中置入元组
    print("任务创建完成，开始下载：开始大小 %d" % queue.qsize())#开始时显示大小 正确

    max_errors = 10
    error_count = 0

    with ThreadPoolExecutor(max_workers=36) as executor:
        futures = []
        for task in range(queue.qsize()):
            partial_process_row = partial(run, tuple_start=queue.get(), cookie_n=cookie_n, save_path=save_path)
            futures.append(executor.submit(partial_process_row))

        for future in tqdm(as_completed(futures), total=num_row, desc="下载进度", unit_scale=True):
            try:
                future.result()  # 这会抛出任何由线程引起的异常
            except ValueError:
                print("下载失败")
                error_count += 1
                if error_count == max_errors:
                    executor.shutdown(wait=False)
                    print("超过错误阈值，终止所有线程")
                    break  # 退出for循环


    print(f"总共有 {error_count} 个文件下载失败。")
    print("queue 结束大小 %d"%queue.qsize())
