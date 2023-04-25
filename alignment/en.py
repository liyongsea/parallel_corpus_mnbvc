import re
import datetime
import itertools
from collections import deque

import nltk
import Levenshtein
from datasets import load_dataset

# GLOBAL CONSTANTS
INDEX_TOKEN = '...'

BEGIN_TOKEN = re.compile(r'The meeting was called to order at') # 151
BEGIN_TOKEN2 = re.compile(r'The meeting (was )?resumed at') # 6
SUSPEND_TOKEN = re.compile(r'The meeting was suspended at')
ROSE_TOKEN = re.compile(r'The meeting rose at')
ROSE_TOKEN2 = re.compile(r'The discussion covered in the summary record ended at ')

SPEAKER_TOKEN = re.compile(r'^[A-Z].{2,25}( \(.*?\))?: ')


# INFO_PAGE_TOKEN = re.compile(r'United Nations\s.*?The meeting was called to order at ', flags=re.M | re.S)
INFO_PAGE_TOKEN = re.compile(r'United Nations\s.*?Corrections will be issued after the end of the session in a consolidated corrigendum\.', flags=re.M | re.S)
INFO_PAGE_TOKEN2 = re.compile(r'United Nations\s.*?Corrected records will be reissued electronically on the Official Document System of the United Nations \(http://documents\.un\.org\)\.', flags=re.M | re.S)
INFO_PAGE_TOKEN3 = re.compile(r'This record contains the text of speeches delivered in English.*?Corrected records will be reissued electronically on the Official Document System of the United Nations \(http://documents\.un\.org\)\.', flags=re.M | re.S)

LINENO_TOKEN = re.compile(r'^[0-9]{1,3}\. [A-Z]')
LINEDOT_TOKEN = re.compile(r'^• [A-Z]')

EDIT_DISTANCE_THRESOLD = 3

def is_likely(s1: str, s2: str) -> bool:
    """
    这个函数以两个字符串的编辑距离为标准决定两个字符串是否相似。
    （仅用于判断这段文本是否可以被当做目录索引文本而删除。）
    如果它们之间的编辑距离大于EDIT_DISTANCE_THRESOLD，则判为不相似。

    为了优化运行效率，在计算编辑距离之前，先做了两个剪枝：
    如果两个字符串长度差超过EDIT_DISTANCE_THRESOLD，则判为不相似。
    如果两个字符串顺序无关的字符编辑距离超过EDIT_DISTANCE_THRESOLD，则判为不相似。

    Args:
        s1 (str)
        s2 (str)

    Returns:
        bool: s1和s2是否相似

    Example:
        >>> is_likely("kit", "sitting")
        False
        >>> is_likely("flaw", "lawn")
        True
    """
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    if len(s2) - len(s1) > EDIT_DISTANCE_THRESOLD: # 优化相当大的O(1)剪枝
        return False
    
    # O(n)统计字符，进一步剪掉一些不必要用n^2编辑距离的情况，实测625s优化到22s
    char_distance = 0
    d = {}
    for s in s1:
        d[s] = d.get(s, 0) + 1
    for s in s2:
        d[s] = d.get(s, 0) - 1
    positive = 0
    negative = 0
    for v in d.values():
        if v > 0:
            positive += v
        else:
            negative += - v
    char_distance = max(positive, negative)
    if char_distance > EDIT_DISTANCE_THRESOLD:
        return False
    # 编辑距离
    edit_distance = Levenshtein.distance(s1, s2)
    if edit_distance > EDIT_DISTANCE_THRESOLD:
        return False

    return True

def read_int(s: str) -> int:
    """从s的开头开始读一段连续的数字"""
    x = 0
    for c in s:
        if c.isdigit():
            x = x * 10 + int(c)
        else:
            return x
    return x


def extract_sentences_from_single_file(filetext: list[str]) -> str:
    """
    此函数会尝试把属于单个文件里的意外被换行符断开的句子恢复回来，
    并且过滤掉部分分页带来的冗余信息。

    返回的字符串是整个文件已经去除了分页信息的文本串
    为了保证规则准确性，输入应该按文本的每行事先做好strip

    Args:
        filetext (list[str]): 按页分开的，来自于同一个文件的文本串

    Returns:
        str: 按如上描述清洗后的文本串

    Example:
        >>> extract_sentences_from_single_file(["Everything seemed to be\nalright.", "Cause you gave\nme whispers of\nlove all night."])
        "Everything seemed to be alright.\nCause you gave me whispers of love all night."
    """

    # 通过连续的标号来认段落，这个搞法比较激进
    match_infos = [] # 存(int数字列表号, int文件行号) 这样的二元组
    line_marker = [] # 可以去掉换行的行数
    outputs = []

    flatten = list(itertools.chain(*[page.split('\n') for page in filetext]))
    for lineid, line in enumerate(flatten):
        m = re.match(LINENO_TOKEN, line)
        if m:
            g = m.group(0)
            match_infos.append((read_int(g), lineid))
        m = re.match(LINEDOT_TOKEN, line)
        if m:
            g = m.group(0)
            match_infos.append((-114514, lineid))
        
    for idx, (linecounter, lineid) in enumerate(match_infos[1:]):
        # 相邻两个识别头标号连续，或者都是点标号，则中间行的空格可以删掉（换成空格，将两段话拼在一起）
        prevcounter, previd = match_infos[idx]
        if linecounter == prevcounter + 1 or linecounter == prevcounter == -114514:
            line_marker.extend(range(previd, lineid - 1))

    line_marker.reverse() # 反转，使标号满足递减序。

    for lineid, line in enumerate(flatten):
        while line_marker and line_marker[-1] < lineid - 1:
            line_marker.pop()

        if line_marker and lineid - 1 == line_marker[-1]:
            line_marker.pop()
            outputs[-1] += ' ' + line
        else:
            outputs.append(line)

    # 根据观察，有至少三个因素影响一行结尾的回车能不能被删掉
    # 1. 次行首字母是不是小写字母
    # 2. 本行末尾字符是不是句号
    # 3. 本行是不是约有50个字符
    
    inputs: list[str] = outputs
    outputs = [inputs[0]]
    for lineid, nextline in enumerate(inputs[1:]):
        prevline = outputs[-1]
        if not nextline or not prevline: # 空行保留
            outputs.append(nextline)
            continue
        score = 0 # 正表示删换行，负表示保留换行
        if prevline[-1] == '.':
            score -= 44
        if prevline[-1] == ',':
            score += 81

        score += min(60, len(inputs[lineid])) - 32

        # 加入nltk的条件
        joined = outputs[-1] + ' ' + nextline
        tokenized_by_nltk = nltk.sent_tokenize(joined)
        if len(tokenized_by_nltk) == 1:
            score += 200
        elif len(tokenized_by_nltk) == 2:
            s1, s2 = tokenized_by_nltk
            if s1 == prevline and s2 == nextline:
                score -= 200
            # if is_likely(s1, outputs[-1]) and is_likely(s2, nextline):
                # score -= 200

        if nextline[0].islower():
            score += 83
        if re.match(LINENO_TOKEN, nextline):
            score -= 999
        if re.match(LINEDOT_TOKEN, nextline):
            score -= 999
        if re.match(SPEAKER_TOKEN, nextline):
            score -= 999


        if score > 0:
            outputs[-1] = joined
        else:
            outputs.append(nextline)
    # 将The meeting rose at ...后一直到The meeting was called to order...中间的部分去掉
    # inputs: list[str] = outputs
    # outputs = []
    # accept_line = True
    # for line in inputs:
    #     if accept_line:
    #         if re.search(ROSE_TOKEN, line) or re.search(ROSE_TOKEN2, line):
    #             accept_line = False
    #         outputs.append(line)
    #     else:
    #         if re.search(BEGIN_TOKEN, line) or re.search(BEGIN_TOKEN2, line):
    #             accept_line = True
    #             outputs.append(line)

    output = '\n'.join(outputs)
    output = re.sub(INFO_PAGE_TOKEN, '', output)
    output = re.sub(INFO_PAGE_TOKEN2, '', output)
    output = re.sub(INFO_PAGE_TOKEN3, '', output)
    return output

def filter_index_title(file_index_titles: list[str], page: str) -> str:
    """把正文里的目录索引条目拿掉
    
    Args:
        file_index_titles (list[str]): 预处理得到的目录页的索引条目
        page: 源文件一页的文本内容
        
    Returns:
        str: 去掉了疑似索引条目的行的此页文本
    """

    filtered_page = []
    unmatched = deque() # 索引条目可能一行写不下，用一个队列来处理
    for line in page.split('\n'):
        line = line.strip()
        matched = False
        for cid, file_index_title in enumerate(file_index_titles): # 每个都for保证出现过的都拿掉，is_likely加了剪枝还不算慢
            if is_likely(file_index_title, line):
                while unmatched:
                    filtered_page.append(unmatched.popleft())
                matched = True
                print(file_index_title, 'cid:', cid)
                filtered_page.append('\n====' + file_index_title +'====\n')
                break

            if unmatched:
                back_line = unmatched.pop() # 这个逻辑只处理最多两行文本
                if is_likely(back_line + ' ' + line, file_index_title):
                    while unmatched:
                        filtered_page.append(unmatched.popleft())
                    matched = True
                    print(file_index_title, 'cid:', cid)
                    filtered_page.append('\n====' + file_index_title +'====\n')
                    break
                unmatched.append(back_line)

        if not matched:
            unmatched.append(line)
            while len(unmatched) > 1: # 三行和以上的索引条目非常少见，所以这里写1，如果有需要可以改大，但上面的组合逻辑也要改
                filtered_page.append(unmatched.popleft())
    while unmatched:
        filtered_page.append(unmatched.popleft())
    return '\n'.join(filtered_page)




if __name__ == "__main__":
    now_timer = datetime.datetime.now()

    # dataset = load_dataset("ranWang/test_pdf_data", split='new')
    dataset = load_dataset("ranWang/UN_PDF_TEXT_DATA", split='randomTest')
    filtered_file = []
    def procedure(row):
        """main procedure for mapping"""
        filtered_pages = {}
        for lang in ['en', 'es', 'ru', 'fr']:
            lang_match_file_content = row[lang].split('\n----\n')
            file_index_titles = []
            for pageid, page in enumerate(lang_match_file_content):
                lines = []
                dot_count = 0
                pageline = page.split('\n')
                # 第一次过滤：分页符
                # if pageid == 0 and pageline:
                #     found = None
                #     for lineid, line in enumerate(pageline):
                #         if re.search(BEGIN_TOKEN, line) or re.search(BEGIN_TOKEN2, line): # 第一页中，在BEGIN_TOKEN之后的才是正文内容
                #             found = lineid
                #             break
                #     if found is not None:
                #         pageline = pageline[found:]

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
                    # if line:
                    lines.append(line)
                    if INDEX_TOKEN in line:
                        dot_count += 1
                
                if dot_count >= 4: # 有大于4行三个点的我们认为是目录页，用特别的处理方式或者先跳过
                    unmatched = []
                    other_buffer = []

                    for line in lines:
                        line = line.strip().replace('\ufffe', '-') # 瞪眼法得，\ufffe应该是连词符-
                        if INDEX_TOKEN in line:
                            title: str = line.split(INDEX_TOKEN, 1)[0].strip()
                            done = 0
                            # 预处理目录页，统计目录索引条目
                            # 有个特征是目录索引总是有一个带.的标号
                            for rid in range(len(unmatched), max(len(unmatched) - 4, -1), -1): # 最多处理连续4行的目录索引
                                concat_title = ' '.join([*unmatched[rid:], title])
                                dot_pos = concat_title.find('.')
                                if dot_pos != -1 and dot_pos < 6: # .出现的地方如果太靠后，我们不要
                                    file_index_titles.append(concat_title)
                                    done = 1
                                    break # 没找到就取title
                            if not done:
                                file_index_titles.append(title)
                            other_buffer.extend(unmatched)
                            unmatched.clear()
                        else:
                            unmatched.append(line)
                    other_buffer.extend(unmatched)
                    lang_match_file_content[pageid] = '\n'.join(other_buffer) # 拿掉目录页
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

    # op = []
    # def raw_dumper(row):
    #     op.append(row['en'])
    # dataset.map(raw_dumper)
    # with open('enraw.txt', 'w', encoding='utf-8') as rawfile:
    #     rawfile.write('\n<<<<<<<<<<\n'.join(op))
    
    # exit(0)
    dataset.map(procedure)
    processed_lang_files = {}

    for fi in filtered_file:
        for lang, content in fi.items():
            # for p, i in enumerate(content):
                # content[p] = eliminate_zh_breakline_mainwork(i)
            # dd.setdefault(lang, []).append('=========='.join(content))  # 页
            processed_lang_files.setdefault(lang, []).append(extract_sentences_from_single_file(content))  # 页

    for lang, content in processed_lang_files.items():
        with open(f'{lang}2.txt', 'w', encoding='utf-8') as f: # 将所有字符整合成一个输出到单文件中
            f.write('\n<<<<<<<<<<\n'.join(content))  # 文件分隔符


    print('running time:', (datetime.datetime.now() - now_timer).total_seconds())