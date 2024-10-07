import csv
import os
os.environ['ARGOS_DEVICE_TYPE'] = 'cuda'

from nltk.translate.bleu_score import sentence_bleu
import argostranslate.translate
import argostranslate.package
import datasets
import openpyxl

import const

INSTALLED = {}
def get_or_install_translator(_from = 'zh', _to = 'en'):
    if tr := INSTALLED.get((_from, _to), None):
        return tr
    try:
        tr = argostranslate.translate.get_translation_from_codes(_from, _to)
        INSTALLED[(_from, _to)] = tr
        return tr
    except Exception as e:
        print(e, '\nattempt to install package...')
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    for i in filter(lambda x: x.from_code == _from and x.to_code == _to, available_packages):
        print('install', i)
        i.install()
    INSTALLED[(_from, _to)] = argostranslate.translate.get_translation_from_codes(_from, _to)
    return INSTALLED[(_from, _to)]

ALL_SOURCE_LANGS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')

if __name__ == "__main__":
    for lang in ALL_SOURCE_LANGS:
        csv_file_path = const.ALIGN_OUTPUT_DIR / f'{lang}2en_bleu.csv'
        xlsx_file_path = const.ALIGN_OUTPUT_DIR / f'{lang}2en_bleu.xlsx'
        is_exists = False
        ds = datasets.load_from_disk(const.ALIGN_OUTPUT_DIR / f'{lang}2en')
        print(len(ds))
        visited = set()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'bleu_score'
        ws.append(['ID','src', 'tr_src', 'dst', 'srclen', 'dstlen','src_rate','dst_rate','bleu1','bleu2','bleu3','bleu4','bleu2avg','bleu3avg','bleu4avg'])

        # if csv_file_path.exists():
        #     is_exists = True
        #     csv_file = open(csv_file_path, 'r+', newline='\n')
        #     reader = csv.DictReader(csv_file)
        #     for data in reader:
        #         try:
        #             visited.add(data['ID'])
        #         except KeyError:
        #             is_exists = False
        #             csv_file.seek(0)
        #             csv_file.truncate()
        #             csv_file.seek(0)
        #             break
        # else:
        #     csv_file = open(csv_file_path, 'w', newline='\n')

        # writer = csv.DictWriter(csv_file, fieldnames=['ID','src', 'tr_src', 'dst', 'srclen', 'dstlen','src_rate','dst_rate','bleu1','bleu2','bleu3','bleu4','bleu2avg','bleu3avg','bleu4avg'])
        # if not is_exists:
        #     writer.writeheader()

        translator = get_or_install_translator(lang, 'en')
        for p, i in enumerate(ds): # clean_para_index_set_pair, src_rate, dst_rate
            data_id = i['record'] + '-' + i['clean_para_index_set_pair']
            if data_id in visited:
                print('skipped', data_id)
                visited.discard(data_id)
                continue
            dst = i['dst_text'].split()
            # if len(dst) < 5:
            #     continue
            translated_en = translator.translate(i['src_text'].replace('\n', ' '))
            translated_en_list = translated_en.split()
            # if len(translated_en_list) < 5:
                # continue
            bleu = sentence_bleu([dst], translated_en_list, weights=[
                (1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, 0, 1, 0),
                (0, 0, 0, 1),
                (0.5, 0.5, 0, 0),
                (0.333, 0.333, 0.333, 0),
                (0.25, 0.25, 0.25, 0.25),
            ])
            ws.append(
                [
                    data_id,
                    i['src_text'],
                    translated_en,
                    i['dst_text'],
                    len(translated_en_list),
                    len(dst),
                    i['src_rate'],
                    i['dst_rate'],
                    bleu[0],
                    bleu[1],
                    bleu[2],
                    bleu[3],
                    bleu[4],
                    bleu[5],
                    bleu[6]
                ]
            )
            # writer.writerow({
            #     "ID": data_id,
            #     "src": i['src_text'],
            #     "tr_src": translated_en,
            #     "dst": i['dst_text'],
            #     "srclen": len(translated_en_list),
            #     "dstlen": len(dst),
            #     "src_rate": i['src_rate'],
            #     "dst_rate": i['dst_rate'],
            #     "bleu1": bleu[0],
            #     "bleu2": bleu[1],
            #     "bleu3": bleu[2],
            #     "bleu4": bleu[3],
            #     "bleu2avg": bleu[4],
            #     "bleu3avg": bleu[5],
            #     "bleu4avg": bleu[6]
            # })
            print(p, len(ds), bleu)
        wb.save(xlsx_file_path)

        # csv_file.close()

