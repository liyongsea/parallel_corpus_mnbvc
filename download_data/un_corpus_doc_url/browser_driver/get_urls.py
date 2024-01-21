import argparse
import time
import random
import datetime
import datasets

from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

def get_weekly_date_ranges_adjusted(start_date_str, end_date_str):
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return []

    result_list = []

    # Adjust start_date to the first day of the week (Monday)
    start_day_of_week = start_date.weekday()  # Monday is 0, Sunday is 6
    start_of_week = start_date - datetime.timedelta(days=start_day_of_week)

    while start_of_week < end_date:
        end_of_week = start_of_week + datetime.timedelta(days=6)  # End of the week

        # Adjust the start and end of the week to be within the given date range
        actual_start = max(start_of_week, start_date)
        actual_end = min(end_of_week, end_date)

        result_list.append(
            (actual_start.strftime("%Y-%m-%d"), actual_end.strftime("%Y-%m-%d"))
        )

        # Move to the next week
        start_of_week = end_of_week + datetime.timedelta(days=1)

    return result_list



def get_urls(driver, date_from, date_to):
    print(f"{date_from} -- {date_to}, running...")
    result_list = []

    driver.get("https://documents.un.org/prod/ods.nsf/home.xsp")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#widget_view\\:_id1\\:_id2\\:dtRelDateFrom input[type="hidden"]',)))

    driver.execute_script(
        f"""document.querySelector("#widget_view\\\:_id1\\\:_id2\\\:dtRelDateFrom > div.dijitReset.dijitInputField.dijitInputContainer > input[type=hidden]:nth-child(2)").value = '{date_from}';"""
    )
    driver.execute_script(
        f"""document.querySelector("#widget_view\\\:_id1\\\:_id2\\\:dtRelDateTo > div.dijitReset.dijitInputField.dijitInputContainer > input[type=hidden]:nth-child(2)").value = '{date_to}';"""
    )

    search_button = driver.find_element(By.CSS_SELECTOR, "#view\\:_id1\\:_id2\\:btnRefine")
    search_button.click()

    all_total = 0
    current_total = 0

    # 循环翻页并收集数据
    while True:
        print(f"{date_from} -- {date_to}, current total is {current_total}, {f'all total is {all_total}' if all_total else 'there is no count in the first round'}")

        # 等待页面加载
        time.sleep(random.randint(5, 10))  # 随机等待时间以模仿人类行为

        # 使用 BeautifulSoup 解析页面
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 获取所有文件元素
        all_files = soup.select("#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:rptResults > div")

        if not all_files:
            break

        for file in all_files:
            id = file.select_one(".odsText.pull-right.flip").text.strip()
            all_languages = file.select(".details div.row.noMargin > div")

            for language in all_languages:
                file_dom = language.select_one("div:nth-of-type(2)")
    
                pdf_links = file_dom.find_all('a', title=lambda title: title and "PDF" in title)
                doc_links = file_dom.find_all('a', title=lambda title: title and "Word Document" in title)

                if pdf_links and len(pdf_links):
                    temp = f'{date_from}_{date_to},{id},{pdf_links[0]["title"].replace(" ", "").replace("打开PDF文件", ",PDF")},{pdf_links[0]["href"].replace("?OpenElement", "")}'
                    result_list.append(temp)

                if doc_links and len(doc_links):
                    temp = f'{date_from}_{date_to},{id},{doc_links[0]["title"].replace(" ", "").replace("打开DOC文件", ",DOC").replace("Word文件", ",DOC")},{doc_links[0]["href"].replace("?OpenElement", "")}'
                    result_list.append(temp)

        current_total = driver.find_element(By.CSS_SELECTOR, f"#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle > b:nth-child(3)", ).text
        all_total = driver.find_element(By.CSS_SELECTOR, f"#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle > b:nth-child(4)",).text

        if current_total == all_total:
            break

        # 检查是否有下一页
        try:
            next_page = driver.find_element(By.CSS_SELECTOR, "#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:pager1__Next__lnk",)
            next_page.click()
        except:
            break  # 没有下一页时跳出循环

    print(f"{all_total} total downlaod success!")
    return result_list

class WebdriverManger():
    def __init__(self):
        self.driver = None

    def get_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome()
            self.driver.implicitly_wait(10)

        return self.driver
    
    def close(self):
        if self.driver:
            self.driver.quit()

def main(dates, save_path):
    webdriver_manger = WebdriverManger()

    for index, date in enumerate(dates):
        print(f"Progress: {index}/{len(dates)}")

        if Path(f"{save_path}/saveFile_{index}_{len(dates) - 1}.txt").exists():
            print(f"{date} exists")
            continue

        driver = webdriver_manger.get_driver()
        urls = get_urls(driver, date[0], date[1])
        # 保存 urls 到文件
        with open(f"{save_path}/saveFile_{index}_{len(dates) - 1}.txt", "w") as f:
            f.write("\n".join(urls))

    webdriver_manger.close()
