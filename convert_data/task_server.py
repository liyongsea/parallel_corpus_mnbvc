import re
import os
import pickle
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.requests import Request
from fastapi import File
from typing import Annotated
from fastapi.middleware.gzip import GZipMiddleware
import asyncio
import uvicorn
import base64


BASE_DIR = r'E:\motrixDL\baiduyun\MNBVC'
ERR_LOG_DIR = BASE_DIR + r'\err'
SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'
SAVED_DIR = BASE_DIR + r'\docxoutput'
# PENDING_DIR = BASE_DIR + r'\out'

TASK_CACHE_DIR = BASE_DIR + r'\oswalkcache.pkl'
GROUP_CACHE_DIR = BASE_DIR + r'\dirmappingcache.pkl'

def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.log', file_abs.split('\\')[-1]))
def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))

app = FastAPI(redoc_url=None, docs_url=None, swagger_ui_init_oauth=None, openapi_url=None)
app.add_middleware(GZipMiddleware)

pending = set()
todo = set()

with open(TASK_CACHE_DIR, 'rb') as f:
    li = pickle.load(f)
for subdir, filenames in li:
    for dfn in filenames:
        absfn = os.path.join(SOURCE_DIR, subdir, dfn)
        if not os.path.exists(saved_path(absfn)) : # and not os.path.exists(err_path(absfn))
            todo.add(os.path.join(subdir, dfn))
print('todo:', len(todo), len(pending))

async def recover(task):
    await asyncio.sleep(300)
    if task in pending:
        pending.remove(task)
        todo.add(task)

@app.post('/upl')
async def task_submit(r: Request, fil: Annotated[bytes, File()]):
    task = base64.b64decode(r.headers['taskid']).decode()
    if task not in pending:
        return False
    pending.remove(task)
    task = os.path.join(SOURCE_DIR, task)
    if os.path.exists(saved_path(task)) or os.path.exists(err_path(task)):
        return False
    with open(saved_path(task), 'wb') as f:
        f.write(fil)
    print(len(todo), len(pending))
    return True

@app.post('/uplerr')
async def task_error(r: Request):
    task = base64.b64decode(r.headers['taskid']).decode()
    if task not in pending:
        return False
    pending.remove(task)
    task = os.path.join(SOURCE_DIR, task)
    if os.path.exists(saved_path(task)) or os.path.exists(err_path(task)):
        return False
    print('report err file:', task)
    with open(err_path(task), 'w') as f:
        pass
    return True

@app.get('/')
async def task_getter():
    cur = todo.pop()
    abscur = os.path.join(SOURCE_DIR, cur)
    while os.path.exists(saved_path(abscur)) or os.path.exists(err_path(abscur)):
        cur = todo.pop() # 没有任务抛长度异常
        abscur = os.path.join(SOURCE_DIR, cur)
    pending.add(cur)
    asyncio.create_task(recover(cur))
    return FileResponse(abscur, filename=os.path.split(cur)[-1], headers={'taskid': base64.b64encode(cur.encode()).decode()})


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=29999)