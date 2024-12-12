"""
mnbvc 平行语料小组的通用后处理脚本。每个语料文件都应该在数据检查器之前运行此脚本，否则语料文件将被拒绝发布。
- 将旧式平行语料转换为新式平行语料
- 自动填充几个能够根据给定段落计算出来的字段
- 验证扩展字段（仅接受 json 格式）。
- 完成基本的自动去重、删除空行

老版本平行语料样例（注意：实际语料一行为一个有效json，不会在json中穿插换行符，这里做换行和缩进仅作为展示用）：
{
    "文件名": "Terraria-workshop-localization_test2.jsonl",
    "是否待查文件": false,
    "是否重复文件": false,
    "段落数": 17944,
    "去重段落数": 0,
    "低质量段落数": 0,
    "段落": [
        {
            "行号": 1,
            "是否重复": false,
            "是否跨文件重复": false,
            "it_text": "",
            "zh_text": "正在生成海洋沙",
            "en_text": "Generating ocean sand",
            "ar_text": "",
            "nl_text": "",
            "de_text": "",
            "eo_text": "",
            "fr_text": "Génération du sable de l'océan",
            "he_text": "",
            "ja_text": "",
            "pt_text": "Gerando areia do oceano",
            "ru_text": "Создание песка в океане",
            "es_text": "",
            "sv_text": "",
            "ko_text": "",
            "th_text": "",
            "other1_text": "",
            "other2_text": "",
            "id_text":"",
            "cht_text":"",
            "vi_text":"",
            "扩展字段": "{\"other_texts\": {\"cs\": \"Generování mořského písku\", \"pl\": \"Generowanie piasku morskiego\", \"hu\": \"Tengeri homok elhelyezése\", \"uk\": \"Генерація океанського піску\", \"tr\": \"Okyanus kumu üretme\"}}",
            "时间": "20240316",
            "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2"
        }
    ],
    "扩展字段": "{\"other_texts_iso_map\": {\"cs\": \"捷克语\", \"pl\": \"波兰语\", \"hu\": \"匈牙利语\", \"uk\": \"乌克兰语\", \"tr\": \"土耳其语\"}}",
    "时间": "20240316"
}

升级后的新版本语料样例：

{
    "文件名": "Terraria-workshop-localization_test2.jsonl",
    "是否待查文件": false,      【不用手填】
    "是否重复文件": false,      【不用手填】
    "段落数": 17944,            【不用手填】
    "去重段落数": 0,            【不用手填】
    "低质量段落数": 0,          【不用手填】
    "行号": 1,                  【不用手填】
    "是否重复": false,          【不用手填】
    "是否跨文件重复": false,    【不用手填】
    "it_text": "",
    "zh_text": "正在生成海洋沙",
    "en_text": "Generating ocean sand",
    "ar_text": "",
    "nl_text": "",
    "de_text": "",
    "eo_text": "",
    "fr_text": "Génération du sable de l'océan",
    "he_text": "",
    "ja_text": "",
    "pt_text": "Gerando areia do oceano",
    "ru_text": "Создание песка в океане",
    "es_text": "",
    "sv_text": "",
    "ko_text": "",
    "th_text": "",
    "id_text":"",
    "cht_text":"",
    "vi_text":"",
    "扩展字段": "{\"other_texts\": {\"cs\": \"Generování mořského písku\", \"pl\": \"Generowanie piasku morskiego\", \"hu\": \"Tengeri homok elhelyezése\", \"uk\": \"Генерація океанського піску\", \"tr\": \"Okyanus kumu üretme\"}}",
    "时间": "20240316",
    "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2"   【不用手填】
}

弃用other1_text、other2_text，展平段落，用段落内层的扩展字段替换外层文件级扩展字段，对于文件级的信息，按段落冗余一份，以文件名为唯一过滤依据

"""
import json
import hashlib
import argparse
import copy
import os
import pickle
import gc
from typing import List

parser = argparse.ArgumentParser(description='''Common post-process script for parallel corpus mnbvc. Every corpus file should run this script before datachecker, or the corpus file cannot be accepted then published.
    - convert old-style parallel corpus to new-style parallel corpus
    - autofill common fields
    - validate extension field (only json format is accepted).
    - auto deduplicate
    - delete empty lines
''')
parser.add_argument('input', type=str, help='The input file path', nargs='?')
parser.add_argument('-d', '--directory', type=str, help='Process a directory instead of a single file')
parser.add_argument('-v', '--verbose', action='store_true', help='Print deduplication info')
parser.add_argument('-dr', '--disable_rename', action='store_true', help='Disable auto assign json `filename` field to its file name')
parser.add_argument('-dbg', '--debug', action='store_true', help='Print debug info')
# parser.add_argument('-ea', '--enable_assert', action='store_true', help='Enable assertions in the script')
# parser.add_argument('-da', '--disable_auto_dedup', action='store_true', help='Disable auto deduplicate and empty line elimination')

args = parser.parse_args()
del parser
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
    "id_text",
    "cht_text",
    "vi_text",
    "扩展字段",
    "时间",
    "zh_text_md5",
]

LANG_FIELDS = [
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
    "id_text",
    "cht_text",
    "vi_text",
]

NEW_STYLE_FIELDS = [
    "文件名",
    "是否待查文件",
    "是否重复文件",
    "段落数",
    "去重段落数",
    "低质量段落数",
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
    "id_text",
    "cht_text",
    "vi_text",
    "扩展字段",
    "时间",
    "zh_text_md5",
]

def scan_filelines(filelines: List[dict]):
    """扫描filelines，填上不需要手动填写的部分，此时传入的filelines除了【不用手填】的字段之外应该已经是一个有效的新版本语料格式"""
    valid_filelines = []
    # 引入处理如龙6语料的自动去除所有非空语言中，出现的字符串完全一致的情况，如{"en_text":"I'm here","zh_text":"I'm here"}，这种语料完全没有意义
    # 同时在此处统一将文本.strip，并去掉完全为空的段落
    if args.debug:
        print("去除空行以及重复...")
    while filelines:
        line = pickle.loads(filelines.pop())
        line_dedup_set = set()
        for lang_field in LANG_FIELDS:
            line[lang_field] = line[lang_field].strip()
            line_dedup_set.add(line[lang_field])
        line_dedup_set.discard("")
        if len(line_dedup_set) <= 1:
            if args.verbose:
                print('【段落去冗余】为空或不同语种字段全一致的段落:',line)
            continue
        line_dedup_set.clear()
        del line_dedup_set
        valid_filelines.append(pickle.dumps(line, protocol=pickle.HIGHEST_PROTOCOL))
    filelines = valid_filelines # 倒序
    gc.collect()
    if args.debug:
        print("文件级去重...")
    # 文件级去重，去除所有LANG_FIELDS加上扩展字段，完全一致的段落，如[{"en_text":"Fine","zh_text":"好"},{"en_text":"Fine","zh_text":"好"}],这种重复只保留第一次出现的那段
    valid_filelines = []
    dedup_str_set = set()
    while filelines:
        line = pickle.loads(filelines.pop())
        dedup_dict = {'扩展字段':line['扩展字段']}
        for lang_field in LANG_FIELDS:
            dedup_dict[lang_field] = line[lang_field]
        dedup_str = json.dumps(dedup_dict, ensure_ascii=False, sort_keys=True)
        dedup_dict.clear()
        del dedup_dict
        if dedup_str not in dedup_str_set:
            valid_filelines.append(pickle.dumps(line, protocol=pickle.HIGHEST_PROTOCOL))
        else:
            if args.verbose:
                print('【文件级去重】与其它段落完全一致的段落:',dedup_str)
        dedup_str_set.add(dedup_str)
    del dedup_str_set
    filelines = valid_filelines # 正序
    del valid_filelines
    gc.collect()
    if args.debug:
        print("统计重复和低质量...")
    # 第一遍扫描，计算【去重段落数】、【低质量段落数】，填写【是否重复】
    zh_text_dedup_set = set() # 【是否重复】由zh_text是否重复来决定
    low_quality_count = 0 # 【低质量段落数】由zh_text和en_text是否任意一个为空来决定
    for lineidx, line in enumerate(filelines):
        line = pickle.loads(line)
        zh_text = line['zh_text']
        en_text = line['en_text']
        if not zh_text or not en_text:
            low_quality_count += 1
        if zh_text in zh_text_dedup_set:
            line['是否重复'] = True
        else:
            line['是否重复'] = False
        filelines[lineidx] = pickle.dumps(line, protocol=pickle.HIGHEST_PROTOCOL)
        zh_text_dedup_set.add(zh_text)
    zh_text_dedup_count = len(zh_text_dedup_set)
    del zh_text_dedup_set
    gc.collect()
    # 第二遍扫描，填入【是否待查文件】【是否重复文件】【段落数】【去重段落数】【低质量段落数】【行号】【是否跨文件重复】【zh_text_md5】
    for lineid, line in enumerate(filelines):
        line = pickle.loads(line)
        line['是否待查文件'] = False # 平行语料组固定将此字段给False
        line['是否重复文件'] = False # 平行语料组固定将此字段给False
        line['段落数'] = len(filelines)
        line['去重段落数'] = len(filelines) - zh_text_dedup_count # 经核实，此字段统计的是“重复了的段落”的个数
        line['低质量段落数'] = low_quality_count
        line['行号'] = lineid + 1 # 行号从1开始
        line['是否跨文件重复'] = False # 平行语料组固定将此字段给False
        line['zh_text_md5'] = hashlib.md5(line['zh_text'].encode('utf-8')).hexdigest()
        cloned_line = {}
        # 确保line只包含NEW_STYLE_FIELDS中的内容
        for field in NEW_STYLE_FIELDS:
            cloned_line[field] = line.pop(field)
        line.clear()
        filelines[lineid] = pickle.dumps(cloned_line, protocol=pickle.HIGHEST_PROTOCOL)
    return filelines

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
    del out_file_dir
    first_warn_map = {'unk_key': set(), 'other_texts_key_check': set()}
    filename2lines = {} # 以文件名为主键，不同的文件名不共享行号、行结构、中文去重计数
    with open(file_path, "r", encoding='utf-8') as fi:
        # fic = fi.read() # 直接读40G文件报 Memory Error 了
        # $ wc -l dual_ass.jsonl
        # 92917622 dual_ass.jsonl
        linecounter = 0
        for line in fi:
            linecounter += 1
            if args.debug and linecounter % 100000 == 0:
                print("READING FILE:", linecounter)
            line = line.strip()
            if not line:
                continue
            data: dict = json.loads(line)
            if not args.disable_rename:
                data['文件名'] = filename # 对于游戏语料，这里强制要求文件名等于jsonl内部文件名
            filelines = filename2lines.setdefault(data['文件名'], [])
            if data.get('扩展字段') is None:
                data['扩展字段'] = data.pop('拓展字段', r'{}')
            if data['扩展字段'] == '':
                data['扩展字段'] = r'{}'
            try:
                ext_field = json.loads(data['扩展字段'])
                accepted_fields = {}
                if 'other_texts' in ext_field:
                    other_texts_field = ext_field.pop('other_texts')
                    for k, v in other_texts_field.items():
                        if len(k) != 2 or not k.islower():
                            if k not in first_warn_map['other_texts_key_check']:
                                first_warn_map['other_texts_key_check'].add(k)
                                print("【警告】other_texts含有key名可能不合ISO 639-1规范的语种双字母缩写，请向工作群报告:", k)
                    accepted_fields['other_texts'] = other_texts_field
                if 'k' in ext_field:
                    k_field = ext_field.pop('k')
                    accepted_fields['k'] = k_field
                for unknown_key, val in ext_field.items():
                    if unknown_key not in first_warn_map['unk_key']:
                        first_warn_map['unk_key'].add(unknown_key)
                        print("【警告】扩展字段含有尚未定义的字段，请向工作群报告:", unknown_key)
                    accepted_fields[unknown_key] = val # 打印警告信息，但是允许收录
                ext_field.clear()
                del ext_field
                data['扩展字段'] = json.dumps(accepted_fields, ensure_ascii=False, sort_keys=True)
                accepted_fields.clear()
                del accepted_fields
            except Exception as e:
                print("【错误】扩展字段并非有效json字符串：", data['扩展字段'])
                exit(1)
            if '段落' in data: # 旧版语料
                for pid, p in enumerate(data['段落']):
                    if '时间' not in p or not p['时间']:
                        p['时间'] = data['时间']
                    if p.get('扩展字段') is None:
                        p['扩展字段'] = p.pop('拓展字段', r'{}')
                    if p['扩展字段'] == '':
                        p['扩展字段'] = r'{}'
                    assert p['other1_text'] == '', f"【错误】段落{p['行号']}中存在other1_text字段 => {p}，请确认具体是哪种语言，并填入扩展字段中"
                    assert p['other2_text'] == '', f"【错误】段落{p['行号']}中存在other2_text字段 => {p}，请确认具体是哪种语言，并填入扩展字段中"
                    try:
                        ext_field = json.loads(p['扩展字段'])
                        p['扩展字段'] = json.dumps(ext_field, ensure_ascii=False, sort_keys=True)
                    except Exception as e:
                        print("【错误】扩展字段并非有效json字符串：", p)
                        exit(1)
                    for lang_field in LANG_FIELDS:
                        p.setdefault(lang_field, "")
                data_cloned = copy.deepcopy(data)
                data_cloned.pop('段落')
                for pid, p in enumerate(data['段落']):
                    for k in KEEP_KEYS:
                        data_cloned[k] = p[k]
                    filelines.append(pickle.dumps(data_cloned, pickle.HIGHEST_PROTOCOL))
                data_cloned.clear()
                del data_cloned
            else:
                filelines.append(pickle.dumps(data, pickle.HIGHEST_PROTOCOL)) # 需要避免把json序列化之后的东西保存下来，可能会有字符串形式的表示的数十倍大
            data.clear()
            del data
            del line
    del first_warn_map
    gc.collect()
    with open(out_file_path, "w", encoding='utf-8') as fo:
        fobuf = []
        while filename2lines:
            filename, filelines = filename2lines.popitem()
            filelines = scan_filelines(filelines)[::-1]
            gc.collect()
            while filelines:
                line = pickle.loads(filelines.pop())
            # for lineid, line in enumerate(filelines):
                fobuf.append(json.dumps(line, ensure_ascii=False, sort_keys=True) + '\n')
                line.clear()
                del line
                if len(fobuf) > 16384:
                    fo.write(''.join(fobuf))
                    fobuf.clear()
                    fo.flush()
        fo.write(''.join(fobuf))

if args.directory:
    for filename in os.listdir(args.directory):
        if filename.endswith('.jsonl'):
            print('[directory] filename:',filename)
            process_file(os.path.join(args.directory, filename))
elif args.input:
    print('[single file] filename:',args.input)
    process_file(args.input)
else:
    print("请提供一个目录或输入文件路径。")
    exit(0)

input("处理完毕，回车关闭")
