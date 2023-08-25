"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""

import argparse as ap
import pandas as pd
import requests as re
import threading as th
import time
import os
import sys
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
        self.cookie_refresh_interval = 3600  # 设定每隔1小时（3600秒）刷新一次cookie
        self.last_refresh_time = time.time() - self.cookie_refresh_interval - 1  # 使得第一次请求能够获取cookie

    def get_cookie(self):
        current_time = time.time()
        if current_time - self.last_refresh_time > self.cookie_refresh_interval:
            self.refresh_cookie()
            self.last_refresh_time = current_time
        return self.session.cookies

    def refresh_cookie(self):
        self.session.post(url="https://documents.un.org/prod/ods.nsf/home.xsp")

def get_dataset(link):
    dataset = load_dataset(link)
    return dataset

def get_tuple(dataset,n):#————取字典第n条内容建立一个元组————

    url = dataset["train"][n]['链接']#取url
    code = dataset["train"][n]['文号']#取文号
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


def run(tuple_start,cookie_n,save_path):#————下载线程————
    urln = tuple_start[0]
    code_n = tuple_start[1]
    langue_n = tuple_start[2]
    d_file(urln, code_n, langue_n, cookie_n, save_path)

def is_valid_content(content):
    # 将二进制内容转为字符串来检查是否包含 "HTTP"
    if "HTTP" in content.decode('utf-8', errors='ignore'):
        return False
    return True


def d_file(urln, code_n, langue_n, cookie_n, save_path):  # ————下载单个文档————

    file_extension = os.path.splitext(urln)[-1].lower()

    # 确保文件后缀为 .wpf 或 .doc
    if file_extension not in ['.wpf', '.doc']:
        raise ValueError(f"The file extension {file_extension} is not supported.")


    nameFile = langue_n + "-" + urln[-12:]
    menu_path = os.path.join(save_path, code_n)
    mkdir(menu_path)
    namePath = os.path.join(menu_path, nameFile)

    res = re.get(urln, cookies=cookie_n)

    # 检查内容是否有效
    if not is_valid_content(res.content):
        raise ValueError(f"The content downloaded from {urln} seems to be invalid or an error page.")

    with open(namePath, 'wb') as f:
        f.write(res.content)  # 写入doc

    # print("当前url:", urln,nameFile, "下载完成", '\n')
    return

#————————————主程序————————————
if __name__ == '__main__':
    print("start")

#从命令行获取存储路径
    parser = ap.ArgumentParser(description="用以指定地址存储")#parser创建了arg_parser对象,字符串在生成的帮助信息中显示
    parser.add_argument("-o","--output_file",help="输出文件的路径")#添加一个--output_file的位置参数，--说明其为可选参数，简写为-o
    args= parser.parse_args()
    save_path=args.output_file
    print("输出路径",save_path)

#从网页上获取链接数据
    cookie_manager = CookieManager()
    link = 'dabaisuv/UN_Documents_2000_2023'
    dataset = get_dataset(link)
    num_row = len(dataset["train"]['链接'])
    test = num_row

#获取cookie
    cookie_n=cookie_manager.get_cookie()

#多线程尝试
    queue = Queue()#下载任务队列

    for i in range(0,test): #构造一个行数个的任务队列（测试20个）
        tuple_UN = get_tuple(dataset,i)
        queue.put(tuple_UN)#向任务队列中置入元组 正确
    print("queue 开始大小 %d" % queue.qsize())#开始时显示大小 正确

    with ThreadPoolExecutor(max_workers=36) as executor:
        futures = []
        for task in range(queue.qsize()):
            partial_process_row = partial(run, tuple_start=queue.get(), cookie_n=cookie_n, save_path=save_path)
            futures.append(executor.submit(partial_process_row))

        for future in tqdm(as_completed(futures), total=test, desc="下载进度", unit_scale=True):
            pass

    print("queue 结束大小 %d"%queue.qsize())
    j = test-queue.qsize()

    # print("读取存储路径时间",t1,"秒，获取数据库时间",t2,"秒，获取cookie时间",t3,"秒，构建任务队列1时间",t3_5,"秒，写入任务队列时间",t4/60,"分，写入时间",t5,"秒")
    # print("下载结束,文件总数：",num_row,"个,共下载",j,"个文件，用时",time_sum/60,"分，存储位置",save_path)