import os
import json
import asyncio

import aiohttp
import magic

import const

fl_cache_dir = const.DOWNLOAD_FILELIST_CACHE_DIR
doc_cache_dir = const.DOWNLOAD_DOC_CACHE_DIR
doc_cache_dir.mkdir(exist_ok=True)
(doc_cache_dir / 'pdf').mkdir(exist_ok=True)
(doc_cache_dir / 'doc').mkdir(exist_ok=True)

filelist = list(os.listdir(fl_cache_dir))

LANGMAP = {
    'ar': 'A',
    'zh': 'C',
    'en': 'E',
    'fr': 'F',
    'ru': 'R',
    'es': 'S',
    # 'other': 'O', # 一般是德语
    'ot': 'O',
}

task_list = asyncio.Queue()

async def get_doc():
    while not task_list.empty():
        symbol, l, save_filename_pdf, save_filename_doc = await task_list.get()
        for retry in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    resp = await session.get(f'https://documents.un.org/api/symbol/access?s={symbol}&l={l}&t=doc', headers={
                        "accept-encoding":"gzip, deflate, br", # br压缩要额外装brotli这个库才能有requests支持
                        "user-agent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
                    })
                    if resp.status == 200:
                        bin_content = await resp.content.read()
                        typ = magic.from_buffer(bin_content, mime=True)
                        if typ == 'application/pdf':
                            save_dir = save_filename_pdf
                        elif typ in (
                            'application/msword',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        ):
                            save_dir = save_filename_doc
                        else:
                            print(f'!!!!!unknown type: {typ}!!!!!')
                            with open(doc_cache_dir / f'unknowndoc{typ}.bin') as f:
                                f.write(bin_content)
                            exit(1)
                        with open(save_dir, 'wb') as f:
                            f.write(bin_content)
                        print('download done:', save_dir)
                        break
                    else:
                        if retry == 2:
                            print(resp)
                            print(resp.headers)
                            print(await resp.text())
                            print('!!!!!ERROR!!!!!')
                            return
            except Exception as e:
                print(e)
                print('retry:', retry)
                if retry == 2:
                    print('!!!!!ERROR!!!!!')
                    return

async def main():
    for i in filelist:
        if i.endswith('.json'):
            with open(fl_cache_dir / i, 'r') as f:
                data = json.load(f)
            for idx, j in enumerate(data['docs']):
                symbol = j['symbol']
                langs = j['languageCode']
                for lang in langs:
                    lang = lang.lower()[:2]
                    if lang in LANGMAP:
                        l = LANGMAP[lang]
                        save_filename_pdf = doc_cache_dir / 'pdf' / f"{i.removesuffix('.json')}-{idx}={lang}.pdf"
                        save_filename_doc = doc_cache_dir / 'doc' / f"{i.removesuffix('.json')}-{idx}={lang}.doc"
                        if save_filename_pdf.exists() or save_filename_doc.exists():
                            print('skip:', save_filename_pdf)
                            continue
                        await task_list.put((symbol, l, save_filename_pdf, save_filename_doc))

    workers = [
        get_doc() for _ in range(16)
    ]
    await asyncio.gather(*workers)

asyncio.run(main())
