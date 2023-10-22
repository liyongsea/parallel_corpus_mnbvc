import datetime
import os
from pathlib import Path
import datasets
from collections import namedtuple
from typing import Tuple
from itertools import chain

import pylcs

DROP_THRESHOLD = 0.2

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

LCSTokenInfo = namedtuple('LCSTokenInfo', ('token', 'length', 'source_line_id'))
def tokenize_by_space_splited_word(input_lines: list[str], output_lines: list[str], offset=0) -> Tuple[list[LCSTokenInfo], list[LCSTokenInfo]]:
    """
    Encode `input_lines` and `output_lines` by space splited word as utf-8 single character, to speedup LCS procedure.
    
    Args:
        input_lines (list[str]): The list of lines from source text.
        output_lines (list[str]): The list of lines from the processed text.
        offset (int): utf-8 encoding begin offset for tokenizing.

    Returns:
        list[list[str]]: The batched lines.
    """
    word_dict = {}
    input_tokens_info = []
    output_tokens_info = []
    for input_line_id, input_line in enumerate(input_lines):
        for word in input_line.split():
            input_tokens_info.append(LCSTokenInfo(
                chr(offset + word_dict.setdefault(word, len(word_dict))),
                len(word),
                input_line_id,
                ))
    
    for output_line_id, output_line in enumerate(output_lines):
        for word in output_line.split():
            if word in word_dict: # 为子序列写的优化
                output_tokens_info.append(LCSTokenInfo(
                    chr(offset + word_dict[word]),
                    len(word),
                    output_line_id,
                    ))
    return input_tokens_info, output_tokens_info

def tokenize_by_char(input_lines: list[str], output_lines: list[str], offset=0) -> Tuple[list[LCSTokenInfo], list[LCSTokenInfo]]:
    """
    """
    char_set = set(chain(*input_lines))
    input_tokens_info = []
    output_tokens_info = []
    for input_line_id, input_line in enumerate(input_lines):
        for char in input_line:
            input_tokens_info.append(LCSTokenInfo(
                char,
                1,
                input_line_id,
                ))
    
    for output_line_id, output_line in enumerate(output_lines):
        for char in output_line:
            if char in char_set: # 为子序列写的优化
                output_tokens_info.append(LCSTokenInfo(
                    char,
                    1,
                    output_line_id,
                    ))
    return input_tokens_info, output_tokens_info

def lcs_sequence_alignment(input_lines: list[str] , output_lines: list[str], drop_th=DROP_THRESHOLD, tokenizer=tokenize_by_space_splited_word) -> Tuple[dict[int, Tuple[int, int]], list[float], list[float]]:
    """
    将input_lines每行的单词用最长公共子序列对齐到output_lines每行的单词中。
    这个函数同时还会计算每行输入输出的单词命中率（此行的已匹配单词总长度/此行单词总长度）。
    
    Args:
        input_lines(str): 输入的一段话
        output_lines(str): chatgpt给对齐好的一段话
    
    Returns:
        align_map(dict[int, set[int]]): 输出行号对应输入的行号
        input_hit_rate(list[float]): 输入每行的匹配率（匹配的单词总长度/本行总单词总长度）
        output_hit_rate(list[float]): 输出每行的匹配率

    Example:
        输入:
            行号    input_lines
            0       1. it's a beautiful
            1       day outside.
            2       2. birds are singing,
            3       flowers are
            4       blooming...
            5       3. on days like these,
            6       kids like you...
            7       4. Should
            8       be
            9       burning
            10      in hell.

            行号    output_lines
            0       1. it's a beautiful day outside.
            1       2. birds are singing, flowers are blooming...
            2       3. on days like these, kids like you...
            3       4. Should be burning in hell.

        输出:
            align_map: {0: {0, 1}, 1: {2, 3, 4}, 2: {5, 6}, 3: {7, 8, 9, 10}}
            input_hit_rate: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] (全部命中)
            output_hit_rate: [1.0, 1.0, 1.0, 1.0] (全部命中)

    """
    if isinstance(input_lines, str):
        input_lines = input_lines.splitlines()
    if isinstance(output_lines, str):
        output_lines = output_lines.splitlines()
    # 英文为内部对齐语言时可以根据词来对齐，中文为内部对齐语言时可以根据jieba分词来对齐
    # 按字符也行，效率会稍低
    input_tokens_info, output_tokens_info = tokenizer(input_lines, output_lines)

    # 算输入输出的每行的单词命中率，即：匹配的单词总字符数 / 单词总字符数
    input_hit_rate = [0 for _ in input_lines] 
    output_hit_rate = [0 for _ in output_lines]

    input_tokens = ''.join(map(lambda x: x[0], input_tokens_info))
    output_tokens = ''.join(map(lambda x: x[0], output_tokens_info))
    aligned_indexes = pylcs.lcs_sequence_idx(input_tokens, output_tokens) # 输入的每个单词的下标对应于输出的每个单词下标，不为-1失配的情况下保证是递增的
    align_map = {}
    for input_token_index, output_token_index in enumerate(aligned_indexes):
        if output_token_index != -1:
            _, input_word_length, input_lineid = input_tokens_info[input_token_index]
            _, output_word_length, output_lineid = output_tokens_info[output_token_index]
            # 每个output_lineid对应一段input_lineid的区间，是一个2元素的列表[l, r]，代表本段包含了源文本中行号区间为[l, r]之间的行
            align_map.setdefault(output_lineid, [input_lineid, input_lineid])[1] = input_lineid # 左区间(即[0])用setdefault填入，右区间由[1] = input_lineid更新
            input_hit_rate[input_lineid] += input_word_length
            output_hit_rate[output_lineid] += output_word_length

    for p, _ in enumerate(input_hit_rate):
        input_hit_rate[p] /= sum(map(len, input_lines[p].split())) + 1e-3
    for p, _ in enumerate(output_hit_rate):
        output_hit_rate[p] /= sum(map(len, output_lines[p].split())) + 1e-3

    # 额外处理：匹配率低于drop_th的olineid不要
    for p, i in enumerate(output_hit_rate):
        if i < drop_th:
            if p in align_map:
                align_map.pop(p)
    
    return align_map, input_hit_rate, output_hit_rate


use_proxy()


def align(en: str | list[str], zh: str | list[str], en_translated: str | list[str]) -> Tuple[list[Tuple[str, str]], list[str], str]:
    """
    1:n对齐，en为主文本(1)，zh为次文本(n)，en_translated为en的翻译文本。
    Args:
        en: 英文已成段文本(被翻译语言)
        zh: 中文未成段文本(算法内部对齐语言，n段和1段en对齐)
        en_translated: 英翻中之后的段落。应该是中文段落。列表长度应该跟en一样长
    Returns:
        aligned (list[Tuple[str, str]]): 对齐好的文本，每条是(英, 中)的格式
        dropped (list[Tuple[str, str]]): 对不上的英语段落文本
        preview (str): 对齐预览文本
    """
    if isinstance(en, str):
        en = en.splitlines()
    if isinstance(zh, str):
        zh = zh.splitlines()
    if isinstance(en_translated, str):
        en_translated = en_translated.splitlines()

    aligned = []
    dropped = []

    align_map, irate, orate = lcs_sequence_alignment(zh, en_translated, DROP_THRESHOLD, tokenize_by_char)
    # irate表示中文原文本对齐命中率，orate表示英翻中文本对齐命中率
    for paragraph_id, (line_id_lowerbound, line_id_upperbound) in align_map.items():
        aligned.append(':'.join([
            str(paragraph_id), # 源语言
            ','.join([str(line_id_lowerbound), str(line_id_upperbound)]), # 内部对齐语言
            # en[paragraph_id], 
            # ''.join(zh[line_id_lowerbound:line_id_upperbound + 1])
        ]))
    
    zh_ptr = 0
    preview_text = []
    for paragraph_id, paragraph in enumerate(en):
        if paragraph_id in align_map:
            line_id_lowerbound, line_id_upperbound = align_map[paragraph_id]
            while zh_ptr < line_id_lowerbound:
                preview_text.append("")
                preview_text.append(zh[zh_ptr])
                preview_text.append("")
                dropped.append(':'.join([
                    '1', 
                    str(zh_ptr), 
                    # zh[zh_ptr],
                ]))
                zh_ptr += 1
            zh_ptr = line_id_upperbound + 1
            preview_text.append("")
            preview_text.append(''.join(zh[line_id_lowerbound:line_id_upperbound + 1]))
            preview_text.append("~" * 20)
            preview_text.append(paragraph)
            preview_text.append("")
        else:
            preview_text.append("")
            preview_text.append(paragraph)
            preview_text.append("")
            dropped.append(':'.join([
                '0',
                str(paragraph_id), 
                # paragraph,
            ]))
    
    return aligned, dropped, '\n'.join(preview_text)


def map_func(row):
    last_time = datetime.datetime.now()
    rec = row['record']
    zh = row['clean_zh']
    en = row['clean_en']
    tr_en = row['en2zh']
    aligned, dropped, preview = align(en, zh, tr_en)
    with (OUTDIR / (rec + '_en2zh.txt')).open('w', encoding='utf-8') as f:
        f.write(preview)
    ima = datetime.datetime.now()
    row['aligned'] = aligned
    row['dropped'] = dropped
    print(rec, dropped, ima - last_time)
    return row

def gen(src = Path(r'F:\undl_en2zh_10')):
    for son in os.listdir(src):
        ds = datasets.load_from_disk(src / son)
        ds = ds.map(map_func)
        yield from ds


def read_secret(key: str) -> str:
    v = os.environ[key] = os.environ.get(key) or input(f"Please input {key}:")    
    return v

OUTDIR = Path(r'F:\new_out')
SAVEDIR = Path(r'F:\align_testset')
if __name__ == '__main__':
    OUTDIR.mkdir(exist_ok=True)
    SAVEDIR.mkdir(exist_ok=True)
    ds = datasets.Dataset.from_generator(gen)
    dds = ds.map(map_func)
    ds.save_to_disk(SAVEDIR)
    # ds = datasets.load_from_disk(SAVEDIR)
    # use_proxy()
    # ds.push_to_hub(repo_id='undl_align_10', split='train', token=read_secret('HF_TOKEN'))
