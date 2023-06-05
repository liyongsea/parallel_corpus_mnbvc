import datetime
import os
import time
import json
import traceback
import re
from collections import OrderedDict
from typing import Tuple
from pathlib import Path
from itertools import chain
import requests

import pylcs
import tiktoken
import datasets

from datasets.dataset_dict import DatasetDict

MAX_TOKEN_COUNT = 1400
WORKDIR_ABSOLUTE = r'.' # 工作区绝对路径，为方便调试使用，实际使用换成.即可
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
    dataset = dataset.select(range(500)).filter(lambda x: x['record'] not in exception_files)
    return dataset

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

def lcs_sequence_alignment(ibatch: list[str] | str, obatch: list[str] | str) -> Tuple[dict[int, set[int]], list[float], list[float]]:
    """将ibatch每行的单词用最长公共子序列对齐到obatch每行的单词中。
    
    Args:
        ibatch(str): 输入的一段话
        obatch(str): chatgpt给对齐好的一段话
    
    Returns:
        mapping(dict[int, set[int]]): 输出行号对应输入的行号
        irate(list[float]): 输入每行的匹配率（匹配的单词总长度/本行总单词总长度）
        orate(list[float]): 输出每行的匹配率
    """
    if isinstance(ibatch, str):
        ibatch = ibatch.splitlines()
    if isinstance(obatch, str):
        obatch = obatch.splitlines()
    offset = 19968
    dic = {}
    
    ibuf = [] # 输入token
    ilen = []

    obuf = []
    olen = []
    # 手写的token转换，优化lcs的效率，这里换成中文字形式编码这些token，只判等
    offset = 19968 # 中文unicode起点
    dic = {}
    for ilineid, iline in enumerate(ibatch):
        sp = iline.split()
        ilen.append(sum(map(len, sp)))
        for i in sp:
            ibuf.append((
                chr(offset + dic.setdefault(i, len(dic))),
                len(i),
                ilineid,
                ))
    
    for olineid, oline in enumerate(obatch):
        sp = oline.split()
        olen.append(sum(map(len, sp)))
        for i in oline.split():
            if i in dic: # 为子序列写的优化
                obuf.append((
                    chr(offset + dic[i]),
                    len(i),
                    olineid,
                    ))
    

    irate = [0 for _ in ilen]
    orate = [0 for _ in olen]

    n1 = ''.join(map(lambda x: x[0], ibuf))
    n2 = ''.join(map(lambda x: x[0], obuf))
    print(f'n1:{len(n1)}, n2:{len(n2)}')
    idxs = pylcs.lcs_sequence_idx(n1, n2)
    mapping = {}
    for iidx, oidx in enumerate(idxs):
        if oidx != -1:
            _, iklen, ikgroup = ibuf[iidx]
            _, oklen, okgroup = obuf[oidx]
            mapping.setdefault(okgroup, set()).add(ikgroup)
            irate[ikgroup] += iklen
            orate[okgroup] += oklen
    
    for p, i in enumerate(irate):
        irate[p] = i / ilen[p]
    for p, i in enumerate(orate):
        orate[p] = i / olen[p]

    # 额外处理：匹配率低于60%的olineid不要
    print(mapping)
    print('orate', orate)
    for p, i in enumerate(orate):
        if i < 0.6:
            if p in mapping:
                mapping.pop(p)

    return mapping, irate, orate

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
        jmap = {}
        for i in os.listdir(dir):
            with open(cat(dir, i, 'output.txt'), 'r', encoding='utf-8') as f:
                outputmap[i] = f.read()
            with open(cat(dir, i, 'is_hard_line_break.json'), 'r', encoding='utf-8') as f:
                jmap[i] = json.load(f)
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
    
    upload_pending = convert_idx()
    hf_tk = read_secret('HF_TOKEN')
    print('dataset length:', len(upload_pending))
    upload_pending = datasets.Dataset.from_list(upload_pending)
    upload_pending.push_to_hub(repo_id='gpt_joined_en_paragraph', split='train', token=hf_tk)

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
    ))
    while (cmd := input('''
    1: ask_gpt
    2: post_process
    3: convert_output_text_to_idx
    4: push_idx_to_hf
    5: download_and_visualize
>>>''')
    ) not in command_map:
        print('invalid input')
    command_map[cmd]()