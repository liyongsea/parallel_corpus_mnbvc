import csv

from nltk.translate.bleu_score import sentence_bleu
import argostranslate.translate
import argostranslate.package
import datasets

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
        if csv_file_path.exists():
            continue
        with open(csv_file_path, 'w', newline='\n') as csv_file:
            writer = csv.writer(csv_file)
            ds = datasets.load_from_disk(const.ALIGN_OUTPUT_DIR / f'{lang}2en')
            print(len(ds))
            translator = get_or_install_translator(lang, 'en')
            writer.writerow(['src', 'dst', 'srclen', 'dstlen','src_rate','dst_rate','bleu1','bleu2','bleu3','bleu4','bleu2avg','bleu3avg','bleu4avg'])
            for p, i in enumerate(ds):
                dst = i['dst_text'].split()
                if len(dst) < 5:
                    continue
                translated_en = translator.translate(i['src_text'].replace('\n', ' '))
                translated_en_list = translated_en.split()
                if len(translated_en_list) < 5:
                    continue
                bleu = sentence_bleu([dst], translated_en_list, weights=[
                    (1, 0, 0, 0),
                    (0, 1, 0, 0),
                    (0, 0, 1, 0),
                    (0, 0, 0, 1),
                    (0.5, 0.5, 0, 0),
                    (0.333, 0.333, 0.333, 0),
                    (0.25, 0.25, 0.25, 0.25),
                ])
                writer.writerow([
                    translated_en,
                    i['dst_text'],
                    len(translated_en_list),
                    len(i['dst_text']),
                    i['src_rate'],
                    i['dst_rate'],
                    bleu[0], bleu[1], bleu[2], bleu[3], bleu[4], bleu[5], bleu[6]
                ])
                print(p, len(ds), bleu)
