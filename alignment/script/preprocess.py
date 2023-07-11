from difflib import SequenceMatcher
from functools import partial
import json
from pathlib import Path
import re
import itertools
import os

from collections import Counter

import datasets

PAGINATION_TOKEN = '\n----\n' # 分页符
FILTER_LOG = 'preprocessed_log.jsonl' # 过滤日志文件路径
HEADER_SCAN_LIMIT = 100 # 我们认为页眉至多出现在距离每页开头100个字符以内的范围内
LANGS = ['zh', 'fr', 'es', 'ru', 'en'] # 待预处理的语言表，这里暂时不包括阿拉伯语ar
DIGITS_PATTERN = re.compile('^\d+$') # 用来认数字的正则，引入是因为str.isdigit不可靠，在并非严格是数字的时候会给True
MATCHER_RATIO = 0.72
PREPROCESS_DIR = Path('preprocessed_dump')

PREPROCESS_DIR.mkdir(exist_ok=True)

def make_filter_log(filtered: str, record: str | int, lang: str, page: str | int, reason: str):
    """将过滤的内容写到log里方便分析"""
    with open(FILTER_LOG, 'a', encoding='utf-8', buffering=1 << 20) as f:
        json.dump({'record': str(record), 'lang': lang, 'page': str(page), 'reason': reason, 'filtered': filtered}, f)
        f.write('\n')

def make_banner(record: str) -> str:
    """简单画一个横幅"""
    divider = '=' * 10 + '\n'
    return  divider + record + '\n' + divider

def dump_row(row: datasets.DatasetDict, prefix: str):
    """
    调试用，输出中间结果到文件
    方便在上传之前最后人工确认一下预处理结果
    """
    for lang in LANGS:
        with (PREPROCESS_DIR / f'{prefix}_{lang}.txt').open('a', encoding='utf-8') as f:
            f.write(make_banner(row['record']) + row[lang])


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

    # 去掉只出现少数的token，提高运行效率
    for x in list(token_occurrences.keys()):
        if token_occurrences[x] < 3 or token_occurrences[x] > len(pages):
            token_occurrences.pop(x)

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

def estimate_pagination_offset(pages: list[str]) -> list[set[str]]:
    """
    统计类似页码信息的token，估算出一个页码偏移值，来帮助后续过程去除疑似页码的数字

    Args:
        pages (list[str]): 单语种文件按页分开后的列表

    Returns:
        int | None: 页码偏移值，为None时表示本文不像是有页码
    """
    pagination_offset = None
    page_token_slots = [set() for _ in pages] # 每页是list中的一个元素，set里装本页里所有页眉部分的token
    for slot, page in zip(page_token_slots, pages):
        for line in page[:HEADER_SCAN_LIMIT].splitlines():
            for token in line.split():
                for i in re.findall(r'\d+', token):
                    slot.add(i)
    
    max_hits = 0 # 记最大页码命中数
    for offset in range(-9, 3): # 请谨慎修改这个偏移值的估计范围
        hits = 0
        for pageid in range(len(pages)):
            if str(pageid + offset) in page_token_slots[pageid]:
                hits += 1
        if hits > max_hits:
            max_hits = hits
            pagination_offset = offset
    # 如果观察日志发现页码去除得过于激进，可以取消注释下面两行来规避一些并不是页码的case
    if max_hits < len(pages) // 2:
        pagination_offset = None
    return pagination_offset

def remove_duplicate_breakline(pages: list[str]):
    """除掉多余的空行"""
    return filter(len, list(
        line.strip() for line in itertools.chain(*[page.splitlines() for page in pages])))

def short_file_and_garbled_text_filter(row):
    """
    过滤掉英文文章中，仅有1~2页的短文件，以及非英文字符比例过高的（很可能是导出错误出现乱码的）文件
    """
    inputs: str = row['en']
    en_rate = len(re.findall(r'[a-zA-Z]', inputs)) / len(inputs) if len(inputs) else 0
    if en_rate < 0.2:
        return False
    if inputs.count(PAGINATION_TOKEN) <= 1: # 1~2页的短文件有很大比例是第一页的噪声，这样的文件拿去对齐意义不大
        return False
    return True

def drop_pagination_header_and_footer(row: datasets.DatasetDict):
    """语种无关过滤页眉（包括页码），不依赖任何正则，仅依靠自身和其它语种中出现的文本块频度统计实现

    Args：
        row (DatasetDict): datasets map进来的行，内含一篇文章的六个语种版本，每页用\n----\n隔开
    Returns:
        row (DatasetDict): 清洗后按原格式组装的row
    """
    all_lang_token_occurrences = count_occurrences_across_all_langs(row)
    all_lang_page_num_sum = sum(map(lambda x: row[x].count(PAGINATION_TOKEN) + 1, LANGS)) # 所有语言版本的文件的页数总和
    record = row['record']

    for lang in LANGS:
        pages = row[lang].replace('\ufffe', '-').split(PAGINATION_TOKEN)
        token_occurrences = count_occurrences_across_single_lang(pages)
        line_occurrences = count_line_digest_occurrences_across_single_lang(pages)
        pagination_offset = estimate_pagination_offset(pages)

        def is_freq(freq: int):
            """频次高于本表达式规定的，我们认为属于噪声信息"""
            return len(pages) >= 3 and freq >= len(pages) - 1 or \
                   len(pages) >= 5 and freq > len(pages) * 0.666

        for pageid, page in enumerate(pages): # pageid仅用于打log用和回写pages
            header = page[:HEADER_SCAN_LIMIT] # 我们假设header为页眉可能出现的范围

            def line_noise_judge(line: str) -> bool:
                """
                先模糊匹配去掉噪声行
                本函数用于判断一行是否疑似噪声行
                为了filter使用，返回False的为噪声行，不保留，返回True的为正常行，需要保留
                """
                line_digest = line2line_digest(line.strip())
                sum_freq = 0
                if not line_digest: # 在这步中，我们先放过空行，以免header和body拼接导致换行被意外吃掉
                    return True
                
                for line_str, occurrence_count in line_occurrences.items():
                    matcher = SequenceMatcher(None, line_digest, line_str, autojunk=False)
                    # 直接算ratio会很慢，这里用上界来剪掉大部分情况
                    if matcher.real_quick_ratio() > MATCHER_RATIO and matcher.quick_ratio() > MATCHER_RATIO and matcher.ratio() > MATCHER_RATIO:
                        sum_freq += occurrence_count
                if is_freq(sum_freq):
                    make_filter_log(line, record, lang, pageid, f'line_freq: {sum_freq}, pages: {len(pages)}')
                    return False
                return True

            newlines = []
            for line in filter(line_noise_judge, header.splitlines()): # 我们先滤掉了有问题的行
                reach_end_of_noises = False # 用来记录第一次新的有效token被加入。因为是处理页眉，我们只删连续一段开头的，这样写来防止删掉类似the la de这些常见单词

                def token_noise_judge(token: str) -> bool:
                    """
                    精确匹配，洗掉噪声token
                    类似line_noise_judge，不再赘述
                    但是本函数需要读写外部的reach_end_of_noises变量，以免删掉出现频次很高的短单词
                    """
                    nonlocal reach_end_of_noises
                    if reach_end_of_noises:
                        return True
                    if pagination_offset is not None and (re.match(DIGITS_PATTERN, token) or
                             re.match(r'^\d+/\d+', token)) and str(pageid + pagination_offset) in re.findall(r'\d+', token): # 过滤页码
                        make_filter_log(token, record, lang, pageid, f'likely page number')
                        return False
                    if all_lang_token_occurrences[token] > all_lang_page_num_sum // 2:
                        make_filter_log(token, record, lang, pageid, f'overall_tk_freq: {all_lang_token_occurrences[token]}, all_pages: {all_lang_page_num_sum}') # 过滤全文常见token
                        return False

                    token_freq = token_occurrences[token]
                    if is_freq(token_freq) and not token_freq > len(pages): # 过滤单文常见token
                        make_filter_log(token, record, lang, pageid, f'tk_freq: {token_freq}, pages: {len(pages)}')
                        return False
                    reach_end_of_noises = True
                    return True
                
                newline = ' '.join(filter(token_noise_judge, line.split()))
                newlines.append(newline)
            
            new_header = '\n'.join(newlines)

            new_page = new_header + page[HEADER_SCAN_LIMIT:] # 我们至此已经处理完页眉，记在new_header里，但是页脚注解部分也需要去
            annotation_index = new_page.find('__________')
            if annotation_index != -1:
                make_filter_log(new_page[annotation_index:], record, lang, pageid, f"annotation block")
                new_page = new_page[:annotation_index]
            
            pages[pageid] = new_page.strip() # 一页处理完成，写回pages里

        row[lang] = '\n'.join(remove_duplicate_breakline(pages))
    return row

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

if __name__ == "__main__":
    use_proxy()
    dataset = datasets.load_dataset("ranWang/un_pdf_text_data_test", split='new_randomTest10000')
    dataset.map(partial(dump_row, prefix='raw'))
    dataset = dataset.filter(short_file_and_garbled_text_filter).map(drop_pagination_header_and_footer, num_proc=8)
    # input('Press any key to dump preprocessed files...')
    dataset.map(partial(dump_row, prefix='preprocessed'))
    dataset.save_to_disk(PREPROCESS_DIR)
    print(len(dataset))
    # input('Press any key to continue push to hub...')
    dataset.push_to_hub('bot-yaya/un_pdf_random9208_preprocessed_2', token=os.environ.get('HF_TOKEN') or input('Your hf token:'))
