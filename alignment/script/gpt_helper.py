import datetime
from difflib import SequenceMatcher
import itertools
import os
import time
import json
import traceback
import re
from collections import OrderedDict, namedtuple
from typing import Tuple
from pathlib import Path
from itertools import chain
import requests

import pylcs
import tiktoken
import datasets

from datasets.dataset_dict import DatasetDict

MAX_TOKEN_COUNT = 1400
WORKDIR_ABSOLUTE = os.path.dirname(os.path.abspath(__file__)) # 工作区绝对路径，为方便调试使用，实际使用换成.即可
RETRY_TIME = 5
SLEEP_TIME = 0

encoder_gpt35 = tiktoken.encoding_for_model("gpt-3.5-turbo")
exception_files = set()

## path
def cat(*args): 
    return '/'.join(args)

def my_path(*args):
    """相对路径"""
    return cat(WORKDIR_ABSOLUTE, *args)

def get_and_cache_dataset():
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(my_path())
    except:
        dataset = datasets.load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED', split='train')
        dataset.save_to_disk(my_path())
    dataset = dataset.select(range(500))
    #.filter(lambda x: x['record'] not in exception_files)
    return dataset

def make_banner(record: str) -> str:
    divider = '=' * 10 + '\n'
    return  divider + record + '\n' + divider

## web
def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

def read_secret(key: str) -> str:
    v = os.environ[key] = os.environ.get(key) or input(f"Please input {key}:")    
    return v

def generate_prompt(input_content: str): 
    return [
        {'role': 'user', 'content':'''Your task is to solve a breakline elimination problem for text exported from PDF. The input may contain unexpected breaklines that split paragraphs, and you should join adjacent lines if they can form a meaningful paragraph and replace the breakline symbols as spaces. You should leave some lines that cannot form a paragraph as they are.

Please note that you should only determine which breaklines to keep or replace and leave other text unchanged. Do not add any words or characters to the input text or provide additional information beyond the requested output.

If there is no breakline symbol should be replaced, just echo the input text as it is.

Additionally, please ensure that pagination and indexing information remains on its own line and does not get joined with adjacent paragraphs. Your response should maintain the original structure of the input while eliminating unnecessary breaklines.
    '''},
        {"role": "assistant", "content": 'Please provide your text.'},
        {"role": "user", "content": input_content},
        {"role": "assistant", "content": 'Output:\n'}
    ]

class ContextLengthExceeded(Exception): pass
class UnknownException(Exception): pass

def request_gpt_segment(prompt: str):
    """主体，入参prompt是向chatgpt问的内容，debug_prompt是让它打印内容，production只打下标"""

    k = read_secret('OPENAI_TOKEN')
    r = requests.post(
        # "https://api.openai.com/v1/chat/completions",
        "https://openai-proxy-syhien.pages.dev/v1/chat/completions", # cf反代
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + k
            },
            json={
                # "model": "text-davinci-003",
                "model": "gpt-3.5-turbo",
                # "model": "gpt-4",
                "messages": generate_prompt(prompt),
                # "temperature": 0, 
                # "max_tokens": 4000 - int(tokens * 1.3)
            },
            timeout= 60 * 5 # 我们顶多等5分钟
        )
    try:
        j = r.json()
        print(j)
    except json.JSONDecodeError:
        j = json.loads('{' + r.text) # 反代有时候只会漏前导'{'，尝试救回来
        print('fixed j:', j)

    with open(my_path('chatgptoutputs.jsonl'), 'a', encoding='utf-8') as f: # 日志
        f.write(r.text)
    if 'error' in j:
        err = j['error']
        if 'code' in err and err['code'] == 'invalid_request_error':
            raise ContextLengthExceeded(err['message'])
        else:
            raise UnknownException(err['message'])
            # with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
            #     f.write(r.text)
    return j['choices'][0]['message']['content']

## algorithm
def clearup_output(raw_output_from_chatgpt: str) -> list[str]:
    return list(filter(lambda x: len(x.strip()), raw_output_from_chatgpt.splitlines()))

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

def get_br_indexes_from_alignmap(align_map: dict[int, set[int]]) -> list[int]:
    br = []
    for igroups in align_map.values():
        for i in igroups:
            if i + 1 in igroups:
                br.append(i)
    br.sort()
    return br

## mapping functions
def ask_gpt_for_one_file(row: DatasetDict):
    try:
        inputs = row['en'].replace('\ufffe', '-')
        en_rate = len(re.findall(r'[a-zA-Z]', inputs)) / len(inputs) if len(inputs) else 0
        print(en_rate)
        if en_rate < 0.3:
            # 435951编码错误，要滤掉这种情况
            print('filtered')
            return
        input_lines = inputs.splitlines() 
        rec = row['record']
        visited = {}

        Path(my_path('done')).mkdir(exist_ok=True)
        output_file_name = my_path(f'done/gpt_en_{rec}.jsonl')

        if os.path.exists(output_file_name):
            with open(output_file_name, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            for json_line in saved_content.splitlines():
                json_line = json_line.strip()
                if json_line:
                    infos = json.loads(json_line)
                    if infos['step'] == MAX_TOKEN_COUNT:
                        visited[infos['batch']] = infos

        # last: list[str] = ['']
        def gen_batch(begin_lineid: int):
            """从begin_lineid开始拿一个batch"""
            assert begin_lineid < len(input_lines)
            buf = ''
            for lineid in range(begin_lineid, len(input_lines)):
                line = input_lines[lineid]
                tmp = (buf + '\n' if len(buf)>0 else '') + line
                tks = encoder_gpt35.encode(tmp) # 如果能保证每行加起来等于总的，那么可以改写成O(n)的
                if len(tks) >= MAX_TOKEN_COUNT:
                    return buf, lineid # 本行还没加上，所以是开区间
                buf = tmp
            if buf:
                return buf, lineid + 1

        todo_lineid = 0
        batch_id = 0

        while todo_lineid < len(input_lines):
            batch, lineid = gen_batch(todo_lineid)

            if batch_id in visited:
                todo_lineid = visited[batch_id]['r'] + 1
            else:
                for retrytime in range(RETRY_TIME):
                    try:
                        if len(encoder_gpt35.encode(batch)) < 20: # 结尾不能成段的噪声可能会让gpt疯狂道歉，这种情况下我们放过
                            last_input_lineid = len(input_lines)
                            todo_lineid = len(input_lines)
                            break

                        outputs = request_gpt_segment(batch)
                        outputlines = clearup_output(outputs)

                        align_map, irate, orate = lcs_sequence_alignment(batch, outputlines)
                        input_line_offset = lineid - len(batch.splitlines()) # 第一行在本文件中的下标
                        assert input_lines[input_line_offset] == batch.splitlines()[0]
                        if lineid < len(input_lines):
                            if len(align_map) > 1:
                                align_map.pop(max(align_map.keys())) # 干掉最后一个分组，避免不完全成段

                            last_input_lineid = max(chain(*align_map.values())) + input_line_offset
                            todo_lineid = last_input_lineid + 1 
                        else:
                            # 已经做完了本文件
                            last_input_lineid = len(input_lines)
                            todo_lineid = len(input_lines)


                        br = []
                        for igroups in align_map.values():
                            for igroup in igroups:
                                if igroup + 1 in igroups:
                                    br.append(igroup + input_line_offset)
                        br.sort()
                        
                        with open(output_file_name, 'a', encoding='utf-8') as f:
                            json.dump({
                                'batch': batch_id, 
                                'step': MAX_TOKEN_COUNT, 
                                'l': min(chain(*align_map.values())) + input_line_offset, 
                                'r': last_input_lineid, 
                                'input': batch, 
                                'output': outputs,
                                'offset': input_line_offset,
                                'br': br
                                }, f)
                            f.write('\n')

                        break
                    except ContextLengthExceeded as e:
                        with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                            json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'context_length_exceeded', 'msg': str(e.args)}, f)
                            f.write('\n')
                    except UnknownException as e:
                        with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                            json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'unknown_response', 'msg': str(e.args)}, f)
                            f.write('\n')
                    except requests.exceptions.ReadTimeout:
                        with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                            json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'timeout', 'msg': str(e.args)}, f)
                            f.write('\n')
                    except KeyboardInterrupt:
                        print('interrupted by keyboard.')
                        exit(0)
                    except Exception as e:
                        traceback.print_exc()
                        with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                            json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'unknown', 'msg': str(e.args)}, f)
                            f.write('\n')
                        print('retry:', retrytime, e)
                        if retrytime == RETRY_TIME - 1:
                            raise
                        print(f'sleep for {SLEEP_TIME}s')
                        time.sleep(SLEEP_TIME)

                print(f'sleep for {SLEEP_TIME}s')
                time.sleep(SLEEP_TIME)

            batch_id += 1
    except Exception as e:
        with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f:
            json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'exc': 'runtime_error', 'msg': traceback.format_exc()}, f)
            f.write('\n')
        with open(my_path('exception_files.txt'), 'a', encoding='utf-8') as f:
            f.write(rec + '\n')

def post_process_for_one_file(row: DatasetDict):
    """后处理，将分批的已请求的jsonl文件整合成一个文件对应的下标idx文件，即soft_linebreak的下标"""
    from loguru import logger
    logger.add(open('log.txt', 'a'))
    inputs = row['en'].replace('\ufffe', '-')
    ilines = inputs.splitlines() # input lines
    rec = row['record']
    output_file_name = my_path(f'done/gpt_en_{rec}.jsonl')
    if not os.path.exists(output_file_name):
        return
    
    # if rec == '448094':
        # print('bp1')
    obatches = [] # output batches
    soft_linebreak_indexes = set()

    with open(output_file_name, 'r', encoding='utf-8') as f:
        flines = f.read().splitlines()
        for p, i in enumerate(flines):
            j = json.loads(i) # batch(int):批次号 step(int):步长，即MAX_TOKEN_COUNT input(str):输入文本 output(str):输出文本 l(int):左边界行号，上次处理的 r(int):右边界行号
            soft_linebreak_indexes = soft_linebreak_indexes.union(j['br'])
            obatches.append(j['output'])
            obatches.append('==========')

    concated = []
    for lineid, iline in enumerate(ilines):
        if lineid - 1 in soft_linebreak_indexes:
            concated[-1] += ' ' + iline
        else:
            concated.append(iline)
    Path(my_path('post')).mkdir(exist_ok=True)
    print(len(concated))

    with open(my_path('post', f'{rec}.src'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(obatches))
    with open(my_path('post', f'{rec}.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(concated))
    with open(my_path('post', f'{rec}.idx'), 'w', encoding='utf-8') as f:
        f.write(','.join(map(str, list(sorted(soft_linebreak_indexes)))))

## methods
def ask_gpt():
    """
    use gpt to segment paragraph, results will be saved as jsonl file to `done` directory.
    previous archive will be checked when restart so no duplicated requests will be made.
    """
    get_and_cache_dataset().map(ask_gpt_for_one_file)

def post_process():
    """
    post-process the files in `done` directory and generate `idx` file to `post` directory.
    `idx` file: machine readable indexes file for indicated which breakline should be deleted.
    `txt` file: human readable (and only for reviewed) text file showing segmented paragraph from `idx` file.
    `src` file: concated gpt's raw output.
    """
    get_and_cache_dataset().map(post_process_for_one_file)

def convert_output_text_to_idx():
    """
    convert output text file to idx file (so then it can be uploaded to hf).
    results will be dumped to `converted` directory.
    """
    Path(my_path('converted')).mkdir(exist_ok=True)
    record_id = input('record id:')
    with open(
        input('Please specify the output text file (support drag):'), 
        'r', encoding='utf-8') as f:
        output = f.read()
    
    for i in get_and_cache_dataset().filter(lambda x: x['record'] == record_id):
        pos = my_path('converted', f'{record_id}.idx')
        ilines = i['en']
        align_map, irate, orate = lcs_sequence_alignment(ilines, output)
        br = get_br_indexes_from_alignmap(align_map)
        with open(pos, 'w', encoding='utf-8') as f:
            f.write(','.join(map(str, br)))

        br = set(br) # br就是需要干掉的换行下标
        concated = []
        for lineid, iline in enumerate(ilines.splitlines()):
            if lineid - 1 in br:
                concated[-1] += ' ' + iline
            else:
                concated.append(iline)

        with open(my_path('converted', f'{record_id}.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(concated))

        print('indexing file saved to', os.path.abspath(pos))

def push_idx_to_hf():
    """
    push `idx` file to huggingface, using `is_hard_linebreak` format.
    """
    ds = get_and_cache_dataset()

    def convert_idx():
        dir = input('directory contain idx files:')
        idx_map = {}
        for i in os.listdir(dir):
            if i.endswith('.idx'):
                rec = i.removesuffix('.idx')
                with open(cat(dir, i), 'r', encoding='utf-8') as f:
                    fcontent = f.read().strip()
                    if fcontent:
                        idx_map[rec] = map(int, fcontent.split(','))
                    else:
                        print(i, 'not contain any br')
        upload_pending = []
        for i in ds.filter(lambda x: x['record'] in idx_map):
            br_rev = [True] * i['en'].count('\n')
            for j in idx_map[i['record']]:
                br_rev[j] = False
            upload_pending.append({'record': i['record'], 'raw_text': i['en'], 'is_hard_linebreak': br_rev})
        return upload_pending

    def convert_manual():
        """临时代码，转换手标数据"""
        dir = input('directory contain manual segmentation output text files:')
        outputmap = {}
        # jmap = {}
        for i in os.listdir(dir):
            with open(cat(dir, i, 'output.txt'), 'r', encoding='utf-8') as f:
                outputmap[i] = f.read()
            # with open(cat(dir, i, 'is_hard_line_break.json'), 'r', encoding='utf-8') as f:
                # jmap[i] = json.load(f)
        upload_pending = []
        for i in ds.filter(lambda x: x['record'] in outputmap):
            rec = i['record']
            src = i['en']
            align_map, _, _ = lcs_sequence_alignment(src, outputmap[rec])
            br = get_br_indexes_from_alignmap(align_map)
            br_rev = [True] * src.count('\n')
            for j in br:
                br_rev[j] = False
            # assert br_rev == jmap[rec] # 顺便测一下对齐脚本正确性
            upload_pending.append({'record': i['record'], 'raw_text': i['en'], 'is_hard_linebreak': br_rev})
        return upload_pending
    
    upload_pending = convert_manual()
    hf_tk = read_secret('HF_TOKEN')
    print('dataset length:', len(upload_pending))
    upload_pending = datasets.Dataset.from_list(upload_pending)
    upload_pending.push_to_hub(repo_id='human_joined_en_paragraph_19', split='train', token=hf_tk)

def download_and_visualize():
    """
    download dataset and dump as text file to `dump` directory for human reviewing and editing
    """
    Path(my_path('dump')).mkdir(exist_ok=True)

    def dump_to_file(row):
        raw = row['raw_text']
        rec = row['record']
        br_rev = row['is_hard_linebreak']
        buf = []
        for p, i in enumerate(raw.splitlines()):
            if p == 0:
                buf.append(i)
            elif br_rev[p - 1]:
                buf.append(i)
            else:
                buf[-1] += ' ' + i # use += ' ❤ ' + i for visualizing the breakline deleted
        with open(my_path('dump', f'{rec}.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(buf))

    datasets.load_dataset('bot-yaya/EN_PARAGRAPH_GPT_JOINED', split='train').map(dump_to_file)
    

def translate_and_align():
    """
    translate and align
    just a idea
    ########################
    ###UNDER CONSTRUCTION###
    ########################
    """
    use_proxy()
    from transformers import pipeline
    # tr = pipeline("translation", model=f"Helsinki-NLP/opus-mt-zh-en", device='cuda:0')
    tr = pipeline("translation", model=f"Helsinki-NLP/opus-mt-en-zh", device='cuda:0')

    hm = datasets.load_dataset('bot-yaya/human_joined_en_paragraph_19', split='train').filter(lambda x: x['record'] != '515053')
    recs = {x['record'] for x in hm}

    ALIGN_LOG_FILE_NAME = my_path('aligned.txt')
    if os.path.exists(ALIGN_LOG_FILE_NAME):
        os.remove(ALIGN_LOG_FILE_NAME)

    DISCARD_LOG_FILE_NAME = my_path('discard.txt')
    if os.path.exists(DISCARD_LOG_FILE_NAME):
        os.remove(DISCARD_LOG_FILE_NAME)

    def translate(row):
        translated = []
        br_rev = hm.filter(lambda x: x['record'] == row['record'])[0]['is_hard_linebreak']

        buf = []
        for p, i in enumerate(row['en'].lower().splitlines()):
            if p == 0:
                buf.append(i)
            elif br_rev[p - 1]:
                buf.append(i)
            else:
                buf[-1] += ' ' + i

        for en_para in buf:
            tmp = []
            translated.append('')
            for word in en_para.split():
                tmp.append(word)
                if len(tmp) >= 350 or sum(map(len, tmp)) >= 1024:
                    translated[-1] += ''.join(tr(' '.join(tmp))[0]['translation_text'])
                    tmp.clear()
            if tmp:
                translated[-1] += ''.join(tr(' '.join(tmp))[0]['translation_text'])
        row['buf'] = buf
        row['translated_en_zh'] = translated
        return row

    def align(row):
        buf = row['buf']
        z = row['zh']
        zls = z.splitlines()
            
        align_map, irate, orate = lcs_sequence_alignment(zls, row['translated_en_zh'], 0.2, tokenize_by_char)
        print(align_map)
        print(irate)
        print(orate)

        with open(ALIGN_LOG_FILE_NAME, 'a', encoding='utf-8') as f:
            f.write(make_banner(row['record']) + '\n')
        
        with open(DISCARD_LOG_FILE_NAME, 'a', encoding='utf-8') as f:
            f.write(make_banner(row['record']) + '\n')


        for o, (il, ir) in align_map.items():
            zh_para = ''.join(zls[il:ir + 1])
            en_para = buf[o]
            print(zh_para)
            print(en_para)
            print()
            print('================')
            print()
            with open(ALIGN_LOG_FILE_NAME, 'a', encoding='utf-8') as f:
                f.write(zh_para + '\n')
                f.write(en_para + '\n')
                f.write('\n')
                f.write('================\n')
                f.write('\n')

        for oid, o in enumerate(buf):
            if oid not in align_map:
                with open(DISCARD_LOG_FILE_NAME, 'a', encoding='utf-8') as f:
                    f.write(o + '\n')
    translated_dataset = (
        datasets.load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED', split='train')
        .filter(lambda x: x['record'] in recs)
        .map(translate)
    )
    translated_dataset.map(align)

def preprocess_and_upload_dataset():
    from collections import Counter
    LANGS = ['zh', 'fr', 'es', 'ru', 'en']
    PAGINATION_TOKEN = '\n----\n'
    PREPROCESS_DIR = 'preprocessed_dump'
    HEADER_SCAN_LIMIT = 100
    DIGITS_PATTERN = re.compile('^\d+$')
    MATCHER_RATIO = 0.72
    FILTER_LOG = 'preprocessed_log.jsonl'
    Path(my_path(PREPROCESS_DIR)).mkdir(exist_ok=True)
    if os.path.exists(my_path(FILTER_LOG)):
        os.remove(my_path(FILTER_LOG))

    def make_filter_log(filtered: str, record: str | int, lang: str, page: str | int, reason: str):
        """将过滤的内容写到log里方便分析"""
        with open(my_path(FILTER_LOG), 'a', encoding='utf-8') as f:
            json.dump({'record': str(record), 'lang': lang, 'page': str(page), 'reason': reason, 'filtered': filtered}, f)
            f.write('\n')

    def drop_pagination_header_and_footer(row: DatasetDict):
        """语种无关过滤页眉（包括页码），不依赖任何正则，仅依靠自身和其它语种中出现的文本块频度统计实现

        Args：
            row (DatasetDict): datasets map进来的行，内含一篇文章的六个语种版本，每页用\n----\n隔开
        Returns:
            row (DatasetDict): 清洗后按原格式组装的row
        """
        record = row['record']

        file_content = {}
        token_spots = {}
        line_spots = {}
        page_token_slotses = {}

        overall_token_spots = Counter()
        overall_pages_num = 0

        # maxpage = 0
        for lang in LANGS:
            file_content[lang] = pages = row[lang].split(PAGINATION_TOKEN)
            overall_pages_num += len(pages)
        #     maxpage = max(maxpage, len(pages))
            token_spots[lang] = token_spot = Counter()  # token计数表，只用来完全匹配，其中页码特判
            # 行计数表，比token粒度更大，用于difflib的近似匹配
            line_spots[lang] = line_spot = Counter()
            page_token_slotses[lang] = page_token_slots = [
                set() for _ in pages]  # 每个用来装页眉的token，仅用来判断疑似页码的数字

            for pageid, page in enumerate(pages):
                lines = page.strip().splitlines()
                page = pages[pageid] = '\n'.join(lines)

                # 页眉只最多取前100字符
                for lineid, line in enumerate(page[:HEADER_SCAN_LIMIT].splitlines()):
                    for token in line.split():
                        # if len(token) < 2: # 单字符的token太危险，不能要
                        # continue
                        page_token_slots[pageid].add(token)
                        token_spot[token] += 1
                    line_digest = line.replace(' ', '')
                    if line_digest:
                        # 行计数表是用于尝试清除类似P a g e 2这种形式的页码
                        line_spot[line_digest] += 1

            for token, ctr in token_spot.items():
                overall_token_spots[token] += ctr

            # 去掉只出现少数的token，提高效率
            for x in list(token_spot.keys()):
                if token_spot[x] < 3 or token_spot[x] > len(pages):
                    token_spot.pop(x)

        for lang, pages in file_content.items():
            token_spot = token_spots[lang]
            line_spot = line_spots[lang]
            page_token_slots = page_token_slotses[lang]

            pagination_offset = 1
            maxcombo = 0
            for offset in range(-9, 3):  # 0 1 2
                combo = 0
                for pageid in range(len(pages)):
                    if str(pageid + offset) in page_token_slots[pageid]:
                        combo += 1
                if combo > maxcombo:
                    maxcombo = combo
                    pagination_offset = offset
            # if maxcombo < len(pages) // 2:
            #     pagination_offset = None

            def is_freq(freq: int): return len(pages) >= 3 and freq >= len(
                pages) - 1 or len(pages) >= 5 and freq > len(pages) * 2 / 3

            for pageid, page in enumerate(pages):
                header, body = page[:HEADER_SCAN_LIMIT], page[HEADER_SCAN_LIMIT:]
                newlines = []
                done = False  # 我们只删连续一段开头的，这样写来防止删掉类似the la de这些常见单词

                for line in header.splitlines():
                    # if 'A/CN.9/WG.VI/WP.22/Add.1' in line and lang == 'zh':
                    #     print('break')
                    # else:
                    #     continue
                    # # 行近似匹配
                    line = line.strip()
                    if not line or done:  # 空行不管，先照旧插入newlines
                        # if line: # 这行用来管空行，即丢掉空行
                        newlines.append(line)
                        continue

                    line_digest = line.replace(' ', '')

                    # substr_score = Counter() # LCS得分，用于处理最长公共子序列，情况不多且过于复杂，先不用，这里留个想法
                    line_freq = 0
                    for line_str, ctr in line_spot.items():
                        matcher = SequenceMatcher(
                            None, line_digest, line_str, autojunk=False)
                        # 上界剪枝
                        if matcher.real_quick_ratio() > MATCHER_RATIO and matcher.quick_ratio() > MATCHER_RATIO and matcher.ratio() > MATCHER_RATIO:
                            line_freq += ctr
                    if is_freq(line_freq):
                        make_filter_log(line, record, lang, pageid,
                                        f'line_freq: {line_freq}, pages: {len(pages)}')
                        continue
                    # 按token过滤
                    new_tokens = []
                    for token in line.split(' '):
                        # token.isdigit() 不可靠
                        if not token:
                            continue
                        if not done:
                            # 特判页码
                            if pagination_offset is not None and re.match(DIGITS_PATTERN, token) and int(token) == pageid + pagination_offset:
                                make_filter_log(token, record, lang,
                                                pageid, f'likely page number')
                                continue
                            overall_token_freq = overall_token_spots[token]
                            if overall_token_freq > overall_pages_num // 2:
                                make_filter_log(
                                    token, record, lang, pageid, f'overall_tk_freq: {overall_token_freq}, all_pages: {overall_pages_num}')
                                continue
                            # for token_str, ctr in token_spot.items():
                                # if token_str == token:
                                # token_freq += ctr
                            token_freq = token_spot[token]
                            if is_freq(token_freq) and not token_freq > len(pages):
                                make_filter_log(
                                    token, record, lang, pageid, f'tk_freq: {token_freq}, pages: {len(pages)}')
                                continue

                        new_tokens.append(token)
                        done = True

                    newlines.append(' '.join(new_tokens))

                # 去页脚逻辑
                annotation_index = body.find('__________')
                if annotation_index != -1:
                    make_filter_log(body[annotation_index:],
                                    record, lang, pageid, f"annotation block")
                    body = body[:annotation_index]

                pages[pageid] = ('\n'.join(newlines) + body).strip()
            row[lang] = PAGINATION_TOKEN.join(pages)  # 放回row，统一格式，之后用别的函数处理合页与成段

    def remove_duplicate_breakline(pages: list[str]):
        flatten = list(line.strip() for line in itertools.chain(*[page.splitlines() for page in pages]))
        outputs = []
        for i in flatten:
            if not i:
                continue
            outputs.append(i)
        return '\n'.join(outputs)

    def chk_en_rate(row):
        inputs = row['en']
        en_rate = len(re.findall(r'[a-zA-Z]', inputs)) / len(inputs) if len(inputs) else 0
        if en_rate < 0.2:
            return False
        return True

    def dump_row(row):
        """调试用，输出中间结果到文件，row是map的DatasetDict"""
        for lang in LANGS:
            with open(my_path(PREPROCESS_DIR, f'dbg_{lang}.txt'), 'a', encoding='utf-8') as f:
                f.write(make_banner(row['record']) + row[lang])


    def preprocess(row):
        drop_pagination_header_and_footer(row)
        for lang in LANGS:
            row[lang] = remove_duplicate_breakline(row[lang].replace('\ufffe', '-').split(PAGINATION_TOKEN))
        return row

    use_proxy()
    dataset = datasets.load_dataset("ranWang/un_pdf_text_data_test", split='randomTest10000')
    dataset = dataset.filter(chk_en_rate).map(preprocess, num_proc=8)
    dataset.map(dump_row)
    dataset.save_to_disk(my_path())
    # dataset = datasets.load_from_disk(my_path())
    print(len(dataset))
    dataset.push_to_hub('bot-yaya/un_pdf_random10032_preprocessed2', token=read_secret('HF_TOKEN'))



if __name__ == "__main__":

    if os.path.exists(my_path('chatgptexception.jsonl')):
        with open(my_path('chatgptexception.jsonl'), 'r', encoding='utf-8') as f:
            for line in f.read().splitlines():
                json_log = json.loads(line)
                if json_log.get('exc') == 'runtime_error':
                    exception_files.add(json_log['rec'])

    if exception_files:
        print('some files cannot be process properly in previous run:')
        print(*exception_files)
        print('these files will be ignored.')

    command_map = OrderedDict((
        ('1', ask_gpt),
        ('2', post_process),
        ('3', convert_output_text_to_idx),
        ('4', push_idx_to_hf),
        ('5', download_and_visualize),
        ('6', translate_and_align),
        ('7', preprocess_and_upload_dataset),
    ))
    while (cmd := input('''
    1: ask_gpt
    2: post_process
    3: convert_output_text_to_idx
    4: push_idx_to_hf
    5: download_and_visualize
    6: translate_and_align
    7: preprocess_and_upload_dataset
>>>''')
    ) not in command_map:
        print('invalid input')
    begintime = datetime.datetime.now()
    command_map[cmd]()
    print('Time elapsed:', datetime.datetime.now() - begintime)