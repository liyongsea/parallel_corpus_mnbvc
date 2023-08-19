"""
1.从excel获取网址(pandas)
2.自动获取cookie（requests）
3.下载doc文件
"""


import pandas as pd
import requests as re
import os
from datasets import load_dataset

list=input("输入链接列表路径：")
save=input("输入文件存储路径：")

"""——————1.获取Excel中文件个数——————"""
df = pd.read_excel(list,sheet_name='Sheet1')
row = df.shape[0]#得到行数（文件中加入表头）

"""——————2.自动获取cookie——————"""
sesObject = re.session()#创建session对象以保持cookie
reqRes = sesObject.post(url="https://documents.un.org/prod/ods.nsf/home.xsp")#进入主页面获取cookie
cook = sesObject.cookies
print("文件总数；",row,", 下载开始：",'\n')

"""——————3.循环识别，判断是否为doc并下载——————"""
i = 0# i为当前行
j = 0# j为下载数
while i < row:
    urln = df.iloc[i, 2]  # 当前行文件（文件中加入表头）
    # 识别url，文件格式以及文件全名
    print("当前url:", urln)
    ju = urln[-3:]
    nameFile = urln[-12:]

    # 下载网页内容
    res = re.get(urln, cookies=cook)
    if res.status_code == 200:
        print("网页请求成功")

    namePath = os.path.join(save, nameFile)
    print(namePath)

    with open(namePath, 'wb') as f:
        f.write(res.content)#写入doc
        j=j+1

    print(nameFile, "下载完成",'\n')
    i = i + 1

print("下载结束,文件总数：",row,"个,共下载",j,"个文件,存储位置",save)