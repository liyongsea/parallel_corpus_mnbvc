import re
import os
import pickle
import shutil
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.requests import Request
from fastapi import File
from fastapi import HTTPException
from typing import Annotated, List
from fastapi.middleware.gzip import GZipMiddleware
import asyncio
import uvicorn
import base64
import datasets
from pathlib import Path
from pydantic import BaseModel
from load_and_translate import clean_paragraph

STEP = 10
SRC = 'fr'
DST = 'en'
BASE_DIR = Path(r'F:')
TASK_SOURCE = BASE_DIR / 'undl_text_local'
TASK_DEST = BASE_DIR / f"{SRC}2{DST}"
DS = datasets.load_from_disk(TASK_SOURCE)
OUTPUT_MANIFEST = r'C:\Users\Administrator\Desktop\lj\alignment\align_undl_text\client_map.txt'

TASK_DEST.mkdir(exist_ok=True)

def get_outputs():
    with open(OUTPUT_MANIFEST, 'r', encoding='utf-8') as f:
        return dict(map(lambda x: x.strip().split(), f.read().strip().splitlines()))

app = FastAPI(redoc_url=None, docs_url=None, swagger_ui_init_oauth=None, openapi_url=None)
app.add_middleware(GZipMiddleware)

todo = []

outs = get_outputs()
for i in range(0, len(DS), STEP):
    done = False
    for j in outs.values():
        task_path = TASK_DEST / j / str(i)
        if task_path.exists():
            with open(task_path / 'dup.pkl', 'rb') as f:
                tr = pickle.load(f)
            if any(tr):
                done = True
                break
            else:
                print('remove empty task', task_path)
                shutil.rmtree(task_path)
    if not done:
        todo.append(i)

print('todo:', len(todo))

class UplBody(BaseModel):
    taskid: int
    client: str
    out: List[List[str]]

@app.post('/upl')
async def task_submit(body: UplBody):
    outs = get_outputs()
    # if body.taskid not in pending:
        # raise HTTPException(400, 'taskid not found')
    if body.client not in outs:
        raise HTTPException(400, 'client not found')
    client_dir = (TASK_DEST / outs[body.client])
    client_dir.mkdir(parents=True, exist_ok=True)
    # shard = pending.pop(body.taskid)
    out_path = client_dir / str(body.taskid)
    if out_path.exists():
        raise HTTPException(400, 'taskid already exists')
    # print(len(body.out), body.out)
    # shard.add_column(f'{SRC}2{DST}', body.out)
    out_path.mkdir()
    with (out_path / 'dup.pkl').open('wb') as f:
        pickle.dump(body.out, f)
    with (out_path / 'preview.txt').open('w', encoding='utf-8') as f:
        buf = []
        for i in body.out:
            buf.append('\n\n'.join(i))
        f.write('\n==========\n'.join(buf))

    # shard.save_to_disk(out_path)
    return 1

@app.get('/')
async def task_getter():
    cur = todo.pop()
    data = DS.select(range(cur, cur + STEP))
    data = data.map(lambda x: {f'clean_{SRC}': list(filter(bool, (clean_paragraph(para) for para in re.split('\n\n', x[SRC]))))})
    data = data.map(lambda x: {f'clean_{DST}': list(filter(bool, (clean_paragraph(para) for para in re.split('\n\n', x[DST]))))})
    x = []
    for i in data:
        if not any(i[f'clean_{SRC}']) or not any(i[f'clean_{DST}']):
            x.append([])
        else:
            x.append(i[f'clean_{SRC}'])

    return {
        'taskid': cur,
        'src': SRC,
        'dst': DST,
        'data': x
    }


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=29999)