import os
import json
import random
os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'

import datasets


import const

# ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar', 'de') # 禁用德语
ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar') # 其它每对语言抽2000条

if __name__ == "__main__":
    for lang in ALL_SOURCE_LANGS:
        ds = datasets.load_from_disk(const.ALIGN_OUTPUT_DIR / f'{lang}2en')
        print(lang, len(ds), ds.features)
        
        dst_text_lens = []
        for idx, d in enumerate(ds):
            l = len(d['dst_text'])
            word_len = len(d['dst_text'].split())
            # if l < 32 or word_len < 5: continue
            dst_text_lens.append((idx, l, word_len))
        
        dst_text_lens.sort(key=lambda x: x[1], reverse=True)

        print(len(dst_text_lens))
        sorted_by_len_ds = ds.select(list(dst_text_lens[i][0] for i in range(len(dst_text_lens))))

        # with open(const.ALIGN_OUTPUT_DIR / f'{lang}2en_dumpall_original.jsonl', 'w') as f:
        #     for item in ds:
        #         f.write(json.dumps(item, ensure_ascii=False) + '\n')
        with open(const.ALIGN_OUTPUT_DIR / f'{lang}2en_dumpall_sorted.jsonl', 'w') as f:
            for item in sorted_by_len_ds:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')