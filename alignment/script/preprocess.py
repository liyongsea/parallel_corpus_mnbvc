import json
import re
import itertools

from collections import Counter

import datasets

PAGINATION_TOKEN = '\n----\n' # 分页符
FILTER_LOG = 'preprocessed_log.jsonl' # 过滤日志文件路径
HEADER_SCAN_LIMIT = 100 # 我们认为页眉至多出现在距离每页开头100个字符以内的范围内
LANGS = ['zh', 'fr', 'es', 'ru', 'en'] # 待预处理的语言表，这里暂时不包括阿拉伯语ar
DIGITS_PATTERN = re.compile('^\d+$') # 用来认数字的正则，引入是因为str.isdigit不可靠，在并非严格是数字的时候会给True


def make_filter_log(filtered: str, record: str | int, lang: str, page: str | int, reason: str):
    """将过滤的内容写到log里方便分析"""
    with open(FILTER_LOG, 'a', encoding='utf-8') as f:
        json.dump({'record': str(record), 'lang': lang, 'page': str(page), 'reason': reason, 'filtered': filtered}, f)
        f.write('\n')

def count_occurrences_across_all_langs(row: datasets.DatasetDict) -> Counter:
    """
    统计一份文件的所有语言版本里重复出现的页眉噪声
    这些出现频次很多的token，如A/CN.9/WG.VI/WP.22/Add.1这些文件信息将在以后的步骤中被过滤掉。
    由于单词级别的token粒度比较小，建议用本函数得到的统计信息用**精确匹配**来滤掉噪声。

    返回一个dict的子类Counter，里面记录每个页眉范围内，每个以空字符分开的单词的出现次数。

    Args:
        row (DatasetDict): 请直接传入pdf导出的原始dataset的整个列

    Returns:
        Counter: 每个token在所有语言的文件中出现的次数

    """
    all_lang_token_occurrences = Counter()
    for lang in LANGS:
        pages = row[lang].split(PAGINATION_TOKEN)
        for page in pages:
            for line in page[:HEADER_SCAN_LIMIT].splitlines(): # 我们认为页眉噪声至多出现在每页的前100个字符内
                for token in line.split(): # 单行内以空格或其它空字符隔开的单词
                    all_lang_token_occurrences[token] += 1
    return all_lang_token_occurrences

def count_occurrences_across_single_lang(pages: list[str]) -> Counter:
    """
    统计一份单语种文件里重复出现的页眉噪声
    与count_occurrences_across_all_langs类似，但只处理单语种，不再赘述
    由于单词级别的token粒度比较小，建议用本函数得到的统计信息用**精确匹配**来滤掉噪声。

    Args:
        pages (list[str]): 单语种文件按页分开后的列表
    
    Returns:
        Counter: 每个token在本单语言的文件中出现的次数

    """
    token_occurrences = Counter()
    for page in pages:
        for line in page[:HEADER_SCAN_LIMIT].splitlines(): # 我们认为页眉噪声至多出现在每页的前100个字符内
            for token in line.split():
                token_occurrences[token] += 1
    return token_occurrences

def line2line_digest(line: str):
    """
    把一行原始文件行变为`line_digest`。
    这种处理方式为了将文件中出现的，如Page 2和P a g e 2这些行的频度算在一起
    目前简单处理为仅把空字符干掉
    """
    return ''.join(line.split())

def count_line_digest_occurrences_across_single_lang(pages: list[str]) -> Counter:
    """
    统计单语种文件中页眉行的出现频次
    这些行会被做成`line_digest`，从而进行更模糊的匹配
    由于行的粒度比较大，建议用本函数得到的统计信息进行一定程度上的模糊匹配来过滤噪声。

    Args:
        pages (list[str]): 单语种文件按页分开后的列表

    Returns:
        Counter: 每行(line_digest)在本单语言的文件中出现的次数
    """
    line_digest_occurrences = Counter()
    for page in pages:
        for line in page[:HEADER_SCAN_LIMIT].splitlines(): # 我们认为页眉噪声至多出现在每页的前100个字符内
            line_digest = line2line_digest(line)
            if line_digest:
                line_digest_occurrences[line_digest] += 1
    return line_digest_occurrences

def count_page_id_like_token_occurrences(pages: list[str]) -> list[set[str]]:
    """
    统计类似页码信息的token

    Args:
        pages (list[str]): 单语种文件按页分开后的列表

    Returns:
        list[set[str]]: 每页是list中的一个元素，set里装本页里所有页眉部分的token
    """
    page_token_slots = [set() for _ in pages]
    for slot, page in zip(page_token_slots, pages):
        for line in page[:HEADER_SCAN_LIMIT]:
            for token in line.split():
                slot.add(token)
    return page_token_slots

def remove_duplicate_breakline(pages: list[str]):
    """除掉多余的空行"""
    return filter(len, list(
        line.strip() for line in itertools.chain(*[page.splitlines() for page in pages])))

def chk_en_rate(row):
    """检查一个文件的英文含量，如果一份英文文件里Unicode乱码而不是英文文字居多，我们应该放弃处理这些文件"""
    inputs = row['en']
    en_rate = len(re.findall(r'[a-zA-Z]', inputs)) / len(inputs) if len(inputs) else 0
    if en_rate < 0.2:
        return False
    return True

def drop_pagination_header_and_footer(row: datasets.DatasetDict):
    """语种无关过滤页眉（包括页码），不依赖任何正则，仅依靠自身和其它语种中出现的文本块频度统计实现

    ！！！目前还没改完！！！

    Args：
        row (DatasetDict): datasets map进来的行，内含一篇文章的六个语种版本，每页用\n----\n隔开
    Returns:
        row (DatasetDict): 清洗后按原格式组装的row
    """
    all_lang_token_occurrences = count_occurrences_across_all_langs(row)
    record = row['record']

    for lang in LANGS:
        single_lang_file = row[lang]

