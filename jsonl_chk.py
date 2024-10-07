import json
import hashlib
INPUT = r"E:\[L1]Doc\WeChat Files\xxx\FileStorage\File\2024-10\杀戮尖塔(1).jsonl"
with open(INPUT, "r") as f:
    for line in f.read().splitlines():
        data = json.loads(line)
        assert data['段落数'] == len(data['段落']), f"【错误】段落数不等于实际段落数量 => 本脚本算出来的:{len(data['段落'])} 语料里的:{data['段落数']}"
        para_without_cn_count = 0
        zh_text_set = set()
        for pid, p in enumerate(data['段落']):
            assert hashlib.md5(p['zh_text'].encode()).hexdigest() == p['zh_text_md5'], f"【错误】{pid}段文本的MD5校验失败 => 本脚本算出来的:{hashlib.md5(p['zh_text'].encode()).hexdigest()} 语料里的:{p['zh_text_md5']}"
            zh_text_set.add(p['zh_text'])
            if len(p['zh_text'].strip()) == 0: # 要不要strip()?
                para_without_cn_count += 1
            # print(p['行号'])
        assert data['去重段落数'] == len(zh_text_set), f"【错误】去重段落数不等于实际去重段落数量 => 本脚本算出来的:{len(zh_text_set)} 语料里的:{data['去重段落数']}"
        assert data['低质量段落数'] == para_without_cn_count, f"【错误】低质量段落数不等于实际低质量段落数量 => 本脚本算出来的:{para_without_cn_count} 语料里的:{data['低质量段落数']}"
    
print('OK')
