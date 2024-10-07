import openpyxl
import csv

import const

ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')

if __name__ == "__main__":
    for lang in ALL_SOURCE_LANGS:
        csv_file_path = const.ALIGN_OUTPUT_DIR / f'{lang}2en_bleu.csv'
        xlsx_file_path = const.ALIGN_OUTPUT_DIR / f'{lang}2en_bleu_converted.xlsx'

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'bleu_score'
        ws.append(['ID','src', 'tr_src', 'dst', 'srclen', 'dstlen','src_rate','dst_rate','bleu1','bleu2','bleu3','bleu4','bleu2avg','bleu3avg','bleu4avg'])

        is_first = True

        with open(csv_file_path, "r", encoding='utf-8') as f:
            creader = csv.reader(f)
            for i in creader:
                if is_first:
                    is_first = False
                    continue
                ws.append(i)
        wb.save(xlsx_file_path)