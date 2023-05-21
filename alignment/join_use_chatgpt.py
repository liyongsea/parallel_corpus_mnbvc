import datetime
from itertools import chain
import os
import time
import json

import pylcs

from pathlib import Path
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict


BATCH_STEP = 2048 # 一次性发给chatgpt多少字符，越多越好，但是尽量不要让它截断
MAX_TOKEN_COUNT = 1400
WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可
RETRY_TIME = 5
SLEEP_TIME = 0

OPENAI_TOKENS = [
]

def cat(*args): 
    return '/'.join(args)

def my_path(*args):
    """相对路径"""
    return cat(WORKDIR_ABSOLUTE, *args)

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket

def read_secret(relative_path, hint=''):
    """隐私文件缓存，之后用环境变量替换"""
    relative_path += '.secret'
    abs_path = my_path(relative_path)
    if not os.path.exists(abs_path):
        cmd = input(f'[{hint} {relative_path}] The secret file is required, your input will be saved in {abs_path}. \nNow please input:')
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(cmd)
        print(f'Your input is saved to {abs_path}, modify it if it is incorrect.')

    try:
        with open(abs_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(e)
        print(f'please put your token to {relative_path} in the root dir specify in WORKDIR_ABSOLUTE')
        print('current WORKDIR_ABSOLUTE:', WORKDIR_ABSOLUTE)
        raise

class ContextLengthExceeded(Exception): pass
class UnknownException(Exception): pass

debug_prompt_engineering = '''I need your help to solve a breakline elimination problem,
given some text exported from PDF, 
some breaklines may split the text as meaningful paragraphs but others could separate them unexpectly,
in this case, you should join adjacent lines if they can form a meaningful paragraph and replace the breakline symbols as spaces,
leave the indexing information and some lines that can not form a paragragh as it is.
Leave the breaklines that can split the text as meaningful paragraphs.
The input may contains a whole line of pagination infos and indexing infos,
you should not join them to the adjacent paragraphs.
You should only determine the breaklines should be keep or replaced,
and leave other text as it is.
Please do not add more word to the input text, 
do not answer any other word except the task output,
do not add any characters to the end of the task output.
Here is the input text:

'''
production_prompt_engineering = '''I need your help to solve a breakline elimination problem,
given some text exported from PDF, 
some breakline may split the text as meaningful paragraphs but others could separate them unexpectly,
in this case, you should join adjacent lines if they can form a meaningful paragraph and replace the breakline symbols as spaces.
leave the indexing information and some lines that can not form a paragragh as it is, 
do not answer any other word except the task output,
do not echo the processed text, 
just tell me the indexes of the breakline symbol you replaced with spaces, 
assume the first breakline symbol has the index 0,
and please separate the indices by comma.
Do not answer any characters except the comma separated index numbers.
Here is the input text:
'''

def chat(prompt: str):
    """主体，入参prompt是向chatgpt问的内容，debug_prompt是让它打印内容，production只打下标"""

    import requests
    k = read_secret('openai_token')
    inputs = debug_prompt_engineering + prompt
    # inputs = production_prompt_engineering + prompt
    tokens = len(inputs.split())
    print('tokens len:', tokens)
    r = requests.post(
        # "https://api.openai.com/v1/chat/completions",
        "https://openai-proxy-syhien.pages.dev/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + k
            },
            json={
                # "model": "text-davinci-003",
                "model": "gpt-3.5-turbo",
                # "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": inputs},
                    {"role": "assistant", "content": 'Output:\n'}
                    ],
                # "temperature": 0, 
                # "max_tokens": 4000 - int(tokens * 1.3)
            }
        )
    j = r.json()
    print(j)
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

async def aiochat(prompt: str):
    """异步版本的chat"""
    import aiohttp


def clearup_output(raw_output_from_chatgpt: str) -> list[str]:
    return list(filter(lambda x: len(x.strip()), raw_output_from_chatgpt.splitlines()))

def likelyin(s1, s2):
    """chatgpt并不是非常听话，会自己去噪或者补全，所以需要一些模糊处理来匹配相似字符串。
    本函数判断s2是否疑似包含s1
    """
    if s1 in s2:
        return True
    if len(s1) < 20: # 短的直接用子串（序列太危险）
        if pylcs.lcs_string_length(s1, s2) / len(s1) > 0.92:
            return True
        return False

    offset = 19968 # 长的直接跑太慢，这里拆单词提速
    dic = {}
    n1 = []
    n1len = []
    n2 = []
    for i in s1.split():
        n1.append(chr(offset+dic.setdefault(i, len(dic))))
        n1len.append(len(i))
    for i in s2.split():
        if i in dic: # 为子序列写的优化
            n2.append(chr(offset+dic.setdefault(i, len(dic))))
    n1 = ''.join(n1)
    n2 = ''.join(n2)
    idxs = pylcs.lcs_string_idx(n1, n2)
    tot = 0
    for token, score in zip(idxs, n1len):
        if token != -1:
            tot += score
    if tot / sum(n1len) > 0.92:
        return True
    return False

import tiktoken
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
processed_counter = 0

def process_one_file_use_chatgpt2(row: DatasetDict):
    global processed_counter
    processed_counter += 1
    if processed_counter > 10:
        return

    inputs = row['en'].replace('\ufffe', '-')
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

    last: list[str] = ['']
    def gen_batch():
        """last[0]用于传递上次没分段出来的文本"""
        buf = ''
        for lineid, line in enumerate(inputs.splitlines()):
            tmp = (buf + '\n' if len(buf)>0 else '') + line
            tks = enc.encode(tmp) # 如果能保证每行加起来等于总的，那么可以改写成O(n)的
            if len(tks) >= MAX_TOKEN_COUNT:
                yield buf, lineid
                l0 = last[0]
                tmp = (l0 + '\n' if len(l0)>0 else '') + line
            buf = tmp
        if buf:
            yield buf, lineid



    def construct_backline(output_backline: str, input_batch: list[str]) -> str:
        back_buf = []
        for backline in reversed(input_batch.splitlines()):
            if not likelyin(backline, output_backline):
                break
            back_buf.append(backline)
        return '\n'.join(reversed(back_buf))

    prvlineid = 0
    for batch_id, (batch, lineid) in enumerate(gen_batch()):
        if batch_id in visited:
            outputs = visited[batch_id]['output']
            outputlines = clearup_output(outputs)
            if len(outputlines) > 1:
                last[0] = construct_backline(outputlines[-1], batch)
            else:
                last[0] = ''
            # lineid = visited[batch_id]['r']
            prvlineid = lineid - last[0].count('\n') + 1

            continue

        # done = False
        for retrytime in range(RETRY_TIME):
            try:
                outputs = chat(batch)
                with open(output_file_name, 'a', encoding='utf-8') as f:
                    json.dump({'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'l': prvlineid, 'r': lineid, 'input': batch, 'output': outputs}, f)
                    f.write('\n')
                outputlines = clearup_output(outputs)
                if len(outputlines) > 1:
                    last[0] = construct_backline(outputlines[-1], batch)
                else:
                    last[0] = ''
                prvlineid = lineid - last[0].count('\n') + 1
                break
            except ContextLengthExceeded as e:
                with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                    json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'context_length_exceeded', 'msg': e.args}, f)
                    f.write('\n')
                return # 整个不能要了
                # break
            except UnknownException as e:
                with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                    json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'exc': 'unknown', 'msg': e.args}, f)
                    f.write('\n')
                return # 整个不能要了
            except KeyboardInterrupt:
                print('interrupted by keyboard.')
                exit(0)
            except Exception as e:
                print('retry:', retrytime, e)
                if retrytime == RETRY_TIME - 1:
                    raise
                print(f'sleep for {SLEEP_TIME}s')
                time.sleep(SLEEP_TIME)
        # Path()
            # f.write(make_banner(input_batch+'\nreq: '+str(i // BATCH_STEP)+'\nBS: '+str(BATCH_STEP))+ outputs + PAGINATION_TOKEN)

        print(f'sleep for {SLEEP_TIME}s')
        time.sleep(SLEEP_TIME)


def read_int(s: str) -> int:
    """把s中所有数字拿出来"""
    x = 0
    is_read = 0
    for c in s:
        if c.isdigit():
            x = x * 10 + int(c)
            is_read = 1
        else:
            if is_read:
                yield x
            is_read = 0
            x = 0
    if is_read:
        yield x

def longest_adjacent_subsequence(li: list[int]):
    """求最长连续+1子序列，返回区间的左下标和右下标"""
    assert len(li) > 0
    l = 0
    r = 0
    ml = 0
    mr = 0
    msiz = 0
    for i, n in enumerate(li):
        if n == li[r] + 1:
            r = i
        else:
            siz = r-l+1
            if siz > msiz:
                ml = l
                mr = r
                msiz = siz
            l = i
            r = i

    siz = r-l+1
    if siz > msiz:
        ml = l
        mr = r
        msiz = siz
    return ml, mr

def post_process(row: DatasetDict):
    """后处理，prompt用输出py样式列表的方法"""
    # from string2string.alignment import NeedlemanWunsch

        # nw = NeedlemanWunsch()
        # a1, a2 = nw.get_alignment(s1.split(), s2.split())
        # aid, a1, a2 = nw.get_alignment_strings_and_indices(a1, a2)
        # if sum(map(lambda x: len(x.strip()), a1)) / len(s1) > 0.88:
            # return True

    from loguru import logger
    logger.add(open('log.txt', 'a'))
    inputs = row['en'].replace('\ufffe', '-')
    ilines = inputs.splitlines() # input lines
    rec = row['record']
    output_file_name = my_path(f'done/gpt_en_{rec}.jsonl')
    if not os.path.exists(output_file_name):
        return
    
    obatches = [] # output batches
    ibatches = []
    ibatchesl = []
    ibatchesr = []

    with open(output_file_name, 'r', encoding='utf-8') as f:
        flines = f.read().splitlines()
        for p, i in enumerate(flines):
            j = json.loads(i) # batch(int):批次号 step(int):步长，即MAX_TOKEN_COUNT input(str):输入文本 output(str):输出文本 l(int):左边界行号，上次处理的 r(int):右边界行号
            obatch = list(filter(lambda x: len(x.strip()), j['output'].replace('\ufffe', '-').splitlines()))
            if p != len(flines) - 1:
                obatch.pop()
            obatches.append(obatch)
            ibatches.append(list(filter(lambda x: len(x.strip()), j['input'].replace('\ufffe', '-').splitlines())))
            ibatchesl.append(j)

    br = set()
    for ibatch, obatch in zip(ibatches, obatches):
        ibatchlines = set(ibatch)
        for oline in obatch:
            if 'II. Activities of the Office of the United Nations High Commissioner' in oline:
                print('breakline1')
            br_id = [] # breakline id to be eliminated
            for prevlineid, nextline in enumerate(ilines[1:]):
                prevline = ilines[prevlineid]
                if nextline not in ibatchlines or prevline not in ibatchlines:
                    # back_few_lines = ibatch[-5:]
                    # for l in back_few_lines
                    continue
                if 'II. Activities of the Office of the United Nations High Commissioner' in nextline:
                    print('breakline2')
                if likelyin(prevline, oline) and likelyin(nextline, oline):
                    br_id.append(prevlineid)

            # 对br_id求最长连续子序列
            # if br_id:
            #     l, r = longest_adjacent_subsequence(br_id)
            #     br = br.union(br_id[l: r+1])
            br = br.union(br_id)
            
    concated = []
    for lineid, iline in enumerate(ilines):
        if lineid - 1 in br:
            concated[-1] += ' ' + iline
        else:
            concated.append(iline)
    Path(my_path('post')).mkdir(exist_ok=True)
    print(len(concated))

    with open(my_path('post', f'{rec}.src'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(chain(*obatches)))
    with open(my_path('post', f'{rec}.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(concated))
    with open(my_path('post', f'{rec}.idx'), 'w', encoding='utf-8') as f:
        f.write(','.join(map(str, list(sorted(br)))))



if __name__ == "__main__":
    while (cmd := input('1: chatgpt; 2: post process >>>')) not in ('1', '2'):
        print('invalid input')
    dataset = load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED')
    if cmd == '1':
    # cmd = input('use proxy? (default settings is socks5://localhost:7890) please answer(y/N):')
    # if cmd.lower() == 'y':
    # use_proxy()
        dataset.map(process_one_file_use_chatgpt2)
    else:
        dataset.map(post_process)
        
    
