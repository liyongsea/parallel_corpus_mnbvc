import os
import json
import random
import shutil
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
            if l < 32 or word_len < 5: continue # 字符串长度
            dst_text_lens.append((idx, l, word_len))
        
        dst_text_lens.sort(key=lambda x: x[1], reverse=True)

        print(len(dst_text_lens))

        longest_indices = list(map(lambda x: x[0], dst_text_lens[:100]))  # 取前100条最长的
        shortest_indices = list(map( lambda x: x[0], dst_text_lens[-100:]))

        # Select 100 rows with the longest data, 100 rows with the shortest data, and the rest randomly selected
        longest_rows = ds.select(longest_indices)
        shortest_rows = ds.select(shortest_indices)
        remaining_indices = set(map(lambda x: x[0], dst_text_lens))
        remaining_indices -= set(longest_indices)
        remaining_indices -= set(shortest_indices)
        print("remaining_indices", len(remaining_indices))
        remaining_indices = list(remaining_indices)
        random.shuffle(remaining_indices)
        random_remaining = ds.select(remaining_indices[:1800])

        # Combine the selected rows into a new dataset
        final_ds = datasets.concatenate_datasets([longest_rows, shortest_rows, random_remaining])

        if (const.ALIGN_OUTPUT_DIR / f'{lang}2en_sampled').exists():
            shutil.rmtree(const.ALIGN_OUTPUT_DIR / f'{lang}2en_sampled')
        # Save the final dataset to disk
        final_ds.save_to_disk(const.ALIGN_OUTPUT_DIR / f'{lang}2en_sampled')
        # Save as jsonl for viewing in VSCode
        with open(const.ALIGN_OUTPUT_DIR / f'{lang}2en_sampled.jsonl', 'w') as f:
            for item in final_ds:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                # print(f"Saved {lang}2en sampled dataset to disk.")