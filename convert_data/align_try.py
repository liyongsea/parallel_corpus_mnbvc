import datetime
import os
from alignment_by_translate_en2zh import align
from collections import namedtuple
from typing import Tuple
from itertools import chain

import pylcs
from transformers import pipeline

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

def lcs_sequence_alignment(input_lines: list[str] , output_lines: list[str], drop_th=0.6, tokenizer=tokenize_by_space_splited_word) -> Tuple[dict[int, Tuple[int, int]], list[float], list[float]]:
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
    # 考虑到运行效率，我们切分粒度采用空格隔开的单词而不是字母
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

    # 额外处理：匹配率低于60%的olineid不要
    print(align_map)
    print('orate', output_hit_rate)
    for p, i in enumerate(output_hit_rate):
        if i < drop_th:
            if p in align_map:
                align_map.pop(p)
    
    return align_map, input_hit_rate, output_hit_rate


use_proxy()
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
TRANSLATOR_MODEL_NAME = f"Helsinki-NLP/opus-mt-en-zh"
TRANSLATOR_TOKENIZER = AutoTokenizer.from_pretrained(TRANSLATOR_MODEL_NAME)
TRANSLATOR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATOR_MODEL_NAME).cuda()

def _tokenize(input_text: str) -> torch.Tensor:
    return TRANSLATOR_TOKENIZER(input_text, return_tensors="pt")

def _translate(input_tokens: torch.Tensor) -> str:
    """翻译英文文本为中文文本"""
    with torch.no_grad():
        output = TRANSLATOR_MODEL.generate(**input_tokens.to('cuda'))
    translated_text = TRANSLATOR_TOKENIZER.decode(output[0], skip_special_tokens=True)
    return translated_text

def translate(en: str | list[str]) -> list[str]:
    """翻译英文段落为中文段落"""
    if isinstance(en, str):
        en = en.splitlines()
    translated = []
    for paragraph in en:
        paragraph_translation = []
        words = paragraph.split()
        while words:
            rptr = min(len(words), 512) # token数必须确定句子才能确定，所以这里用512作为上限，用二分法（更像是二进制指数退避？）找到最大能用的token数
            tokens = _tokenize(' '.join(words[:rptr]))
            if tokens.input_ids.shape[1] > 512:
                lptr = 1 # 以1为界保证递增
                while lptr < rptr - 1:
                    mid = (lptr + rptr) // 2
                    test_tokens = _tokenize(' '.join(words[:mid]))
                    if test_tokens.input_ids.shape[1] > 512:
                        rptr = mid
                    else:
                        lptr = mid
                        tokens = test_tokens
                        break # 实际上我们不需要找到边界，拿一段出来能够翻译的就行了
            else:
                lptr = rptr
            if tokens.input_ids.shape[1] > 512:
                raise RuntimeError("Algorithm error")
            paragraph_translation.append(_translate(tokens))
            words = words[lptr:]
        translated.append(''.join(paragraph_translation))
    return translated
    

def align(en: str | list[str], zh: str | list[str], en_translated: str | list[str] = None) -> Tuple[list[Tuple[str, str]], list[str], str]:
    """
    Args:
        en: 英文已成段文本
        zh: 中文未成段文本
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

    if not en_translated:
        en_translated = translate(en)

    aligned = []
    dropped = []

    align_map, irate, orate = lcs_sequence_alignment(zh, en_translated, 0.2, tokenize_by_char)
    # irate表示中文原文本对齐命中率，orate表示英翻中文本对齐命中率
    print(irate) # 这两个变量仅用于诊断，这里用print输出而不是打日志
    print(orate)
    for paragraph_id, (line_id_lowerbound, line_id_upperbound) in align_map.items():
        aligned.append((''.join(zh[line_id_lowerbound:line_id_upperbound + 1]), en[paragraph_id]))
    
    zh_ptr = 0
    preview_text = []
    for paragraph_id, paragraph in enumerate(en):
        if paragraph_id in align_map:
            line_id_lowerbound, line_id_upperbound = align_map[paragraph_id]
            while zh_ptr < line_id_lowerbound:
                preview_text.append("")
                preview_text.append(zh[zh_ptr])
                preview_text.append("")
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
            dropped.append(paragraph)
    
    return aligned, dropped, '\n'.join(preview_text)



if __name__ == '__main__':
    SOURCE_DIR = r'E:\motrixDL\baiduyun\MNBVC\sample_100'
    last_time = datetime.datetime.now()
    for i in os.listdir(SOURCE_DIR):
        dirpath = os.path.join(SOURCE_DIR, i)
        dirlist = os.listdir(dirpath)
        cn = ''
        en = ''
        for j in os.listdir(dirpath):
            if j.startswith("中文"):
                cn = j
            elif j.startswith("英文"):
                en = j
        outfile = os.path.join(dirpath, 'en-zh.txt')
        if cn and en and not os.path.exists(outfile):
            with open(os.path.join(dirpath, cn), 'r', encoding='utf-8', errors='ignore') as f: # '英文-N1507770.DOCx'
                cn = f.read().split('\n\n')
            with open(os.path.join(dirpath, en), 'r', encoding='utf-8', errors='ignore') as f:
                en = f.read().split('\n\n')
            aligned, dropped, preview = align(en, cn)
            ima = datetime.datetime.now()
            print(i, dropped, ima - last_time)
            last_time = ima
            with open(outfile, 'w', encoding='utf-8') as f:
                f.write(preview)