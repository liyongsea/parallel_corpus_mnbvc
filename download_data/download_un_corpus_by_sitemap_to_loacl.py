import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import multiprocessing
import os
from tqdm import tqdm
import sys


output_folder = './downloaded_websites'
lang_list = ['zh', 'en', 'fr', 'es', 'ru', 'ar']
error_url_save_path = "./error_url.txt"


def save_error_url(url):
    if os.path.isfile(error_url_save_path):
        mode = 'a'
    else:
        mode = 'w'
        
    with open(error_url_save_path, mode) as f:
         f.write(url + '\n')


def get_html(url, retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    try:
        response = session.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"链接异常: {url} --- {e}")
        save_error_url(url)
        return None
    
    return response.text


def extract_urls_from_sitemap(sitemap_url):
    html_text = get_html(sitemap_url)
    if not html_text:
        return []
    
    soup = BeautifulSoup(html_text)
    urls = [loc.get_text() for loc in soup.find_all('loc')]
    return urls


def get_all_lang_url():
    lang_with_urls = {}
    
    
    print("Fetching all sitemap_urls...")
    for lang in lang_list:
        folder_path = os.path.join(output_folder, lang)
       
        sitemap_urls = extract_urls_from_sitemap(f"https://news.un.org/{lang}/sitemap.xml")
        is_lang_with_urls_exist = lang_with_urls.get("lang",None)
        
        if not is_lang_with_urls_exist:
            lang_with_urls[lang] = sitemap_urls
        else:    
            lang_with_urls[lang] += sitemap_urls
    
    print("Fetching all urls...")
    for lang in lang_with_urls:
        urls = []
        for lcos in lang_with_urls[lang]:
            urls += extract_urls_from_sitemap(lcos)
            
        lang_with_urls[lang] += urls
    
    return lang_with_urls



def download_and_parse_page(tuple_parameter):
    """
    例如 url = https://news.un.org/zh/story/2012/05/173792 lang = zh

    则文件保存位置为 ./downloaded_websites/zh/news.un.org.zh.story.2012.05.173792.html
    如果 url中不存在'https://'或者'http://', 则在 文件名前会添加'no_prefix'
    """
    url, lang = tuple_parameter
    
    html_text = get_html(url)
    
    url_split = url.split("//")
    filename =  url_split[1].replace("/",".") if len(url_split) == 2 else "no_prefix" + url_split[0]
    
    if html_text:
        with open(f"{output_folder}/{lang}/{filename}.html", 'w', encoding='utf-8') as f:
            f.write(html_text)

    
    
def main(seleted_lang_list):
    global lang_list
    lang_list = seleted_lang_list

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
            
    lang_with_urls = get_all_lang_url()
    
    # 相当于遍历lang_list中的所有语言
    for lang in lang_with_urls:
        if not os.path.exists(output_folder + "/" + lang):
            os.mkdir(output_folder + "/" + lang)
            
        urls = lang_with_urls[lang]
        
        print(f"{lang} start downloading...")
        with multiprocessing.Pool(processes=multiprocessing.cpu_count() * 8) as pool:
            for _ in tqdm(pool.imap_unordered(download_and_parse_page, [(url, lang) for url in urls]), total=len(urls)):
                pass


if __name__ == "__main__":

    if len(sys.argv) == 1:
        main(lang_list)
    else:
        arg_str = sys.argv[1]

        seleted_lang_list = [lang_str.replace(" ","") for lang_str in arg_str.split(",")]

        for lang in seleted_lang_list:
            if not lang in lang_list:
                raise TypeError("参数必须为在 ['zh', 'en', 'fr', 'es', 'ru', 'ar'] 中！ 它的格式为 'zh, en, ...' ")

        main(seleted_lang_list)
