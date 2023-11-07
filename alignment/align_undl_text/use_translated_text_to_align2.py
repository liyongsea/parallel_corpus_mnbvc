import datetime
import os
from pathlib import Path
import shutil
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

REPLACE_MAP = {
    '，': ',',
    '（': '(',
    '）': ')',
    '？': '?',
    # '。': '.',
    '：': ':',
    '；': ';',
    '“': '"',
    '”': '"',
    '‘': "'",
    '’': "'",
    '！': '!',
}
def replace_zh_punctuation(text: str) -> str:
    return ''.join(map(lambda x: REPLACE_MAP.get(x, x), text))

def tokenize_by_jieba(input_lines: list[str], output_lines: list[str], offset=0) -> Tuple[list[LCSTokenInfo], list[LCSTokenInfo]]:
    """"""
    import jieba
    word_dict = {}
    input_tokens_info = []
    output_tokens_info = []
    for input_line_id, input_line in enumerate(input_lines):
        for word in jieba.cut(replace_zh_punctuation(input_line)):
            word = word.strip()
            if word:
                input_tokens_info.append(LCSTokenInfo(
                    chr(offset + word_dict.setdefault(word, len(word_dict))),
                    len(word),
                    input_line_id,
                    ))
        
    for output_line_id, output_line in enumerate(output_lines):
        for word in jieba.cut(replace_zh_punctuation(output_line)):
            word = word.strip()
            if word in word_dict: # 为子序列写的优化
                output_tokens_info.append(LCSTokenInfo(
                    chr(offset + word_dict[word]),
                    len(word),
                    output_line_id,
                    ))
    return input_tokens_info, output_tokens_info


def lcs_sequence_alignment(input_lines: list[str] , output_lines: list[str], drop_th=DROP_THRESHOLD, tokenizer=tokenize_by_space_splited_word):
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
    for input_token_index, output_token_index in enumerate(aligned_indexes):
        if output_token_index != -1:
            _, input_word_length, input_lineid = input_tokens_info[input_token_index]
            _, output_word_length, output_lineid = output_tokens_info[output_token_index]
            # 每个output_lineid对应一段input_lineid的区间，是一个2元素的列表[l, r]，代表本段包含了源文本中行号区间为[l, r]之间的行
            input_hit_rate[input_lineid] += input_word_length
            output_hit_rate[output_lineid] += output_word_length

    for p, _ in enumerate(input_hit_rate):
        input_hit_rate[p] /= sum(map(len, input_lines[p].split())) + 1e-3

    for p, _ in enumerate(output_hit_rate):
        output_hit_rate[p] /= sum(map(len, output_lines[p].split())) + 1e-3


    # 我们需要构造一个 set => set 的映射关系，这是n:m对齐的关键
    edges = {} # 化简成图
    for input_token_index, output_token_index in enumerate(aligned_indexes):
        if output_token_index != -1:
            _, _, input_lineid = input_tokens_info[input_token_index]
            _, _, output_lineid = output_tokens_info[output_token_index]
            if input_hit_rate[input_lineid] >= drop_th and output_hit_rate[output_lineid] >= drop_th:
                edges.setdefault(f"i{input_lineid}", set()).add(f"o{output_lineid}")
                edges.setdefault(f"o{output_lineid}", set()).add(f"i{input_lineid}")
    
    # bfs求连通块
    set2set = []

    while edges:
        n, e = edges.popitem()
        vis = {n}
        q = [e]
        while q:
            e = q.pop()
            for i in e:
                vis.add(i)
                if t := edges.pop(i, None):
                    q.append(t)
        il = []
        ol = []
        for k in vis:
            if k.startswith('i'):
                il.append(int(k[1:]))
            else:
                ol.append(int(k[1:]))
        il.sort()
        ol.sort()
        set2set.append((il, ol))
    return set2set


def align(ilang: str | list[str], olang: str | list[str], ilang_tr: str | list[str]) -> Tuple[list[Tuple[str, str]], list[str], str]:
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
    if isinstance(ilang, str):
        ilang = ilang.splitlines()
    if isinstance(olang, str):
        olang = olang.splitlines()
    if isinstance(ilang_tr, str):
        ilang_tr = ilang_tr.splitlines()

    if len(ilang) != len(ilang_tr):
        assert len(ilang) == len(ilang_tr), f"len inequal, {len(ilang)}, {len(ilang_tr)}"

    aligned = []
    aligned_pairs = []
    preview_text = []

    ivis = set()
    ovis = set()
    set2set = lcs_sequence_alignment(olang, ilang_tr, DROP_THRESHOLD, tokenizer=tokenize_by_space_splited_word)
    set2set.sort(key=lambda x: x[0][0])
    for oset, iset in set2set:
        aligned.append(','.join(map(str, iset)) + '|' + ','.join(map(str, oset)))
        itmp = '\n'.join(map(lambda x: ilang[x], iset))
        otmp = '\n'.join(map(lambda x: olang[x], oset))
        aligned_pairs.append((itmp, otmp))
        preview_text.append("")
        preview_text.append(itmp)
        preview_text.append("~" * 10)
        preview_text.append(otmp)
        preview_text.append("")
        for x in iset: ivis.add(x)
        for x in oset: ovis.add(x)

    preview_text.append('#' * 10)

    for p, i in enumerate(ilang):
        if p not in ivis:
            preview_text.append("")
            preview_text.append(i)
            preview_text.append("")
    
    preview_text.append('#' * 10)

    for p, i in enumerate(olang):
        if p not in ovis:
            preview_text.append("")
            preview_text.append(i)
            preview_text.append("")
    
    return aligned, aligned_pairs, '\n'.join(preview_text)


# cnt = 0
# c2 = 0
def map_func(ds):
    li = []
    for rid, row in enumerate(ds):
        rec = row['record']
        src = row[f'clean_{SRC}']
        dst = row[f'clean_{DST}']
        tr = row[f'{SRC}2{DST}']
        if src and dst:
            aligned, pairs, preview = align(src, dst, tr)
            with (OUTDIR / (rec + '.txt')).open('w', encoding='utf-8') as f:
                f.write(preview)
            for apairs, atext in zip(aligned, pairs):
                i, o = atext
                li.append({'record': rec, 'clean_para_index_set_pair': apairs, 'src': SRC, 'dst': DST, 'src_text': i, 'dst_text': o})
    return li

from load_and_translate import clean_paragraph
import re
import pickle

BASE_DIR = Path(r'F:')
TASK_SOURCE = BASE_DIR / 'undl_text_local'
DS = datasets.load_from_disk(TASK_SOURCE)
SRC = 'de'
DST = 'en'
STEP = 10

def gen_dump_translated_text():
    srcs = (Path(rf'F:\{SRC}2{DST}\argos'), )
    for src in srcs:
        for son in list(os.listdir(src)):
            sid = int(son)
            data = DS.select(range(sid, sid + STEP))
            data = data.map(lambda x: {f'clean_{SRC}': list(filter(bool, (clean_paragraph(para) for para in re.split('\n\n', x[SRC]))))})
            data = data.map(lambda x: {f'clean_{DST}': list(filter(bool, (clean_paragraph(para) for para in re.split('\n\n', x[DST]))))})
            with open(src / son / 'dup.pkl', 'rb') as f:
                tr = pickle.load(f)
            for i, dt in enumerate(data):
                if not any(dt[f'clean_{SRC}']) or not any(dt[f'clean_{DST}']):
                    # x.append([])
                    if 0 != len(tr[i]):
                        print(sid, i, f"unexpected translation, {len(dt[f'clean_{SRC}'])}, {len(dt[f'clean_{DST}'])}, {len(tr[i])}")
                        shutil.rmtree(src / son)
                        break
                    yield {f'clean_{SRC}': [], f'clean_{DST}': [], 'record': dt['record'], f'{SRC}2{DST}': tr[i]}
                else:
                    # x.append(i[f'clean_{SRC}'])
                    if len(dt[f'clean_{SRC}']) != len(tr[i]):
                        print(sid, i, f"len inequal, {len(dt[f'clean_{SRC}'])}, {len(tr[i])}")
                        shutil.rmtree(src / son)
                        break
                    yield {f'clean_{SRC}': dt[f'clean_{SRC}'], f'clean_{DST}': dt[f'clean_{DST}'], 'record': dt['record'], f'{SRC}2{DST}': tr[i]}


def read_secret(key: str) -> str:
    v = os.environ[key] = os.environ.get(key) or input(f"Please input {key}:")    
    return v

OUTDIR = Path(rf'F:\new_out2_{SRC}2{DST}')
DUMP_TRANSLATION_PATH = Path(rf'F:\dump_tr_{SRC}2{DST}')
METHOD2_PREVIEW_DS_PATH = Path(rf'F:\method2_ds_{SRC}2{DST}')

if __name__ == '__main__':
    OUTDIR.mkdir(exist_ok=True)
    DUMP_TRANSLATION_PATH.mkdir(exist_ok=True)
    METHOD2_PREVIEW_DS_PATH.mkdir(exist_ok=True)
    # ds = datasets.Dataset.from_generator(gen_dump_translated_text)
    # ds.save_to_disk(DUMP_TRANSLATION_PATH)
    ds = datasets.load_from_disk(DUMP_TRANSLATION_PATH)
    ds = datasets.Dataset.from_list(map_func(ds))
    ds.save_to_disk(METHOD2_PREVIEW_DS_PATH)
    # use_proxy()
    # ds.push_to_hub(repo_id=f'undl_{SRC}2{DST}_translation', split='train', token=read_secret('HF_TOKEN'), )

