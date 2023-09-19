from queue import Empty
import re
import os
import win32com.client as win32
from win32com.client import constants
from pathlib import Path
import multiprocessing as mp
import psutil
import pickle
import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.requests import Request
from fastapi import File
from typing import Annotated
import asyncio
import uvicorn

BASE_DIR = r'D:\wwd'
ERR_LOG_DIR = BASE_DIR + r'\err'
SOURCE_DIR = BASE_DIR + r'\src'
SAVED_DIR = BASE_DIR + r'\out'
# PENDING_DIR = BASE_DIR + r'\out'

TASK_CACHE_DIR = BASE_DIR + r'\oswalkcache.pkl'
GROUP_CACHE_DIR = BASE_DIR + r'\dirmappingcache.pkl'

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

app = FastAPI()

pending = set()
todo = set()

with open(TASK_CACHE_DIR, 'rb') as f:
    li = pickle.load(f)
for subdir, filenames in li:
    for dfn in filenames:
        absfn = os.path.join(SOURCE_DIR, subdir, dfn)
        if not os.path.exists(saved_path(absfn)) and not os.path.exists(err_path(absfn)):
            todo.add(absfn)
print('todo:', len(todo), len(pending))

async def recover(task):
    await asyncio.sleep(30)
    if task in pending:
        pending.remove(task)
        todo.add(task)

@app.post('/upl')
async def task_submit(task: str, fil: Annotated[bytes, File()]):
    pending.remove(task)
    if os.path.exists(saved_path(task)) or os.path.exists(err_path(task)):
        return False
    with open(saved_path(task), 'wb') as f:
        f.write(fil)
    return True

@app.post('/uplerr')
async def task_error(task: str):
    pending.remove(task)
    if os.path.exists(saved_path(task)) or os.path.exists(err_path(task)):
        return False
    print('report err file:', task)
    with open(err_path(task), 'w') as f:
        pass
    return True

@app.get('/')
async def task_getter():
    cur = todo.pop()
    while os.path.exists(saved_path(cur)) or os.path.exists(err_path(cur)):
        cur = todo.pop() # 没有任务抛长度异常

    pending.add(cur)
    asyncio.create_task(recover(cur))
    # with open(absfn, 'rb') as f:
    #     bts = f.read()
    return FileResponse(absfn)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=29999)