from pathlib import Path

import datasets
import jieba

BASE_PATH = Path(r'F:\rework_undl_text_local')

ds = datasets.load_from_disk(BASE_PATH)
l = len(ds) # 165840


available = {}
tokens = {}
print(ds.column_names)
for p, d in enumerate(ds):
    for lang in [
        'de', 'ar', 'es', 'fr', 'ru', 'en',
        'zh']:
        content = d[lang].strip()
        if content:
            available[lang] = available.get(lang, 0) + 1
            if lang == 'zh':
                tokens[lang] = tokens.get(lang, 0) + len(jieba.lcut(content))
            else:
                tokens[lang] = tokens.get(lang, 0) + len(content.split())
    if p % 1000 == 0:
        print(p, available, tokens, flush=True)
print(available, tokens, flush=True)