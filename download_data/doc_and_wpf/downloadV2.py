"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""

import argparse as ap
import pandas as pd
import requests as re
import threading as th
import queue as  qu
import time
import os
import numpy
from queue import Queue
from threading import Thread
from datasets import load_dataset

# 'dabaisuv/UN_Documents_2000_2023'
dictname=dict()

def get_dataset(link):
    dataset = load_dataset(link)
    return dataset
def get_tuple(dataset,n):#————取字典第n条内容建立一个元组————
    url = dataset["train"]['链接'][n]#取url
    code = dataset["train"]['文号'][n]#取文号
    code = code.replace("/","_")
    code = code.replace("\\", "_")
    langue=dataset["train"]['语言'][n]#取名
    tuple_u_n=(url,code,langue)
    return tuple_u_n

# def get_url(dataset,n):#————取url————
#     dset_url = dataset["train"]['链接']
#     res_url = dset_url[n]
#     print(res_url)
#     return(res_url)
#
# def set_name_start(dataset,ns):#————取名————
#     name = dataset["train"]['文号'][ns]+"-"+dataset["train"]['语言'][ns]
#     return(name)
def mkdir(path):#————创建目录文件夹————
    path=path.strip()
    path=path.rstrip("\\")
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path)
        print(path+' 创建成功')
        return
    else:
        print(path+' 目录已存在')
        return


def g_cookie():#————自动获取cookie————
    sesObject = re.session()#创建session对象以保持cookie
    reqRes = sesObject.post(url="https://documents.un.org/prod/ods.nsf/home.xsp")#进入主页面获取cookie
    cook = sesObject.cookies
    return(cook)



# def write(in_q_t,dataset,n,a):#————写入线程————
#     while in_q_t.qsize() != a:
#         tuple_UN=get_tuple(dataset,n)
#         queue.put(tuple_UN)  # 向任务队列中置入元组 正确
#         in_q.task_done()
def run(in_q,cookie_n,save_path):#————下载线程————
    while in_q.empty() is not True:
        tuple_start = in_q.get(tuple_UN)
        urln = tuple_start[0]
        code_n = tuple_start[1]
        langue_n=tuple_start[2]
        d_file(urln, code_n, langue_n, cookie_n, save_path)
        in_q.task_done()

def d_file(urln, code_n, langue_n, cookie_n, save_path):  # ————下载单个文档————
    ju = urln[-3:]
    nameFile = langue_n + "-" + urln[-12:]
    menu_path = os.path.join(save_path, code_n)
    mkdir(menu_path)
    namePath = os.path.join(menu_path, nameFile)

    res = re.get(urln, cookies=cookie_n)
    with open(namePath, 'wb') as f:
        f.write(res.content)  # 写入doc
    print("当前url:", urln, "下载完成", '\n')
    return

#————————————主程序————————————
if __name__ == '__main__':
#计时
    time_s=time.perf_counter()
    test = 120
#从命令行获取存储路径
    parser = ap.ArgumentParser(description="用以指定地址存储")#parser创建了arg_parser对象,字符串在生成的帮助信息中显示
    parser.add_argument("-o","--output_file",help="输出文件的路径")#添加一个--output_file的位置参数，--说明其为可选参数，简写为-o
    args= parser.parse_args()
    save_path=args.output_file
    print("输出路径",save_path)

    time_1=time.perf_counter()

#从网页上获取链接数据
    link = 'dabaisuv/UN_Documents_2000_2023'
    dataset = get_dataset(link)
    num_row = len(dataset["train"]['链接'])
    print(num_row)

    time_2=time.perf_counter()
#获取cookie
    cookie_n=g_cookie()

    time_3=time.perf_counter()
#多线程尝试
    # queue_name = Queue()#写入元组队列
    queue = Queue()#下载任务队列

    # # result_queue=Queue()#结果队列
    # for i in range(0,20): #构造一个行数个的任务队列（测试20个）
    #     for index1 in range(10):  # 使用10个线程来消化写入元组队列
    #         thread = Thread(target=write, args=(queue_name, dataset,i,20,))
    #         thread.daemon = True
    #         thread.start()
    #
    # queue_name.join()

    # tu = numpy.array([0 for t in range[20]])
    # for k in range(0, test):  # 构造一个行数个的任务队列（测试20个）
    #     tuple_UN = get_tuple(dataset, k)
    #     tu[i]=tuple_UN

    time_3_5 = time.perf_counter()

    for i in range(0,test): #构造一个行数个的任务队列（测试20个）
        tuple_UN = get_tuple(dataset,i)
        print(tuple_UN)
        queue.put(tuple_UN)#向任务队列中置入元组 正确
    print("queue 开始大小 %d" % queue.qsize())#开始时显示大小 正确

    time_4=time.perf_counter()

    for index in range(50):#使用50个线程来消化任务队列
        thread = Thread(target=run,args=(queue,cookie_n,save_path,))
        thread.daemon=True
        thread.start()

    queue.join()#队列处理完，线程结束


#下载文件
    # i = 0  # i为当前行
    # while i < 50:                           #测试数量20,实用替换为num_row
    #     urln = g_url(d_set, i)
    #     d_file(urln,cookie_n,save)
    #     i=i+1

#计时
    time_e=time.perf_counter()
    t1=time_1 - time_s
    t2=time_2 - time_1
    t3=time_3 - time_2
    t3_5=time_3_5 - time_3
    t4=time_4 - time_3_5
    t5=time_e - time_4
    time_sum=time_e - time_s

    print("queue 结束大小 %d"%queue.qsize())
    j = test-queue.qsize()                   #测试20

    print("读取存储路径时间",t1,"秒，获取数据库时间",t2,"秒，获取cookie时间",t3,"秒，构建任务队列1时间",t3_5,"秒，写入任务队列时间",t4/60,"分，写入时间",t5,"秒")
    print("下载结束,文件总数：",num_row,"个,共下载",j,"个文件，用时",time_sum/60,"分，存储位置",save_path)