"""
本代码用于演示我们是如何从数据源进行一步步操作从而得到数据集

出于简洁明了的目的，不会针对各个环节的效率进行优化

实际实践所用代码可以参照https://wiki.mnbvc.org/doku.php/pxyl中留档的代码
"""
from pathlib import Path
import os

os.environ['OPENSSL_CONF'] = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\openssl.cnf'
# 打开SSL重新协商，https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled
import requests
import re
import pickle

def get_doc_list_from_datetime_range(from_date='2000-01-01',to_date='2024-01-03'):
    session = requests.session()
    headers = {
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Host': 'documents.un.org',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
        'Origin': 'https://documents.un.org',
    }
    page = 0


    data = {
        "view:_id1:_id2:txtSymbol":"",
        "view:_id1:_id2:rgTrunc":"R",
        "view:_id1:_id2:txtWrds":"",
        "view:_id1:_id2:txtSubj":"",
        "view:_id1:_id2:dtPubDateFrom":"",
        "view:_id1:_id2:dtPubDateTo":"",
        "view:_id1:_id2:dtRelDateFrom":from_date,
        "view:_id1:_id2:dtRelDateTo":to_date,
        "view:_id1:_id2:txtJobNo":"",
        "view:_id1:_id2:txtSess":"",
        "view:_id1:_id2:txtAgItem":"",
        "view:_id1:_id2:txtFTSrch":"",
        "view:_id1:_id2:cbType":"FP",
        "view:_id1:_id2:cbSort":"R",
        "view:_id1:_id2:hdnSubj":"",
        "$$viewid":"!akj84efbvsyavfcz3ciemq6hk!",
        "$$xspsubmitid: view:_id1:_id2":"id131",
        "$$xspexecid":"",
        "$$xspsubmitvalue":"",
        "$$xspsubmitscroll":"0|300",
        "view:_id1: view":"id1"
    }
    
    # resp = session.get('https://documents.un.org/prod/ods.nsf/home.xsp', headers=headers)

    # view_id_pattern = re.compile(r"""<input type="hidden" name="\$\$viewid" id="view:_id1__VUID" value="(.*?)">""", re.M)
    # data["$$viewid"] = view_id_pattern.findall(resp.text)[0]

    # resp = session.post('https://documents.un.org/prod/ods.nsf/home.xsp', headers=headers, data=data)

    # with open('tmpreq1.pkl', 'wb') as f:
    #     pickle.dump(resp, f)

    with open('tmpreq1.pkl', 'rb') as f:
        resp = pickle.load(f)

    print(resp.text)

    # response = session.get(
    #     'https://documents.un.org/prod/ods.nsf/xpSearchResultsM.xsp?$$ajaxid=view%3A_id1%3A_id2%3AcbMain%3AmainPanel',
    #     headers=headers,
    #     data=data,
    # )
    # print("raw1:",response.text)

    # with open('tmpreq.pkl', 'wb') as f:
    #     pickle.dump(response, f)

    # # with open('tmpreq.pkl', 'rb') as f:
    # #     response = pickle.load(f)
    # raw = response.text
    # print("raw:",raw)
    

def download_doc_from_net(timeout=30):
    """
    数据源下载，经调研，发现https://documents.un.org/prod/ods.nsf/home.xsp内含有doc格式文件
    """
    session = requests.session()
    session.post("https://documents.un.org/prod/ods.nsf/home.xsp")

def doc2docx():
    """
    将doc格式文件转换为docx格式文件。
    """

def wpf2docx():
    """
    将wpf格式文件转换为docx格式文件。
    """

def docx2txt():
    """
    将docx格式文件转换为txt格式文件。
    """

def translate():
    """
    文本翻译
    """

def align():
    """
    文本对齐
    """

if __name__ == '__main__':
    get_doc_list_from_datetime_range()