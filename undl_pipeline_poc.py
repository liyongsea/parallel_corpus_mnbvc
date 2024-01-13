"""
本代码用于演示我们是如何从数据源进行一步步操作从而得到数据集

出于简洁明了的目的，不会针对各个环节的效率进行优化

实际实践所用代码可以参照https://wiki.mnbvc.org/doku.php/pxyl中留档的代码
"""
import json
from pathlib import Path
import os
import re
import pickle
from bs4 import BeautifulSoup

# os.environ['OPENSSL_CONF'] = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\openssl.cnf'
# 打开SSL重新协商，https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import logging as log

log.basicConfig(level=log.DEBUG, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')


def get_all_view_hover_boxs(soup: BeautifulSoup):
    selector = "#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:rptResults .viewHover"
    view_hover_elements = soup.select(selector)
    return view_hover_elements


def parse_view_hover_box_file_link(hover_box_element: BeautifulSoup):
    id = hover_box_element.select_one(".odsText.pull-right.flip").text.strip()
    all_languages_elements = hover_box_element.select(".details div.row.noMargin > div")

    url_with_languages = []
    for language_element in all_languages_elements:
        language = language_element.select_one(".odsTitle").text

        file_element = language_element.select_one("div:nth-of-type(2)")

        pdf_links = file_element.find_all("a", title=lambda title: title and "PDF" in title)
        doc_links = file_element.find_all("a", title=lambda title: title and "Word Document" in title)

        file_links = []

        if pdf_links and len(pdf_links):
            file_links.append({"type": "pdf", "url": pdf_links[0]["href"].replace("?OpenElement", "")})

        if doc_links and len(doc_links):
            file_links.append({"type": "doc", "url": doc_links[0]["href"].replace("?OpenElement", "")})

        url_with_languages.append({"language": language, "file_links": file_links})

    return {"id": id, "url_with_languages": url_with_languages}


def get_all_file_links_by_page(soup: BeautifulSoup):
    """
    Return:
        [{'id': 'S/2012/882', 'url_with_languages': [{'language': 'ARABIC', "file_links": [{'type': 'pdf', 'url': 'xxx'}, {'type': 'pdf', 'url': 'xxx'}, ...]}, ...]
    """
    view_hover_elements = get_all_view_hover_boxs(soup)

    result = []
    for hover_element in view_hover_elements:
        url_with_languages = parse_view_hover_box_file_link(hover_element)
        result.append(url_with_languages)

    return result

def get_total_info(soup) -> (str, str, str, str):
    """
    Return:
        current_start、current_end、total、current_page: 当前轮次开始的数量、当前轮次结束的数量、最大数量、当前的页数。
        这三个值都是str类型的int。
    """
    page_title_info_element = soup.select_one("#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle")
    b_tags = page_title_info_element.find_all("b")

    current_start = b_tags[1].text
    current_end = b_tags[2].text
    total = b_tags[3].text

    page_info_element = soup.select_one(".pagination")
    active_li_tags = page_info_element.select("li.active")
    active_li_tags = list(filter(lambda li: "Group__lnk" in li.select_one("a").get('id'), active_li_tags))
  
    if len(active_li_tags) == 1:
        current_page = active_li_tags[0].text
    else:
        raise ValueError(f"{current_start} -- {current_end}, 不存在页数信息")
    
    return current_start, current_end, total, current_page

SAVE_PATH = Path("un_doc_url_result")
SAVE_PATH.mkdir(exist_ok=True)

def save_data(data, date, page):
    with open(SAVE_PATH / f"{date['from']}--{date['to']}--{page}.json", "w") as f:
        json.dump(data, f)

def get_doc_list_from_datetime_range(from_date="2023-01-01", to_date="2023-01-07"):
    log.debug(f"{from_date} -- {to_date} start...")
    session = requests.session()
    session.headers = {
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Host": "documents.un.org",
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "Origin": "https://documents.un.org",
    }

    data = {
        "view:_id1:_id2:txtSymbol": "",
        "view:_id1:_id2:rgTrunc": "R",
        "view:_id1:_id2:txtWrds": "",
        "view:_id1:_id2:txtSubj": "",
        "view:_id1:_id2:dtPubDateFrom": "",
        "view:_id1:_id2:dtPubDateTo": "",
        "view:_id1:_id2:dtRelDateFrom": from_date,
        "view:_id1:_id2:dtRelDateTo": to_date,
        "view:_id1:_id2:txtJobNo": "",
        "view:_id1:_id2:txtSess": "",
        "view:_id1:_id2:txtAgItem": "",
        "view:_id1:_id2:txtFTSrch": "",
        "view:_id1:_id2:cbType": "FP",
        "view:_id1:_id2:cbSort": "R",
        "view:_id1:_id2:hdnSubj": "",
        "$$viewid": "!akj84efbvsyavfcz3ciemq6hk!",
        "$$xspsubmitid": "view:_id1:_id2:_id131",
        "$$xspexecid": "",
        "$$xspsubmitvalue": "",
        "$$xspsubmitscroll": "0|300",
        "view:_id1": "view:id1",
    }

    resp = session.get( "https://documents.un.org/prod/ods.nsf/home.xsp")

    view_id_pattern = re.compile( r"""<input type="hidden" name="\$\$viewid" id="view:_id1__VUID" value="(.*?)">""", re.M, )
    data["$$viewid"] = view_id_pattern.findall(resp.text)[0]

    multipart_data = MultipartEncoder(fields=data)

    resp = session.post(
        "https://documents.un.org/prod/ods.nsf/home.xsp",
        data=multipart_data,
        headers={"Content-Type": multipart_data.content_type}
    )

    data["$$viewid"] = view_id_pattern.findall(resp.text)[0]

    log.debug(f"page 1 start...")
    soup = BeautifulSoup(resp.text, "html.parser")
    _, current_end, total, page = get_total_info(soup)
    file_links = get_all_file_links_by_page(soup)
    save_data(file_links, {"from": from_date, "to": to_date}, page)

    while True:
        page_token = f"view:_id1:_id2:cbMain:_id136:pager1__Group__lnk__{page}"
        log.info(f"page {int(page) + 1} start...")

        data["$$xspsubmitid"] = page_token
        print(session.headers)
        print(data)
        resp = session.post(
            "https://documents.un.org/prod/ods.nsf/xpSearchResultsM.xsp?$$ajaxid=view%3A_id1%3A_id2%3AcbMain%3AmainPanel",
            data=data
        )

        soup = BeautifulSoup(resp.text, "html.parser")
        _, current_end, total, page = get_total_info(soup)
        file_links = get_all_file_links_by_page(soup)
        save_data(file_links, {"from": from_date, "to": to_date}, page)

        if current_end == total:
            break
    
    log.debug(f"{from_date} -- {to_date} completed!")
        

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


if __name__ == "__main__":
    get_doc_list_from_datetime_range()
