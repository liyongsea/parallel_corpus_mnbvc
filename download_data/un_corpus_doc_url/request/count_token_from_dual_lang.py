from pathlib import Path

import datasets
import jieba

BASE_PATH = Path(r'F:\undl_text_alignment_prod')

for lang in [
    # 'de', 'ar', 'es', 'fr', 'ru',
    'zh']:
    ds_path = BASE_PATH / f'{lang}2en'
    ds = datasets.load_from_disk(ds_path)
    # print(lang, ds.column_names)
    # print(lang, len(ds))
    sum_token_lang = 0
    sum_token_en = 0
    for d in ds:
        if lang == 'zh':
            sum_token_lang += len(jieba.lcut(d['src_text']))
        else:
            sum_token_lang += len(d['src_text'].split())
        sum_token_en += len(d['dst_text'].split())
    print(lang, sum_token_en, sum_token_lang)
