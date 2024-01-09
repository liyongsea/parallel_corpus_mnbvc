"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""

import argparse as ap
import threading as th
import requests as re
import os
import time
import schedule
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from datasets import load_dataset
from functools import partial
from datetime import datetime
from pathlib import Path

class CookieManager:
    """
    管理session中的cookies。
    """
    
    def __init__(self):
        """
        初始化session和最后的cookie属性。
        """
        self.session = re.Session()
        self.last_cookie = None

    def get_cookie(self):
        """
        从目标URL请求并获取新的cookie。

        返回:
            session.cookies: 返回会话的cookies。

        异常:
            ValueError: 如果获取cookie的请求失败。
        """
        response = self.session.post(url="https://documents.un.org/prod/ods.nsf/home.xsp", timeout=30)
        if response.status_code != 200:
            raise ValueError("cookie请求失败。状态码: {}".format(response.status_code))

        current_cookie = dict(self.session.cookies)  # 将cookie转换为字典形式

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 现在时间

        if self.last_cookie == self.session.cookies: #对比是否更新
            print(f"\n{current_time} -cookie更新失败")
        else:
            print(f"\n{current_time} -cookie更新成功")
            self.last_cookie = self.session.cookies

        return self.session.cookies

class Downloader:
    """
    处理下载操作。
    """
    def __init__(self, save_path):
        """
        使用给定的保存路径初始化下载器，并安排刷新cookie。
        """
        self.save_path = save_path

        self.refresh_cookie()
        # Todo: 生产/merge 时记得改一下，现在是10s一刷新
        schedule.every(10).seconds.do(self.refresh_cookie)

    def refresh_cookie(self):
        """
        使用CookieManager刷新cookie。
        """
        cookie_manager = CookieManager()
        self.cookie_n = cookie_manager.get_cookie()

    def run(self,stop_event, tuple_start):
        """
        运行下载进程。

        返回:
            bool: 如果下载成功，则返回True，否则返回字符串"error"。
        """
        if stop_event.is_set():
            return

        urln = tuple_start[0]
        code_n = tuple_start[1]
        langue_n = tuple_start[2]

        try:
            tuple_path = self.set_path(urln, code_n, langue_n, self.save_path)
            self.d_file(urln, tuple_path)
            return True
        except ValueError:
            print(urln, "下载失败")
            return "error"

    def set_path(self,urln, code_n, langue_n, save_path):
        """
        根据给定的参数设置文件路径。

        返回:
            tuple: 包含目录和文件路径的元组。
        """
        file_extension = os.path.splitext(urln)[-1].lower()

        # 确保文件后缀为 .wpf 或 .doc
        if file_extension not in ['.wpf', '.doc']:
            raise ValueError(f"{file_extension}路径无效")

        name_File = langue_n + "-" + urln[-12:]
        menu_path = os.path.join(save_path, code_n)
        name_path = os.path.join(menu_path, name_File)
        tuple_path = (menu_path, name_path)

        return tuple_path

    def mkdir(path):
        """
        在给定的路径创建一个目录。

        参数:
            path (str): 要创建的目录的路径。
        """
        Path(path).mkdir(parents=True, exist_ok=True)

    def is_valid_content(content):
        """
        检查内容是否为有效的非HTML内容。将二进制内容转为字符串来检查是否包含HTTP或BODY标签———— 正确

        返回:
            bool: 如果有效，则为True，否则为False。
        """

        content_str = content.decode('utf-8', errors='ignore')  # 将二进制内容转为字符串
        if '<!doctype html public ' in content_str.lower() \
                       and '<html>' in content_str.lower() \
                       and '<head>' in content_str.lower():
            print('html格式的文件')
            return False
        return True

    def d_file(self,urln,tuple_path):
        """
        下载单个文件。

        参数:
            urln (str): 要下载的文件的URL。
            tuple_path (tuple): 包含目录和文件路径的元组。

        异常:
            ValueError: 如果内容无效。
        """
        menu_path = tuple_path[0]
        name_path = tuple_path[1]

        res = re.get(urln, cookies=self.cookie_n) # 获取文本内容

        if Downloader.is_valid_content(res.content) == False: # 判断文本是否正确
            raise ValueError
        else: # 创建文件夹，创建路径并写入
            Downloader.mkdir(menu_path)
            with open(name_path, 'wb') as f:
                f.write(res.content)  # 写入doc
                res.raw.close()
        return

def schedule_runner(finish_event): # 每秒检查一次cookie获取
    """
    定期运行计划任务，每秒检查一次是否需要根据 finish_event 标志停止。

    参数：
        - finish_event (Event): 一个事件，用于指示何时停止计划运行器。
        
    使用：
        - schedule: 一个应该被导入以处理调度的模块。
        - time: 一个应该被导入以处理时间操作的模块。

    """
    while not finish_event.is_set():
        schedule.run_pending()
        time.sleep(1)

def get_dataset(link):
    """
    从给定的链接获取数据集。

    参数：
        - link (str): 用于获取数据集的链接。
        
    使用：
        - load_dataset: 一个函数，应定义为从链接加载数据集。

    返回：
        - dataset: 从链接获取的数据集。
    """
    dataset = load_dataset(link)
    return dataset

def get_tuple(dataset,n): # ————取字典第n条内容建立一个元组————
    """
    创建一个包含从数据集的第n个条目中提取的数据的元组。

    参数：
        - dataset (dict): 表示数据集的字典。
        - n (int): 要提取数据的条目的索引。
        
    返回：
        - tuple_u_n (tuple): 包含第n个条目的URL、代码和语言的元组。
        - None: 如果第n个条目在数据集中的'文号'值为None。
    """
    url = dataset["train"][n]['链接'] # 取url
    code = dataset["train"][n]['文号'] # 取文号
    if code is None:
        print(f"Warning: '文号' value is None for index {n}")
        return None

    code = code.replace("/","_")
    code = code.replace("\\", "_")
    langue=dataset["train"][n]['语言'] # 取名
    tuple_u_n=(url,code,langue)
    return tuple_u_n

def main(dataset, save_path):
    print("输出路径",save_path)

    # 调用下载类
    downloader = Downloader(save_path=save_path)

    num_row = len(dataset)
    print("链接获取完成")

    # 多线程
    queue = Queue() # 下载任务队列
    max_workers = 2 # 线程数
    max_errors = 10 # 最大错误数量
    error_count = 0 # 错误计数变量
    stop_event = th.Event() # 终止事件
    finish_event = th.Event() # 全局结束事件

    cookie_thread = th.Thread(target=schedule_runner, args=(finish_event,)) # 检测获取cookie时间
    cookie_thread.start()

    # 构造一个行数个的任务队列（测试N个）num_row个
    for i in range(0,2000): 
        tuple_UN = get_tuple(dataset,i)
        if tuple_UN is not None:
            queue.put(tuple_UN) # 向任务队列中置入元组

    print("任务创建完成，开始下载：开始大小 %d" % queue.qsize()) # 开始时显示大小 正确

    with ThreadPoolExecutor(max_workers) as executor:
        futures = []

        for _ in range(queue.qsize()):
            partial_process_row = partial(downloader.run, stop_event, tuple_start=queue.get())
            futures.append(executor.submit(partial_process_row))

        for future in tqdm(as_completed(futures), total=num_row, desc="下载进度", unit_scale=True):
            if error_count >= max_errors:
                break

            result = future.result()#检查错误代码
            if result == "error":
                error_count += 1
                if error_count == max_errors:
                    stop_event.set()
                    executor.shutdown(wait=False)
                    print("超过错误阈值，终止所有线程")

    finish_event.set()
    cookie_thread.join()

    print(f"总共有 {error_count} 个文件下载失败。")
    print("queue 结束大小 %d"%queue.qsize())
