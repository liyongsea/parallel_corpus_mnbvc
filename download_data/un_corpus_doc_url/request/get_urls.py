import datetime
import json
from pathlib import Path
import os
import re
from tqdm import tqdm
from bs4 import BeautifulSoup
import copy

# os.environ['OPENSSL_CONF'] = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\openssl.cnf'
# 打开SSL重新协商，https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import logging as log

log.basicConfig(level=log.INFO, format='%(asctime)s %(levelname)s (%(funcName)s:%(lineno)d) - %(message)s')


def get_all_view_hover_boxs(soup: BeautifulSoup):
    selector = "#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:rptResults .viewHover"
    view_hover_elements = soup.select(selector)
    return view_hover_elements


#  es ar fr zh en de ru
language_map = {
    "ARABIC": "ar",
    "CHINESE": "zh",
    "ENGLISH": "en",
    "FRENCH": "fr",
    "RUSSIAN": "ru",
    "SPANISH": "es"
}

def parse_view_hover_box_file_link(hover_box_element: BeautifulSoup):
    id = hover_box_element.select_one(".odsText.pull-right.flip").text.strip()
    all_languages_elements = hover_box_element.select(".details div.row.noMargin > div")

    url_with_languages = []
    for language_element in all_languages_elements:
        language = language_element.select_one(".odsTitle").text
        language = language_map.get(language, language)

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

def get_page_info(soup) -> (str, str, str, str):
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

    if not page_info_element:
        log.info(f"此时间范围不存在数据")
        return None, None, None, None
    
    active_li_tags = page_info_element.select("li.active")
    active_li_tags = list(filter(lambda li: "Group__lnk" in li.select_one("a").get('id'), active_li_tags))
  
    if len(active_li_tags) == 1:
        current_page = active_li_tags[0].text
    else:
        log.info(f"{current_start} -- {current_end}, 不存在页数信息")
    
    return current_start, current_end, total, current_page

def save_data(data, date, page, save_path):
    (save_path / f"{date['from']}--{date['to']}").mkdir(exist_ok=True)

    with open(save_path / f"{date['from']}--{date['to']}" / f"{page}.json", "w") as f:
        json.dump(data, f)

def check_file_exist(date, page, save_path):
    return (save_path / f"{date['from']}--{date['to']}" / f"{page}.json").exists()

DEFAULT_DEADERS = {
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Host": "documents.un.org",
    "Cache-Control": "no-cache",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
    "Origin": "https://documents.un.org",
}

DEFAULT_FORM_DATA = {
    "view:_id1:_id2:txtSymbol": "",
    "view:_id1:_id2:rgTrunc": "R",
    "view:_id1:_id2:txtWrds": "",
    "view:_id1:_id2:txtSubj": "",
    "view:_id1:_id2:dtPubDateFrom": "",
    "view:_id1:_id2:dtPubDateTo": "",
    "view:_id1:_id2:dtRelDateFrom": "",
    "view:_id1:_id2:dtRelDateTo": "",
    "view:_id1:_id2:txtJobNo": "",
    "view:_id1:_id2:txtSess": "",
    "view:_id1:_id2:txtAgItem": "",
    "view:_id1:_id2:txtFTSrch": "",
    "view:_id1:_id2:cbType": "FP",
    "view:_id1:_id2:cbSort": "R",
    "view:_id1:_id2:hdnSubj": "",
    "$$viewid": "",
    "$$xspsubmitid": "view:_id1:_id2:_id131",
    "$$xspexecid": "",
    "$$xspsubmitvalue": "",
    "$$xspsubmitscroll": "0|0",
    "view:_id1": "view:_id1",
}

class UnRequestManger():
    def __init__(self) -> None:
        self.session = None
        self.body_data = copy.deepcopy(DEFAULT_FORM_DATA)
        # 用于记录是否完成search，如果没有完成需要search函数提供id以供翻页使用
        self.completed_search = False
    
    def init_session(self):
        self.session = requests.session()
        self.session.headers = DEFAULT_DEADERS

    def get_session(self):
        if not self.session:
            self.init_session()
        return self.session

    def login(self):
        resp = self.get_session().get("https://documents.un.org/prod/ods.nsf/home.xsp")
        view_id_pattern = re.compile( r"""<input type="hidden" name="\$\$viewid" id="view:_id1__VUID" value="(.*?)">""", re.M, )
        self.body_data["$$viewid"] = view_id_pattern.findall(resp.text)[0]

    def search(self, from_date, to_date):
        self.body_data["view:_id1:_id2:dtRelDateFrom"] = from_date
        self.body_data["view:_id1:_id2:dtRelDateTo"] = to_date
        multipart_data = MultipartEncoder(fields=self.body_data)

        resp = self.get_session().post(
            "https://documents.un.org/prod/ods.nsf/home.xsp",
            data=multipart_data,
            headers={"Content-Type": multipart_data.content_type}
        )
        view_id_pattern = re.compile( r"""<input type="hidden" name="\$\$viewid" id="view:_id1__VUID" value="(.*?)">""", re.M, )
        self.body_data["$$viewid"] = view_id_pattern.findall(resp.text)[0]
        self.completed_search = True
        return resp.text
    
    def get_pgae(self, page, from_date, to_date):
        if not self.completed_search:
            self.search(from_date, to_date)

        page_token = f"view:_id1:_id2:cbMain:_id136:pager1__Group__lnk__{page}"
        self.body_data["$$xspsubmitid"] = page_token

        resp = self.get_session().post("https://documents.un.org/prod/ods.nsf/xpSearchResultsM.xsp?$$ajaxid=view%3A_id1%3A_id2%3AcbMain%3AmainPanel", data=self.body_data)
        return resp.text

def find_max_numbered_json(folder_path):
    """
    Find the JSON file with the highest numeric name in the given folder.

    :param folder_path: Path to the folder containing the JSON files.
    :return: The highest number found in the file names, or None if no numeric file names are found.
    """
    max_number = None

    pattern = re.compile(r'^(\d+)\.json$')

    folder = Path(folder_path)

    for file in folder.glob('*.json'):
        match = pattern.match(file.name)
        if match:
            number = int(match.group(1))
            if max_number is None or number > max_number:
                max_number = number

    return max_number

def check_time_range_continue_request(from_date, to_date, save_path: Path, total, page_size=20):
    save_dir = save_path / f"{from_date}--{to_date}"
    if save_dir.exists():
        max_page = find_max_numbered_json(save_dir)
        file = open(save_dir / f"{max_page}.json", "r")
        max_page_total = len(json.load(file))
        return (max_page - 1) * page_size + max_page_total < total, max_page - 1
    else:
        return True, 1


def get_urls(from_date, to_date, save_path):
    log.info(f"{from_date} -- {to_date} start...")
    un_request_manger = UnRequestManger()
    un_request_manger.login()

    log.info(f"正在检查缓存数据，并进行第一轮请求！")
    text = un_request_manger.search(from_date, to_date)
    soup = BeautifulSoup(text, "html.parser")
    _, current_end, total, current_page_str = get_page_info(soup)

    if not total:
        return

    is_continue, current_page = check_time_range_continue_request(from_date, to_date, save_path, int(total))
    if not is_continue:
        log.info(f"{from_date} -- {to_date} 所有数据均被缓存!")
        return
    
    
    file_links = get_all_file_links_by_page(soup)
    save_data(file_links, {"from": from_date, "to": to_date}, current_page, save_path)
    log.info(f"process {current_end} / {total}")

    while True:
        text = un_request_manger.get_pgae(current_page, from_date, to_date)

        soup = BeautifulSoup(text, "html.parser")
        _, current_end, total, current_page_str = get_page_info(soup)
        current_page = int(current_page_str)
        file_links = get_all_file_links_by_page(soup)
        save_data(file_links, {"from": from_date, "to": to_date}, current_page, save_path)

        log.info(f"process {current_end} / {total}")
        if current_end == total:
            break

    log.info(f"{from_date} -- {to_date} completed!")


def main(dates, save_path: Path):
    for _, date in tqdm(enumerate(dates), total=len(dates)):
        get_urls(date[0], date[1], save_path)

