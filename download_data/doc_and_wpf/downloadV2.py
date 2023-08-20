"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""
import datadict as datadict
import pandas as pd
import requests as re
import queue as  qu
import time
import os
from datasets import load_dataset

# 'dabaisuv/UN_Documents_2000_2023'
def g_dict(link):#————取字典最后一列————
    dataset = load_dataset(link)
    dataset_n = dataset["train"]['链接']
    return(dataset_n)
def g_url(dset_n,n):#————取url————
    res = dset_n[n]
    return(res)
def g_cookie():#————自动获取cookie————
    sesObject = re.session()#创建session对象以保持cookie
    reqRes = sesObject.post(url="https://documents.un.org/prod/ods.nsf/home.xsp")#进入主页面获取cookie
    cook = sesObject.cookies
    return(cook)
def d_file(urln,cook,savePath):#————下载单个文档————
        ju = urln[-3:]
        nameFile = urln[-12:]
        namePath = os.path.join(savePath, nameFile)

        res = re.get(urln, cookies=cook)
        with open(namePath, 'wb') as f:
            f.write(res.content)#写入doc
        print("当前url:", urln, "下载完成",'\n')
        return

if __name__ == '__main__':

    link = 'dabaisuv/UN_Documents_2000_2023'

    d_set = g_dict(link)
    num_row = len(d_set)

    save = input("输入文件存储路径：")

    cookie_n=g_cookie()

    i = 0  # i为当前行
    while i < num_row:                           #测试数量20,实用替换为num_row
        urln = g_url(d_set, i)
        d_file(urln,cookie_n,save)
        i=i+1

    print("下载结束,文件总数：",num_row,"个,共下载",i,"个文件,存储位置",save)