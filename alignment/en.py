from collections import deque
import itertools
from datasets import load_dataset
import re
import datetime

now_timer = datetime.datetime.now()

"""
工作方向：
1. 先做英语的段落。
2. 把其它语言的段落映射到英语去。


"""

dataset = load_dataset("ranWang/test_pdf_data", split='new')

filtered_file = []

EDIT_DISTANCE_THRESOLD = 3

def edit_distance(s1, s2):
    """chatgpt帮我写的n方编辑距离算法"""
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    if len(s2) - len(s1) > EDIT_DISTANCE_THRESOLD: # 优化相当大的O(1)剪枝
        return EDIT_DISTANCE_THRESOLD + 1
    
    # O(n)统计字符，进一步剪掉一些不必要用n^2编辑距离的情况 625s优化到22s
    char_distance = 0
    d = {}
    for s in s1:
        d[s] = d.get(s, 0) + 1
    for s in s2:
        d[s] = d.get(s, 0) - 1
    positive = 0
    negative = 0
    for k, v in d.items():
        if v > 0:
            positive += v
        else:
            negative += - v
    char_distance = max(positive, negative)
    if char_distance > EDIT_DISTANCE_THRESOLD:
        return char_distance

    distances = range(len(s1) + 1)

    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_

    return distances[-1]

def read_int(s: str) -> int:
    "从开头开始读一段连续的数字"
    x = 0
    for c in s:
        if c.isdigit():
            x = x * 10 + int(c)
        else:
            return x
    return x

truncate_token = 'This record contains the text of speeches delivered in English and of the '
begin_token = re.compile(r'^The meeting was called to order at') # 151
begin_token2 = re.compile(r'^The meeting resumed at') # 6
suspend_token = re.compile(r'The meeting was suspended at')
rose_token = re.compile(r'The meeting rose at')


speaker_token = re.compile(r'^[A-Z].{2,25}( \(.*?\))?: ')

info_page_token = re.compile(r'United Nations .*?Corrections will be issued after the end of the session in a consolidated corrigendum\.', flags=re.M | re.S)
info_page_token2 = re.compile(r'United Nations .*?Corrected records will be reissued electronically on the Official Document System of the United Nations \(http://documents\.un\.org\)\.', flags=re.M | re.S)
info_page_token3 = re.compile(r'This record contains the text of speeches delivered in English.*?Corrected records will be reissued electronically on the Official Document System of the United Nations \(http://documents\.un\.org\)\.', flags=re.M | re.S)

def extract_sentences_from_single_file(filetext: list[str]):
    """把文件里的每个句子尽可能合并出来，输入是一个包含每页所有字符的列表，输出会把这个列表拍平
    输入应该每行事先做好strip"""

    """通过连续的标号来认段落，这个搞法比较激进"""
    match_infos = []
    line_marker = [] # 可以去掉换行的行数
    outputs = []
    lineno_pattern = re.compile(r'^[0-9]{1,3}\. [A-Z]')
    linedot_pattern = re.compile(r'^• [A-Z]')
    # for pageid, page in enumerate(filetext):
    flatten = list(itertools.chain(*[page.split('\n') for page in filetext]))
    for lineid, line in enumerate(flatten):
        m = re.match(lineno_pattern, line)
        if m:
            g = m.group(0)
            match_infos.append((read_int(g), lineid))
        m = re.match(linedot_pattern, line)
        if m:
            g = m.group(0)
            match_infos.append((-114514, lineid))
        
    for idx, (linecounter, lineid) in enumerate(match_infos[1:]):
        # 相邻两个识别头标号连续，则中间行的空格可以删掉（换成空格，将两段话拼在一起）
        prevcounter, previd = match_infos[idx]
        if linecounter == prevcounter + 1 or linecounter == prevcounter == -114514:
            line_marker.extend(range(previd, lineid - 1))

    line_marker.reverse()

    for lineid, line in enumerate(flatten):
        # if re.match(article_pattern, line) or outputs and re.match(article_pattern, outputs[-1]):
            # outputs.append(line)
            # continue
        while line_marker and line_marker[-1] < lineid - 1:
            line_marker.pop()

        if line_marker and lineid - 1 == line_marker[-1]:
            line_marker.pop()
            outputs[-1] += ' ' + line
        else:
            outputs.append(line)

    """根据观察，有至少三个因素影响一行结尾的回车能不能被删掉
    1. 次行首字母是不是小写字母
    2. 本行末尾字符是不是句号
    3. 本行是不是约有50个字符"""
    
    inputs: list[str] = outputs
    outputs = [inputs[0]]
    for lineid, nextline in enumerate(inputs[1:]):
        if not nextline:
            continue
        sc = 0 # 正表示删换行，负表示保留换行
        prevline = outputs[-1]
        if prevline[-1] == '.':
            sc -= 44
        if prevline[-1] == ',':
            sc += 81

        sc += min(60, len(inputs[lineid])) - 32

        if nextline[0].islower():
            sc += 83
        if re.match(lineno_pattern, nextline):
            sc -= 999
        if re.match(linedot_pattern, nextline):
            sc -= 999
        if re.match(speaker_token, nextline):
            sc -= 999


        if sc > 0:
            outputs[-1] += ' ' + nextline
        else:
            outputs.append(nextline)
    
    """将The meeting rose at ...后一直到The meeting was called to order...中间的部分去掉"""
    inputs: list[str] = outputs
    outputs = []
    accept_line = True
    for line in inputs:
        if accept_line:
            if re.search(rose_token, line):
                accept_line = False
            outputs.append(line)
        else:
            if re.match(begin_token, line) or re.match(begin_token2, line):
                accept_line = True
                outputs.append(line)

    output = '\n'.join(outputs)
    output = re.sub(info_page_token, '', output)
    output = re.sub(info_page_token2, '', output)
    output = re.sub(info_page_token3, '', output)
    return output

def filter_index_title(file_index_titles: list, page: str):
    """把正文里的目录索引条目拿掉"""

    filtered_page = []
    unmatched = deque()
    for lineid, line in enumerate(pageline := page.split('\n')):
        line = line.strip()
        matched = False
        for cid, file_index_title in enumerate(file_index_titles): # 每个都for太慢了，几十秒一个pdf
            if (ed := edit_distance(file_index_title, line)) <= EDIT_DISTANCE_THRESOLD:
                while unmatched: filtered_page.append(unmatched.popleft())
                matched = True
                print(file_index_title, ed, 'cid:', cid)
                break
            else:
                if unmatched:
                    back_line = unmatched.pop()
                    # 如果要改三行的话这里要修改一下
                    if (ed := edit_distance(back_line + ' ' + line, file_index_title)) <= EDIT_DISTANCE_THRESOLD:
                        while unmatched: filtered_page.append(unmatched.popleft())
                        matched = True
                        print(file_index_title, ed, 'cid:', cid)
                        break
                    else:
                        unmatched.append(back_line)

        if not matched:
            unmatched.append(line)
            while len(unmatched) > 1:
                filtered_page.append(unmatched.popleft())
    while unmatched: filtered_page.append(unmatched.popleft())
    return '\n'.join(filtered_page)


INDEX_TOKEN = '...'

maxed = 0

for rowid, row in enumerate(dataset):
    filtered_pages = {}
    for lang in ['en']:
        lang_match_file_content = row["content"][lang]
        file_index_titles = []
        for pageid, page in enumerate(lang_match_file_content):
            lines = []
            dot_count = 0
            pageline = page.split('\n')
            # 第一次过滤：分页符
            if pageid == 0:
                for truncated_title_pageline_index, line in enumerate(pageline):
                    if re.match(begin_token, line) or re.match(begin_token2, line):
                        break
                pageline = pageline[truncated_title_pageline_index:]

            for lineid, line in enumerate(pageline):
                line = line.strip()
                if lineid < 4 or len(pageline) - lineid < 3: # discard pagination info
                    line = re.sub(r'([a-zA-Z0-9\.]{1,13}/){2,5}[A-Za-z0-9\.]{1,13}', '', line) # 拿掉文件码
                    line = re.sub(r'^([0-9/]{1,8} ){0,1}[0-9-]{1,8}( [/0-9]{1,8}){0,1}$', '', line) # 拿掉页码
                    line = line.strip()
                    line = re.sub(r'^(\([PartVol\.]{1,4} [IVX]{1,4}\)\*?)$', '', line) # 拿掉Part、Vol
                    line = re.sub(r'^Article [IVX]{1,4}$', '', line) # 拿掉Article索引

                line = line.strip()
                line = re.sub(r'^\*[0-9]+\*$', '', line)
                line = re.sub(r'^[0-9]+-[0-9]+ \(E\)$', '', line)
                if line:
                    lines.append(line)
                if INDEX_TOKEN in line:
                    dot_count += 1
            
            if dot_count >= 4: # 有大于4行三个点的我们认为是目录页，用特别的处理方式或者先跳过
                unmatched = []

                for line in lines:
                    line = line.strip().replace('\ufffe', '-') # 瞪眼法得，\ufffe应该是连词符-
                    if INDEX_TOKEN in line:
                        title: str = line.split(INDEX_TOKEN, 1)[0].strip()
                        done = 0

                        # 有个特征是标题总是有一个带.的标号
                        for rid in range(len(unmatched), max(len(unmatched) - 4, -1), -1):
                            concat_title = ' '.join([*unmatched[rid:], title])
                            dot_pos = concat_title.find('.')
                            if dot_pos != -1 and dot_pos < 6: # .出现的地方如果太靠后，我们不要
                                file_index_titles.append(concat_title)
                                done = 1
                                break # 没找到就取title
                        if not done:
                            file_index_titles.append(title)
                        unmatched.clear()
                    else:
                        unmatched.append(line)
                lang_match_file_content[pageid] = '' # 拿掉目录页
            else:

                dst = '\n'.join(lines)
                lang_match_file_content[pageid] = dst
        # 二次过滤：去掉目录索引
        for pageid, page in enumerate(lang_match_file_content):
            # dst = page
            dst = filter_index_title(file_index_titles, page)
            if dst:
                filtered_pages.setdefault(lang, []).append(dst)

    filtered_file.append(filtered_pages)

dd = {}

for fi in filtered_file:
    for lang, content in fi.items():
        # for p, i in enumerate(content):
            # content[p] = eliminate_zh_breakline_mainwork(i)
        # dd.setdefault(lang, []).append('=========='.join(content))  # 页
        dd.setdefault(lang, []).append(extract_sentences_from_single_file(content))  # 页

for lang, content in dd.items():
    with open(f'{lang}2.txt', 'w', encoding='utf-8') as f: # 将所有字符整合成一个输出到单文件中
        f.write('\n<<<<<<<<<<\n'.join(content))  # 文件分隔符


print('running time:', (datetime.datetime.now() - now_timer).total_seconds())