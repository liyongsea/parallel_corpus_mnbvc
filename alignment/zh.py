import re
import datetime
from collections import deque
import string
import jieba

from datasets import load_dataset

# GLOBAL CONSTANTS
INDEX_TOKEN = '...'

NEAR_WORD = {}
CONTEXT_LENGTH = 1 # 超参
SCORE = [1] # 相关度赋分，保持长度与context_length一致
CONCAT_THRESOLD = 1

WHITESPACES = set(string.whitespace.replace('\n', ''))

PUNCTUATION_SET = set(string.punctuation)
PUNCTUATION_LANG = {
    'ar': {
        '،': '.',  # full stop
        '.': '.',  # full stop
        '!': '!',  # exclamation mark
        '؟': '?',  # question mark
        '،': ',',  # comma
        '؛': ';',  # semicolon
        ':': ':',  # colon
        '“': '"',  # left quotation marks
        '”': '"',  # right quotation marks
    },
    'zh': {
        '，': ',',
        '。': '.',
        '：': ':',
        '？': '?',
        '！': '!',
        '；': ';',
        '“': '"',
        '”': '"',
        '（': '(',
        '）': ')',
    },
}
for k, v in PUNCTUATION_LANG.items():
    PUNCTUATION_SET.update(v.keys())

DIGITS = {
    'ar': {
        '٠': 0,
        '١': 1,
        '٢': 2,
        '٣': 3,
        '٤': 4,
        '٥': 5,
        '٦': 6,
        '٧': 7,
        '٨': 8,
        '٩': 9,
    },
    'zh': {
        '零': 0,
        '一': 1,
        '二': 2,
        '三': 3,
        '四': 4,
        '五': 5,
        '六': 6,
        '七': 7,
        '八': 8,
        '九': 9,
        '十': 10,
    }
}

IS_ALL_THIS_LANG = {
    # \u0621-\u064A\u0660-\u0669
    # 除中文外，句子中都含空格
    'ar': re.compile(r'[\u0600-\u06ff ]+'),
    'zh': re.compile(r'[\u3006\u3007\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002ebef\U00030000-\U0003134f]+'),
    'fr': re.compile(r'[a-zA-ZÀ-Ÿ ]+'),
    'es': re.compile(r'[a-zA-ZáéíóúñÁÉÍÓÚÑüÜ ]+'),
    'ru': re.compile(r'[А-я,Ё,ё ]+'),
    'en': re.compile(r'[A-Za-z ]+'),
}

def filter_duplicated_whitespaces(src: str) -> str:
    """去噪：
        1. 如果换行符跟其它空格字符相连，这些字符替换成换行符
        2. 连续出现空格字符的，替换成其中一个空格字符"""
    buf = []
    newline = 0
    space = None
    for i in src:
        if i == '\n':
            newline += 1
        elif i in WHITESPACES:
            space = i
        else:
            if newline:
                buf.append('\n' * newline)
            elif space:
                buf.append(space)
            newline = 0
            space = None
            buf.append(i)
    if newline:
        buf.append('\n' * newline)
    elif space:
        buf.append(space)
    return ''.join(buf)

zh_no_concat_ruleset = [
    re.compile(r'摘要$'),
    re.compile(r'注$'),
    re.compile(r'导言$'),
    re.compile(r'^附件[一二三四五六七八九十].$'),
]
zh_no_concat_ruleset_s2 = [
    re.compile(r'^[0-9]+\.'),
]
zh_char = re.compile(r'[\u3006\u3007\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002ebef\U00030000-\U0003134f]')
def zh_rate(src: str) -> float: return len(re.findall(zh_char, src)) / len(src) if len(src) else 0
def eliminate_zh_space(src: str) -> str:
    """
    成句：
        对于中文，我们需要一个滑动窗口扫描每个字周围的字，
        由于双字词语最多，字越多的词语越少，我们需要一种函数来计算一个字和其他字的上下文相关度。
        我们仅删除字与字之间上下文相关度低的空格。或者这一步我们直接交给jieba

    """
    def merge(buf: list, segment: list, use_jieba=True):
        def can_concat_two_by_ruleset(s1: str, s2: str) -> bool:
            if (r2 := zh_rate(s2)) <= 0.01 or (r1 := zh_rate(s1)) <= 0.01:
                return False

            if not use_jieba:
                return True

            back_char = s1[-1]
            front_char = s2[0]
            if back_char == '。': # 特判标点符号
                return False
            elif back_char in ('，', '）', '、'):
                return True
            
            match_no_concat_ruleset = False
            for pat in zh_no_concat_ruleset:
                if re.search(pat, s2) or re.search(pat, s1):
                    match_no_concat_ruleset = True
                    break
            if match_no_concat_ruleset:
                return False
            for pat in zh_no_concat_ruleset_s2:
                if re.search(pat, s2):
                    match_no_concat_ruleset = True
                    break
            if match_no_concat_ruleset:
                return False

            conn = back_char + front_char
            result = jieba.cut(s1 + s2, cut_all=True, HMM=False, use_paddle=True) # 开不开HMM实际上没有影响
            can_eliminate = False
            for r in result:
                if conn in r:
                    can_eliminate = True
                    break
            if can_eliminate:
                return True
            if r1 > 0.667 and r2 > 0.667:
                return True
            return False


        for i in segment:
            buf.append(i)
            while len(buf) >= 2 and can_concat_two_by_ruleset(buf[-2], buf[-1]):
                bck = buf.pop()
                buf[-1] += bck


    linebuf = []
    for line in src.split('\n'):
        seg = line.split(' ')
        segbuf = []
        merge(segbuf, seg, False)
        linebuf.append(' '.join(segbuf))

    linebuf2 = []
    merge(linebuf2, linebuf)

    return '\n'.join(linebuf2)


def eliminate_zh_breakline_prework(src: str) -> None:
    """统计字的上下文衔接度，可以分为用jieba分词后按词统计，也可以直接按字统计
    """
    for line in src.split('\n'):
        # for cid, char in enumerate(line):
        #     if char in all_punctuation_set:
        #         continue
        #     char_stat = near_word.setdefault(char, {})
        #     for back_char_index in range(max(0, cid - context_length), cid):
        #         back_char = line[back_char_index]
        #         if back_char in all_punctuation_set:
        #             continue
        #         distance = cid - back_char_index
        #         char_stat[back_char] = char_stat.get(back_char, 0) + score[distance - 1]
        for zhseg in re.findall(IS_ALL_THIS_LANG['zh'], line):
            sp = jieba.lcut(zhseg, use_paddle=True)
            for wid, word in enumerate(sp):
                word_stat = NEAR_WORD.setdefault(word, {})
                for back_word_index in range(max(0, wid - CONTEXT_LENGTH), wid):
                    back_word = sp[back_word_index]
                    dist = wid - back_word_index
                    word_stat[back_word] = word_stat.get(back_word, 0) + SCORE[dist - 1]
                    
def eliminate_zh_breakline_mainwork(src: str) -> str:
    linebuf = []
    for line in src.split('\n'):
        if not linebuf or not re.search(IS_ALL_THIS_LANG['zh'], line) or not re.search(IS_ALL_THIS_LANG['zh'], linebuf[-1]):
            linebuf.append(line)
            continue
        s1 = linebuf[-1]
        s2 = line
        back_char = s1[-1]
        front_char = s2[0]
        # 不处理标点符号
        if back_char in PUNCTUATION_SET or front_char in PUNCTUATION_SET:
            linebuf.append(line)
            continue
        # 特判目录：阿拉伯数字和中文数字中的换行不处理
        if back_char in string.digits and front_char in DIGITS['zh'] or \
            back_char in DIGITS['zh'] and front_char in string.digits:
            linebuf.append(line)
            continue

        # 只看两个字接在一起
        # char_stat = near_word.setdefault(front_char, {}).get(back_char, 0)
        # if char_stat >= concat_thresold:
        #     linebuf[-1] += line
        # else:
        #     linebuf.append(line)

        back_word = jieba.lcut(s1, use_paddle=True)[-1]
        front_word = jieba.lcut(s2, use_paddle=True)[-1]
        word_stat = NEAR_WORD.setdefault(front_word, {}).get(back_word, 0)
        if word_stat >= CONCAT_THRESOLD:
            linebuf[-1] += line
        else:
            linebuf.append(line)

    return '\n'.join(linebuf)


def prework(row):
    for lang in ['zh']:
        pages = row[lang].split('\n----\n')
        for page in pages:
            eliminate_zh_breakline_prework(page)

def mainwork(row):
    for lang in ['zh']:
        pages = row[lang].split('\n----\n')
        for pageid, page in enumerate(pages):
            pages[pageid] = eliminate_zh_breakline_mainwork(page)
        with open('zh_eliminate_br.txt', 'a', encoding='utf-8') as f:
            f.write('\n----\n'.join(pages))
        
def dump_only(row):
    with open('zh_raw.txt', 'a', encoding='utf-8') as f:
        f.write(row['zh'])


if __name__ == "__main__":
    now_timer = datetime.datetime.now()
    dataset = load_dataset("ranWang/UN_PDF_TEXT_DATA", split='randomTest')
    
    # dataset.map(prework)
    # dataset.map(mainwork)
    dataset.map(dump_only)

    print('running time:', (datetime.datetime.now() - now_timer).total_seconds())