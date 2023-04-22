import urllib.request
import gzip
import io
from lxml import etree
import argparse
import json
import re
from pathlib import Path
from tqdm import tqdm 

def get_sitemap_text(gz_url):
    """
    Args:
        sitemap url (URL links with .gz suffix)

    Returns:
        Sitemap text
    """
    response = urllib.request.urlopen(gz_url)
    compressed_file = io.BytesIO(response.read())
    decompressed_file = gzip.GzipFile(fileobj=compressed_file)
    return decompressed_file.read()


def parse_all_son_sitemap_url(sitemap_text):
    """Parse all son sitemap link in root sitemap file text

    Returns:
        Sitemap link list
    """
    root = etree.fromstring(sitemap_text)
    locs = []
    for sitemap in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
        loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        locs.append(loc)
    return locs


def get_pdf_url_in_sitemap_text(sitemap_text):
    """Get all pdf links in the son sitemap file text

    Returns:
        Pdf link list
    """
    root = etree.fromstring(sitemap_text)
    locs = []
    for url in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
        loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        locs.append(loc)
    return locs


LANG_LIST = ["ar", "en", "es", "fr", "ru", "zh"]

LANGUAGE_REGEX = re.compile(f"({'|'.join(LANG_LIST)})\.pdf$")

def match_six_countries_file_url(url_list):
    """Find a matching PDF link for the six languages in a URL linked list
       In the parameters passed in, the PDF URLs of different languages in the six countries should be continuous 

    Returns:
        PDF links in well matched six languages

        Examples:
            [["https://xxx-zh.pdf", "https://xxx-en.pdf", ...], ...]
    """    
    pdf_dict = []
    
    for i in range(len(url_list) - len(LANG_LIST) + 1):
        match = True
        for j in range(len(LANG_LIST)):
            if not LANGUAGE_REGEX.search(url_list[i+j].lower()):
                match = False
                break
   
        if match:
            pdf_dict.append([url_list[i+j] for j in range(len(LANG_LIST))])
            
    return pdf_dict



ROOT_SITEMAP_URL = "https://digitallibrary.un.org/sitemap_index.xml.gz"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_save_dir', default="./download_pdf", type=str, help='文件保存的文件夹路径')

    args = parser.parse_args()
    Path(args.file_save_dir).mkdir(parents=True, exist_ok=True)

    root_sitemap_text = get_sitemap_text(ROOT_SITEMAP_URL)
    son_sitemap_url_list = parse_all_son_sitemap_url(root_sitemap_text)


    surrogate_analysis_List = []
    # Use single threading to ensure stability, If it is multi-threaded, it may trigger the website circuit breaker mechanism
    for son_sitemap_url in tqdm(son_sitemap_url_list):
        son_sitemap_text = get_sitemap_text(son_sitemap_url)
        pdf_url_list = get_pdf_url_in_sitemap_text(son_sitemap_text)

        surrogate_analysis_List += pdf_url_list

    six_language_pdf_links = match_six_countries_file_url(surrogate_analysis_List)

    with open(f"{args.file_save_dir}/SixLanguagePDF-URLS.json", "w") as f:
        json.dump(six_language_pdf_links, f)