import datasets
from datasets import Dataset
from bs4 import BeautifulSoup
from tqdm import tqdm


dataset = datasets.load_dataset("ranWang/un_corpus_for_sitemap")


not_required_content = {'Weibo', 'Twitter', '打印', '电子邮件', '\n', '.', '。', ''}
not_required_class = {"datetime", "media-credit", "list-group"}


def get_all_contents(root_tag):
    class_list = root_tag.get('class')
    # class_list 不可能存在多个
    if class_list and class_list[0] in not_required_class:
        return set()
    
    contents = set()
    for child in root_tag.children:
        if hasattr(child, 'children'):
            contents |= get_all_contents(child)
        else:
            content = child.get_text().replace("\xa0","").replace(" ","").replace("\n","")
            if not content in not_required_content:
                contents.add(content)

    return contents


def get_news_content(row):
    soup = BeautifulSoup(row['html_content'])
    
    all_useful_tag = set()
    
    if "content" in row['url']:
        all_useful_tag |= set(soup.select(".main-content"))
    else:    
        all_useful_tag |= set(soup.select(".field-content"))
        all_useful_tag |= set(soup.select(".field__item"))
    
    all_tag_content = set()
    for tag in all_useful_tag:
        all_tag_content |= get_all_contents(tag)
    
    all_tag_content = set(all_tag_content)
    all_tag_content.discard(row['title']) 
    
    return sorted(all_tag_content)


def get_dataset_row(row):
    return {"uuid":row['uuid'], "url":row['url'], "title":row['title'], "news_content":get_news_content(row), "html_content":row['html_content']}


def transform_dict_to_dataset(dataset_single_lang_dict):
    dataset_list_dict = {"uuid":[], "url":[], "title":[], "news_content":[], "html_content":[]}                         

    for row in dataset_single_lang_dict:
        for key in row:
            dataset_list_dict[key].append(row[key])

    return Dataset.from_dict(dataset_list_dict)


for lang in dataset:

    obtained_content_row_list = []

    for row in tqdm(dataset[lang]):
        obtained_content_row_list.append(get_dataset_row(row))

    lang_dataset = transform_dict_to_dataset(obtained_content_row_list)

    lang_dataset.save_to_disk(f"{lang}_dataset")


    