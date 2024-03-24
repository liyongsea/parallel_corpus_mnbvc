import os
import json

import requests
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

                    url = f'https://documents.un.org/api/symbol/access?s={symbol}&l={l}&t=doc'
                    resp = requests.get(url)
                    if resp.status_code == 200:
                        typ = magic.from_buffer(resp.content, mime=True)
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
                                f.write(resp.content)
                            exit(1)
                        with open(save_dir, 'wb') as f:
                            f.write(resp.content)
                        print('download done:', save_dir)
                    else:
                        print(resp)
                        print(resp.headers)
                        print(resp.text)
                        print('!!!!!ERROR!!!!!')
        os.rename(fl_cache_dir / i, fl_cache_dir / f'{i}.getdoc_done')
