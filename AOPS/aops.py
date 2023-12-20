import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_toolbelt.multipart.encoder import MultipartEncoder


FORUM_LIST = []
VIEW_POST_LIST = []
VISITED_FOLDER = []
BASE_URL = "https://artofproblemsolving.com/m/community/ajax.php"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Connection": "keep-alive"
}
COMMON_FORM_DATA = {
    "aops_logged_in": False,
    "aops_user_id": 1,
    "aops_session_id": "21d6f40cfb511982e4424e0e250a9557"
}


def build_session_with_retry(retries=3, backoff_factor=0.5,):
    """构造具有重试机制的请求会话"""
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def build_multipart_data(data: dict):
    """构造请求表单数据"""
    fields = {}
    for key, value in data.items():
        fields.update({
            key: json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        })
    return MultipartEncoder(fields=fields)


def send_post_multipart_request(session, url, json_data, headers=DEFAULT_HEADERS, error_file="error.log"):
    """发起一个表单请求"""
    multipart_data = build_multipart_data(json_data)
    multipart_headers = {**headers, 'Content-Type': multipart_data.content_type}

    try:
        response = session.post(url, data=multipart_data, headers=multipart_headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if error_file:
            with open(error_file, "a") as file:
                file.write(f'{time.strftime("%Y-%m-%d %H:%M:%S %z")} - {url} - {json_data} - {e}\n')
        return None


def fetch_items_categories(session: requests.Session, url: str, parent_category_id: int,  headers=DEFAULT_HEADERS):
    """获取全部目录"""
    start_num = 0
    categories = []
    form_data = {
        "sought_category_ids": [],
        "parent_category_id": parent_category_id,
        "seek_items": 1,
        'start_num': start_num,
        "log_visit": 0,
        "a": "fetch_items_categories",
        **COMMON_FORM_DATA
    }

    while True:
        response = send_post_multipart_request(session, url, form_data)
        if response is None:
            continue
        new_items = response['response'].get('new_items', None)
        if new_items is not None:
            categories.extend([item['category'] for item in new_items])
            form_data['start_num'] += 10
        else:
            break
    return categories


def fetch_posts_for_topic(session: requests.Session, url: str, topic_id: int, headers=DEFAULT_HEADERS):
    """通过话题ID获取全部回复"""
    posts = []
    form_data = {
        "topic_id": topic_id,
        "start_post_id": -1,
        "start_post_num": 1,
        "show_from_time": -1,
        "num_to_fetch": 500,
        "a": "fetch_posts_for_topic",
        **COMMON_FORM_DATA
    }

    while True:
        response = send_post_multipart_request(session, url, form_data, error_file='./fetch_posts_errors.log')
        response_posts = response['response']['posts']

        if len(response_posts) > 0:
            posts.extend(response_posts)
            form_data['start_post_num'] = response_posts[-1]['post_number'] + 1
        else:
            break
    return posts


def fetch_topic(session: requests.Session, url: str, category_id: int, headers=DEFAULT_HEADERS):
    """通过分类ID获取分类下的全部主题"""
    form_data = {
        "category_type": "forum",
        "log_visit": 0,
        "fetch_before": 0,
        "user_id": 0,
        "fetch_archived": 0,
        "fetch_announcements": 0,
        "category_id": category_id,
        "a": "fetch_topics",
        **COMMON_FORM_DATA
    }
    while True:
        response = send_post_multipart_request(session, url, form_data, error_file='./fetch_posts_errors.log')
        response_topics = response['response']['topics']
        for topic in response_topics:
            yield topic

        if len(response_topics) > 0:
            form_data['fetch_before'] = response_topics[-1]['last_post_time']

        if response['response']['no_more_topics']:
            break


def fetch_more_items(session: requests.Session, url: str, category_id: int, headers=DEFAULT_HEADERS):
    """"""
    form_data = {
        'category_id': category_id,
        'last_item_score': 5,
        'last_item_level': 0,
        'log_visit': 0,
        'start_num': 0,
        'fetch_all': 1,
        'a': 'fetch_more_items',
        **COMMON_FORM_DATA
    }

    response = send_post_multipart_request(session, url, form_data)
    return [item for item in response['response']['items'] if item['post_data']['post_type'] == 'forum']


def parse_categorie_id(categories, folder: list = []):
    "获取具体的网站目录和对应id"
    for category in categories:
        if category['category_type'] == 'forum':
            FORUM_LIST.append((folder + [category['category_name']], category['category_id']))
            print((folder + [category['category_name']], category['category_id']))
        
        if category['category_type'] in ['folder', 'folder_collections']:
            # 防止重复进入套娃目录造成死循环
            if category['category_id'] in VISITED_FOLDER:
                continue
            VISITED_FOLDER.append(category['category_id'])

            item_ids = [item['item_id'] for item in category['items']]
            res_categories = fetch_items_categories(build_session_with_retry(), BASE_URL, category['category_id'], item_ids)
            if res_categories == None:
                continue
            parse_categorie_id(res_categories, folder + [category['category_name']])

        if category['category_type'] == 'view_posts':
            VIEW_POST_LIST.append((folder + [category['category_name']], category['category_id']))
            print((folder + [category['category_name']], category['category_id']))


def posts_format(posts):
    """格式化回复列表，只取需要的字段"""
    res = []
    for post in posts:
        res.append({
            "post_id": post["post_id"],
            "topic_id": post["topic_id"],
            "poster_id": post["poster_id"],
            "post_rendered": post["post_rendered"],
            "post_canonical": post["post_canonical"],
            "username": post["username"],
            "thanks_received": post["thanks_received"],
            "nothanks_received": post["nothanks_received"],
            "post_time": post["post_time"],
            "post_format": post["post_format"]
        })
    return res


def get_topics_by_cateid_with_post(ids):
    """通过分类id获取全部主题和回复
    ids参数e.g: [["Contest Collections", "Contest Collections Discussion"], 40244]
    """
    session = build_session_with_retry()
    save_dir = Path('./aops_result/' + '/'.join(ids[0]))
    save_dir.mkdir(parents=True, exist_ok=True)

    for topic in fetch_topic(session, BASE_URL, ids[1]):
        posts = fetch_posts_for_topic(session, BASE_URL, topic['topic_id'])

        with open(save_dir / f'{topic["topic_id"]}.json', 'w', encoding='utf-8') as out:
            json.dump(
                {
                    'topic_id': topic["topic_id"],
                    'category_id': topic["category_id"],
                    'category_name': topic["category_name"],
                    'topic_title': topic["topic_title"],
                    'topic_type': topic["topic_type"],
                    'comment_count': topic["comment_count"],
                    'num_views': topic["num_views"],
                    'first_post_id': topic["first_post_id"],
                    'first_poster_id': topic["first_poster_id"],
                    'first_poster_name': topic["first_poster_name"],
                    'first_post_time': topic["first_post_time"],
                    'last_update_time': topic["last_update_time"],
                    'posts': posts_format(posts)
                }, out
            )
        print(f'topics {ids[1]} {topic["topic_id"]} {topic["topic_title"]}')


def get_view_post_by_id_with_post(ids):
    """通过分类id获取全部viewpost和回复
    ids参数e.g: [["Contest Collections", "International Contests", "IMO", "2023 IMO"], 3381519]
    """
    session = build_session_with_retry()
    save_dir = Path('./aops_result/' + '/'.join(ids[0]))
    save_dir.mkdir(parents=True, exist_ok=True)

    for item in fetch_more_items(session, BASE_URL, ids[1]):
        posts = fetch_posts_for_topic(session, BASE_URL, item['post_data']['topic_id'])

        with open(save_dir / f'{item["post_data"]["topic_id"]}.json', 'w', encoding='utf-8') as out:
            json.dump(
                {
                    'topic_id': item["post_data"]["topic_id"],
                    'category_id': item["post_data"]["category_id"],
                    'category_name': item["post_data"]["category_name"],
                    'topic_title': None,
                    'topic_type': None,
                    'comment_count': len(posts),
                    'num_views': None,
                    'first_post_id': posts[0]['topic_id'],
                    'first_poster_id': posts[0]['poster_id'],
                    'first_poster_name': posts[0]['username'],
                    'first_post_time': posts[0]['post_time'],
                    'last_update_time': posts[-1]['post_time'],
                    'posts': posts_format(posts)
                }, out
            )
        print(f'view post {ids[1]} {item["item_id"]} {item["item_text"]} {item["post_data"]["topic_id"]}')


if __name__ == '__main__':
    folder_index = Path('./categories_folder_index.json')
    viewpost_index = Path('./categories_viewpost_index.json')

    # 索引
    if not(folder_index.exists() and viewpost_index.exists()):
        with open('./aops-categories-metadata.json', 'r', encoding='utf-8') as aops_cate_input:
            aops_categories_metadata = json.load(aops_cate_input)
            # 这里只爬一组竞赛题集合，需要爬全部请注释下面两行
            # aops_categories_metadata.reverse()
            aops_categories_metadata = [_ for _ in aops_categories_metadata if _['category_id'] in [13]]
            parse_categorie_id(aops_categories_metadata)

        with open(folder_index, 'w', encoding='utf-8') as out1:
            json.dump(FORUM_LIST, out1)

        with open(viewpost_index, 'w', encoding='utf-8') as out2:
            json.dump(VIEW_POST_LIST, out2)
    else:
        with open(folder_index, 'r', encoding='utf-8') as inp1:
            FORUM_LIST = json.load(inp1)

        with open(viewpost_index, 'r', encoding='utf-8') as inp2:
            VIEW_POST_LIST = json.load(inp2)

    # Download data
    with ProcessPoolExecutor() as ps_pool:
        for _1 in FORUM_LIST:
            ps_pool.submit(get_topics_by_cateid_with_post, _1)

        for _2 in VIEW_POST_LIST:
            ps_pool.submit(get_view_post_by_id_with_post, _2)
