import json
import hashlib
import argparse
import copy
import os

parser = argparse.ArgumentParser(description='Process some files.')
parser.add_argument('input', type=str, help='The input file path', nargs='?')
parser.add_argument('-d', '--directory', type=str, help='Process a directory instead of a single file')
parser.add_argument('-ea', '--enable_assert', action='store_true', help='Enable assertions in the script')

args = parser.parse_args()

is_first = True

KEEP_KEYS = [
    "行号",
    "是否重复",
    "是否跨文件重复",
    "it_text",
    "zh_text",
    "en_text",
    "ar_text",
    "nl_text",
    "de_text",
    "eo_text",
    "fr_text",
    "he_text",
    "ja_text",
    "pt_text",
    "ru_text",
    "es_text",
    "sv_text",
    "ko_text",
    "th_text",
    "other1_text",
    "other2_text",
    "id_text",
    "cht_text",
    "vi_text",
    "扩展字段",
    "时间",
    "zh_text_md5",
]

def process_file(file_path):
    global is_first
    parent, filename = os.path.split(file_path)
    out_file_dir = os.path.join(parent, "jsonl_reworked")
    out_file_path = os.path.join(parent, "jsonl_reworked", filename)
    if is_first:
        if os.path.exists(out_file_dir):
            print(f"请确保{out_file_dir}目录为空，否则其内容可能会被覆盖。如不希望请直接结束本程序。")
            if input("请输入Y以确认继续进行:") != 'Y':
                print("程序退出...")
                exit(0)
        else:
            os.makedirs(out_file_dir)
        is_first = False

    with open(file_path, "r", encoding='utf-8') as fi, open(out_file_path, "w", encoding='utf-8') as fo:
        for line in fi.read().strip().split('\n'):
            data = json.loads(line)
            if data['扩展字段'] == '':
                data['扩展字段'] = r'{}'
            if args.enable_assert:
                try:
                    json.loads(data['扩展字段'])
                except Exception as e:
                    print("【错误】非法扩展字段：", data['扩展字段'])
                    exit(1)
            data['段落数'] = len(data['段落'])
            para_low_quality_count = 0
            zh_text_set = set()
            for pid, p in enumerate(data['段落']):
                if p['扩展字段'] == '':
                    p['扩展字段'] = r'{}'
                if args.enable_assert:
                    assert p['other1_text'] == '', f"【错误】段落{p['行号']}中存在other1_text字段 => {p}，请确认具体是哪种语言，并填入扩展字段中"
                    assert p['other2_text'] == '', f"【错误】段落{p['行号']}中存在other2_text字段 => {p}，请确认具体是哪种语言，并填入扩展字段中"
                    try:
                        json.loads(p['扩展字段'])
                    except Exception as e:
                        print("【错误】非法扩展字段：", p)
                        exit(1)
                cleared_zh_text = p['zh_text'].strip()
                cleared_en_text = p['en_text'].strip()
                if not cleared_en_text or not cleared_en_text:
                    para_low_quality_count += 1
                if not cleared_zh_text:
                    p['zh_text_md5'] = ''
                else:
                    p['zh_text_md5'] = hashlib.md5(cleared_zh_text.encode()).hexdigest()
                if cleared_zh_text in zh_text_set:
                    p['是否重复'] = True
                else:
                    p['是否重复'] = False
                zh_text_set.add(cleared_zh_text)
            data['去重段落数'] = len(data['段落']) - len(zh_text_set)
            data['低质量段落数'] = para_low_quality_count
            data['是否待查文件'] = False
            data['是否重复文件'] = False
            data_cloned = copy.deepcopy(data)
            data_cloned.pop('段落')
            
            for pid, p in enumerate(data['段落']):
                for k in KEEP_KEYS:
                    data_cloned[k] = p[k]
                json.dump(data_cloned, fo, ensure_ascii=False)
                fo.write('\n')

if args.directory:
    for filename in os.listdir(args.directory):
        if filename.endswith('.jsonl'):
            print('filename:',filename)
            process_file(os.path.join(args.directory, filename))
elif args.input:
    process_file(args.input)
else:
    print("请提供一个目录或输入文件路径。")
    exit(0)

os.system('pause')