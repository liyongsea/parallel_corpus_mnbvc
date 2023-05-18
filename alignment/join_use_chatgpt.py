import datetime
import os
import time
import json

from pathlib import Path
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict
##


BATCH_STEP = 4096 # 一次性发给chatgpt多少字符，越多越好，但是尽量不要让它截断
WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可
RETRY_TIME = 5
SLEEP_TIME = 10



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
some breakline may split the text as meaningful paragraghs but others could separate them unexpectly,
in this case, you should join adjacent lines if they can form a meaningful paragraph and replace the breakline symbols as spaces.
try to filter noises and keep as many meaningful info as you can, 
leave the indexing information and some lines that can not form a paragragh as it is, 
do not add more word to the input text, 
do not answer any other word except the task output,
format the resulting paragraphs as python list, and make sure it can use by python's eval with no error.
Here is the input text:

'''
    production_prompt_engineering = '''I need your help to solve a breakline elimination problem,
given some text exported from PDF, 
some breakline may split the text as meaningful paragraghs but others could separate them unexpectly,
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
    # inputs = debug_prompt_engineering + prompt
    inputs = production_prompt_engineering + prompt
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

def process_one_file_use_chatgpt(row: DatasetDict):
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


if __name__ == "__main__":
    dataset = load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED')
    # cmd = input('use proxy? (default settings is socks5://localhost:7890) please answer(y/N):')
    # if cmd.lower() == 'y':
    # use_proxy()
    
    dataset.map(process_one_file_use_chatgpt)
