import re
from difflib import SequenceMatcher
from collections import namedtuple

import nltk

from text_segmenter import HardLineBreakDetector

CHINESE_NUM_DICT = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
                '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
CHINESE_UNIT_DICT = {'十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000}

ROMAN_VAL = {
    'I': 1,
    'V': 5,
    'X': 10,
    # 'L': 50,
}

def read_chinese(s: str) -> int:
    """读汉字"""
    num = 0
    unit = 1
    for digit in reversed(s):
        if digit in CHINESE_UNIT_DICT:
            if CHINESE_UNIT_DICT[digit] < unit:
                unit = CHINESE_UNIT_DICT[digit]
                num += unit
            else:
                unit = CHINESE_UNIT_DICT[digit]
        elif digit in CHINESE_NUM_DICT:
            num += CHINESE_NUM_DICT[digit] * unit
    return num

def read_int(s: str) -> int:
    """
    鲁棒地读入一个在字符串中的数字，避免报错。
    用于将以下三种样式的有序列表标号中解析出整数标号:
        1. 
        (1) 
        1)
    """
    x = 0
    for c in s:
        if c.isdigit():
            x = x * 10 + int(c)
    return x

def read_int_after_last_dot(s: str) -> int:
    """读最后一个.后的数字"""
    return int(s.strip().split('.')[-1])

def read_roman(s: str) -> int:
    """读罗马数字"""
    prev = 0
    curr = 0
    num = 0
    for i in reversed(s):
        if i in ROMAN_VAL:
            curr = ROMAN_VAL[i]
            if curr < prev:
                num -= curr
            else:
                num += curr
            prev = curr
    return num

def read_en_letter(s: str, begin_char='a') -> int:
    for i in s:
        o = ord(i) - ord(begin_char)
        if 0 <= o <= 25:
            return o
    return -2



class RuleBasedDetector(HardLineBreakDetector):
    LINE_NUMBERING_PATTERNS = [
        (re.compile(r'^\d{1,3}\. '), read_int), # 有序列表，阿拉伯数字，很少有上千的，不写+而是{1,3}，避免错误匹配一些年份 1.
        (re.compile(r'^• '), lambda x: None), # 无序列表 •
        (re.compile(r'^\d{1,2}\.\d{1,2} '), read_int_after_last_dot), # 第二类有序列表，阿拉伯数字带小标号 1.1
        (re.compile(r'^[IVX]{1,5}\. '), read_roman), # 有序列表，罗马数字 I.
        (re.compile(r'^\([a-z]\) '), read_en_letter), # 有序列表，括号小写英文 (a)
        (re.compile(r'^[a-z]\) '), read_en_letter), # 有序列表，半括号小写英文 a)
        (re.compile(r'^\d{1,3}\) '), read_int), # 有序列表，半括号数字 1)
        (re.compile(r'^\(\d{1,3}\) '), read_int), # 有序列表，全括号数字 (1)
        (re.compile(r'^[A-Z]\. '), lambda x: read_en_letter(x, 'A')), # 有序列表，大写英文标号 A. 
        (re.compile(r'^[一二三四五六七八九十]{1,3}、'), read_chinese), # 汉字有序列表 一、 
        (re.compile(r'^[一二三四五六七八九十]{1,3}\. '), read_chinese), # 汉字有序列表 一. 
        (re.compile(r'^\([一二三四五六七八九十]{1,3}\) '), read_chinese), # 第二类汉字有序列表 (一)
    ]
    MatchedLinenoInfo = namedtuple('MatchedLinenoInfo', ['rule_id', 'int_index'])

    @staticmethod
    def match_lineno_seg(line: str):
        """
        尝试跟列表规则组进行匹配，匹配不成功返回None，成功则返回一个MatchedLinenoInfo，line必须在传入前做strip
        int_index为None时，表示无序列表
        """
        for rule_id, (rule_pattern, process_func) in enumerate(RuleBasedDetector.LINE_NUMBERING_PATTERNS):
            m = re.match(rule_pattern, line)
            if m:
                return RuleBasedDetector.MatchedLinenoInfo(rule_id, process_func(m.group(0)))
        return None

    @staticmethod
    def score_by_nltk(prevline: str, nextline: str) -> int:
        # 加入nltk的条件，太长会严重影响性能，限制前一句最多100字符
        score = 0
        nextline2Bjoined = nextline[:100]
        joined = prevline[-100:] + ' ' + nextline2Bjoined
        tokenized_by_nltk = nltk.sent_tokenize(joined)

        if len(tokenized_by_nltk) == 1:
            score += 200
        elif len(tokenized_by_nltk) >= 2:
            # 遍历结果，找到一个ratio和第二句差不多的
            maxratio = 0
            for token in reversed(tokenized_by_nltk):
                sm = SequenceMatcher(lambda x: x==' ', token, nextline2Bjoined, autojunk=True) # 0.6->0 0.9->200
                if sm.real_quick_ratio() < maxratio or sm.quick_ratio() < maxratio:
                    continue
                maxratio = max(maxratio, sm.ratio())
            score -= (maxratio - 0.6) * 666.7 # * 200 / 0.3
        return score

    @staticmethod
    def score_simple(prevline: str, nextline: str) -> int:
        score = 0 # 正表示删换行，负表示保留换行
        if prevline[-1] in ('.', '?', '!', ';'): # 标点
            score -= 44
        if prevline[-1] == ',':
            score += 81

        score += min(60, len(prevline)) - 32 # 长度

        if nextline[0].islower(): # 小写
            score += 83
        return score

    @staticmethod
    def score_special(prevline: str, nextline: str) -> int:
        INF = 998244353
        if (not nextline) or (not prevline): # 当两行中一行是空行，则拼接
            return INF
        if RuleBasedDetector.match_lineno_seg(nextline): # 避免和lineno规则冲突
            return -INF
        return 0
    
    def detect(self, lines: list[str], **kwargs) -> list[bool]:
        """
        Detects the positions of hard line breaks in a list of lines based on rule-based heuristics.
        Firstly, we try to recognize line numbering patterns and mark the breakline between adjacent consequent line number or adjacent
        unordered line numberling patterns as soft line breaks.
        Secondly, we score the line breaks according to the length of previous line, the last punctuation of previous line, whether
        the first character of nextline is capitalized, and nltk tokenize result. These rules are written in `score_simple` and 
        `score_by_nltk` method, we assign a positive score in case the line break seems to be a soft line break, and negative otherwise.


        Args:
            lines (list[str]): A list of strings representing the lines of text.
            **kwargs: Additional keyword arguments (not used in this method).

        Returns:
            list[bool]: A list of boolean values indicating the positions of hard line breaks.
                        True indicates a hard line break should be present at the corresponding index,
                        while False indicates that the line break should be removed (lines should be merged).

        Note:
            The detection process is performed using rule-based heuristics that evaluate various factors,
            including line numbering patterns, punctuation, capitalization, line lengths, and linguistic analysis with the help of NLTK.
            The method assigns scores to each line break, and based on the scores, determines whether to keep or remove
            the line break. The line breaks are represented as boolean values in the returned list, where True indicates
            a hard line break and False indicates the line break should be removed.
        """
        is_hard_breaklines = [True] * (len(lines) - 1)
        match_infos = [] # 存(int数字列表号, int文件行号) 这样的二元组
        soft_linebreak_indice = [] # 可以去掉换行的行下标
        ## 行标号规则
        for lineid, line in enumerate(lines):
            m = self.match_lineno_seg(line)
            if m:
                match_infos.append((m.rule_id, m.int_index, lineid))

        for idx, (rule_id, linecounter, lineid) in enumerate(match_infos[1:]):
            # 相邻两个识别头标号连续，或者都是点标号，则中间行的\n可以删掉（换成空格，将两段话拼在一起）
            prev_rule_id, prevcounter, prev_lineid = match_infos[idx]
            if prev_rule_id == rule_id:
                if linecounter is None or linecounter == prevcounter + 1:
                    soft_linebreak_indice.extend(range(prev_lineid, lineid - 1))
        
        for lineid, nextline in enumerate(lines[1:]):
            # prevline = outputs[-1]
            prevline = lines[lineid]

            score = self.score_special(prevline, nextline) # 特判的运行优先级要高于一般规则（否则会Runtime Error）
            if score == 0:
                score += self.score_simple(prevline, nextline) # TODO: 单元测试
                score += self.score_by_nltk(prevline, nextline)

            if score > 0:
                soft_linebreak_indice.append(lineid)

        for i in soft_linebreak_indice:
            is_hard_breaklines[i] = False
        return is_hard_breaklines
