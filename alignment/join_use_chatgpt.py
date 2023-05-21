import datetime
import os
import time
import json

from pathlib import Path
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict

from loguru import logger
logger.add(open('log.txt', 'a'))
##


BATCH_STEP = 2048 # 一次性发给chatgpt多少字符，越多越好，但是尽量不要让它截断
MAX_TOKEN_COUNT = 1400
WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可
RETRY_TIME = 5
SLEEP_TIME = 20



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

def chat(prompt: str):
    """主体，入参prompt是向chatgpt问的内容，debug_prompt是让它打印内容，production只打下标"""
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

import tiktoken
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
processed_counter = 0

def process_one_file_use_chatgpt2(row: DatasetDict):
    global processed_counter
    processed_counter += 1
    if processed_counter > 100:
        return

    inputs = row['en']
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
        for line in inputs.splitlines():
            tmp = (buf + '\n' if len(buf)>0 else '') + line
            tks = enc.encode(tmp) # 如果能保证每行加起来等于总的，那么可以改写成O(n)的
            if len(tks) >= MAX_TOKEN_COUNT:
                yield buf
                l0 = last[0]
                tmp = (l0 + '\n' if len(l0)>0 else '') + line
            buf = tmp
        if buf:
            yield buf

    for batch_id, batch in enumerate(gen_batch()):
        if batch_id in visited:
            outputlines = visited[batch_id]['output'].splitlines()
            outputlines = list(filter(lambda x: len(x.strip()), outputlines))
            if len(outputlines) > 1:
                last[0] = outputlines[-1]
            else:
                last[0] = ''
            continue

        # done = False
        for retrytime in range(RETRY_TIME):
            try:
                outputs = chat(batch)
                with open(output_file_name, 'a', encoding='utf-8') as f:
                    json.dump({'batch': batch_id, 'step': MAX_TOKEN_COUNT, 'input': batch, 'output': outputs}, f)
                    f.write('\n')
                outputlines = list(filter(lambda x: len(x.strip()), outputs.splitlines()))
                if len(outputlines) > 1:
                    last[0] = outputlines[-1]
                else:
                    last[0] = ''
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

def process_one_file_use_chatgpt(row: DatasetDict):
    global processed_counter
    processed_counter += 1
    if processed_counter > 100:
        return

    inputs = row['en']
    rec = row['record']
    visited = set()

    Path(my_path('done')).mkdir(exist_ok=True)
    output_file_name = my_path(f'done/gpt_en_{rec}.jsonl')

    if os.path.exists(output_file_name):
        with open(output_file_name, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        for json_line in saved_content.splitlines():
            json_line = json_line.strip()
            if json_line:
                infos = json.loads(json_line)
                if infos['step'] == BATCH_STEP:
                    visited.add(infos['batch'])


    for i in range(0, len(inputs), BATCH_STEP):
        batch_id =  i // BATCH_STEP
        if batch_id in visited:
            continue

        input_batch = inputs[i : i + 2 * BATCH_STEP]
        # done = False
        for retrytime in range(RETRY_TIME):
            try:
                outputs = chat(input_batch)
                with open(output_file_name, 'a', encoding='utf-8') as f:
                    json.dump({'batch': batch_id, 'step': BATCH_STEP, 'input': input_batch, 'output': outputs}, f)
                    f.write('\n')
                break
            except ContextLengthExceeded as e:
                with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                    json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': BATCH_STEP, 'input': input_batch, 'exc': 'context_length_exceeded', 'msg': e.args}, f)
                    f.write('\n')
                break
            except UnknownException as e:
                with open(my_path('chatgptexception.jsonl'), 'a', encoding='utf-8') as f: # 日志
                    json.dump({'time': str(datetime.datetime.now()),'rec': rec, 'batch': batch_id, 'step': BATCH_STEP, 'input': input_batch, 'exc': 'unknown', 'msg': e.args}, f)
                    f.write('\n')
                break
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

def post_process_index():
    """后处理，prompt用仅输出下标的方法"""
    Path(my_path('post')).mkdir(exist_ok=True)
    for filename in os.listdir(my_path('done')):
        if filename.endswith('jsonl') and filename.startswith('gpt_en_'):
            with open(my_path('done', filename), 'r', encoding='utf-8') as f:
                content = f.read()
            for line in content.splitlines():
                j = json.loads(line.strip())
                if j['step'] == BATCH_STEP:
                    breaklines = [] # 回车符的下标
                    input_text = j['input']
                    for p, i in enumerate(input_text):
                        if i == '\n':
                            breaklines.append(p)
                    breaklines_set1 = set(breaklines) # 要留的下标，第一种选法：字符位移
                    output_index = j['output']
                    
                    breakline_num_selection = [] # 第二种选法：第几个回车
                    for ind in read_int(output_index):
                        breaklines_set1.discard(ind - breaklines[0]) # 字符位移
                        if ind < len(breaklines):
                            breakline_num_selection.append(ind)
                    breaklines_set1 = set(breaklines) - breaklines_set1 # 求差，得到要删的下标
                    breaklines_set2 = set(breaklines[i] for i in breakline_num_selection) # 要删的下标

                    real_output_buffer_1 = []
                    real_output_buffer_2 = []
                    for p, i in enumerate(input_text):
                        if i == '\n':
                            real_output_buffer_1.append(' ' if p in breaklines_set1 else '\n')
                            real_output_buffer_2.append(' ' if p in breaklines_set2 else '\n')
                        else:
                            real_output_buffer_1.append(i)
                            real_output_buffer_2.append(i)
                    real_output1 = ''.join(real_output_buffer_1)
                    real_output2 = ''.join(real_output_buffer_2)
                    print(real_output1)
                    print('==========')
                    print(real_output2)
                    print('#####')
                    print(breaklines_set1)
                    print('=====')
                    print(breaklines_set2)
                    cmd = '2'
                    # while (cmd := input('1 or 2?>>>')) not in ('1', '2'):
                        # print('invalid input')
                    with open(my_path('post', filename), 'a', encoding='utf-8') as f:
                        to_be_dumped = {'batch': j['batch'], 'step': BATCH_STEP}

                        if cmd == '1':
                            to_be_dumped['real_output'] = real_output1
                            to_be_dumped['deleted'] = list(breaklines_set1)
                        else:
                            to_be_dumped['real_output'] = real_output2
                            to_be_dumped['deleted'] = list(breaklines_set2)

                        json.dump(to_be_dumped, f)
                        f.write('\n')


def post_process_list():
    """后处理，prompt用输出py样式列表的方法"""
    # import difflib
    # import string2string
    import pylcs
    Path(my_path('post')).mkdir(exist_ok=True)
    for filename in os.listdir(my_path('done')):
        if filename.endswith('jsonl') and filename.startswith('gpt_en_'):
            with open(my_path('done', filename), 'r', encoding='utf-8') as f:
                content = f.read()
            source_input_buffer = []
            outputs = []
            content = content.splitlines()

            unexpected_output = False
            for lineid, line in enumerate(content):
                j = json.loads(line.strip())
                if j['step'] == BATCH_STEP:
                    # breaklines = [] # 回车符的下标
                    input_text = j['input']
                    source_input_buffer.append(input_text[:BATCH_STEP])
                    try:
                        real_output = eval(j['output'])
                    except SyntaxError as e:
                        logger.error('file: {}, err: {}, output: {}', filename, e, j['output'])
                        unexpected_output = True
                        break
                        # user = input('>>>')
                        # real_output = eval(j['output'] + user)

                    # if lineid != 0:
                    #     real_output = real_output[1:]
                    # if lineid != len(content) -1:
                    #     real_output = real_output[:-1]
                    outputs.append(real_output)
                    print(input_text)
                    print('==========')
                    print(*real_output, sep='\n')
                    print('#####')
            if unexpected_output:
                continue
            source_input = ''.join(source_input_buffer).replace('\ufffe', '\n').splitlines()
            source_input_belongs = [{} for _ in source_input]
            char_offset = 0
            for source_input_line_index, source_input_line in enumerate(source_input):
                # done = False
                char_offset += len(source_input_line) + 1 # 算上回车符
                # idx1 = char_offset // BATCH_STEP
                # idx2 = 
                for output_batch_index, output_batch in enumerate(outputs):
                    lborder = output_batch_index * BATCH_STEP
                    rborder = lborder + 2 * BATCH_STEP
                    center = lborder + BATCH_STEP
                    if char_offset in range(lborder, rborder):
                        for output_line_index, output_line in enumerate(output_batch):
                            # if source_input_line in output_line:
                            if source_input_line in output_line :#or pylcs.lcs_sequence_length(source_input_line, output_line) / len(source_input_line) >= 0.93:
                                source_input_belongs[source_input_line_index].setdefault(output_batch_index, {}).update({output_line_index: char_offset - center})
            print(source_input_belongs)

            processed_input_buffer = []
            processed_input_index_buffer = []
            b2 = []
            for source_input_line_index, source_input_line in enumerate(source_input):
                belongs = source_input_belongs[source_input_line_index]
                if not belongs: # 没有所属，可能是噪声被chatgpt滤掉了
                    print('[filtered]', source_input_line)
                    continue
                if not processed_input_index_buffer: # 在后面的操作中保证processed_input_buffer非空
                    # processed_input_buffer.append(source_input_line)
                    processed_input_index_buffer.append(source_input_line_index)
                    b2.append(source_input_line_index)
                    continue

                prevbelongs = source_input_belongs[processed_input_index_buffer[-1]]
                # can_join = True
                can_join = 0
                # for output_batch_id, output_line_id in belongs: # 保守做法：只要有断行，就断行
                for output_batch_id, v in belongs.items():
                    for output_line_id, d in v.items():
                        same_output_batch = prevbelongs.get(output_batch_id, {})
                        # if (output_batch_id, output_line_id - 1) in prevbelongs:
                        if output_line_id - 1 in same_output_batch and output_line_id not in same_output_batch:
                        # if output_line_id in same_output_batch:
                            # can_join = False
                            can_join -= 1 /(1e-5 + abs( same_output_batch[output_line_id - 1])) # 负，不能接
                            # can_join = True
                            # break
                        if output_line_id - 1 not in same_output_batch and output_line_id in same_output_batch:
                            can_join += 1 /(1e-5 + abs( same_output_batch[output_line_id])) # 正，能接

                    # if not can_join:
                        # break

                if can_join > 0:
                    # processed_input_buffer[-1] += ' ' + source_input_line
                    processed_input_index_buffer[-1] = source_input_line_index
                    
                else:
                    # processed_input_buffer.append(source_input_line)
                    processed_input_index_buffer.append(source_input_line_index)
                    b2.append(source_input_line_index)

            print(processed_input_index_buffer)
            print(b2)

            idx = 0
            for source_input_line_index, source_input_line in enumerate(source_input):
                if not processed_input_buffer:
                    processed_input_buffer.append(source_input_line)
                    continue
                while idx < len(b2) and b2[idx] < source_input_line_index:
                    idx += 1
                if idx < len(b2) and b2[idx] == source_input_line_index:
                    processed_input_buffer.append(source_input_line)
                    idx += 1
                else:
                    processed_input_buffer[-1] += ' ' + source_input_line
                    

            dumped = '\n'.join(processed_input_buffer)
            
            with open(my_path('post', filename), 'w', encoding='utf-8') as f:
                f.write(dumped)
                print('\n====\n'.join(processed_input_buffer))

            input('continue>>>')


                    #     if cmd == '1':
                    #         to_be_dumped['real_output'] = real_output1
                    #         to_be_dumped['deleted'] = list(breaklines_set1)
                    #     else:
                    #         to_be_dumped['real_output'] = real_output
                    #         to_be_dumped['deleted'] = list(breaklines_set2)

                    #     json.dump(to_be_dumped, f)
                    #     f.write('\n')
if __name__ == "__main__":
    while (cmd := input('1: chatgpt; 2: post process >>>')) not in ('1', '2'):
        print('invalid input')
    if cmd == '1':
    # cmd = input('use proxy? (default settings is socks5://localhost:7890) please answer(y/N):')
    # if cmd.lower() == 'y':
    # use_proxy()
        dataset = load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED')
        dataset.map(process_one_file_use_chatgpt2)
    else:
        post_process_list()
    
