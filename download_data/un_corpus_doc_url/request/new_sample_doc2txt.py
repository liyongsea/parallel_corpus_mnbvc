"""
由于其它软件，如LibreOffice转doc为docx的乱码率太高
本步需要一台装有Windows的机器（虚拟机环境亦可，而且利用多核应该考虑多虚拟机并行执行），并且装有Office
采用COM方式调用WORD进行另存为

本脚本假设用户使用的是中文语言环境的WORD，否则需要改动一些pywinauto的字符串搜索依据

docx转文本需要系统上装有pandoc，并且写入环境变量，即，pandoc应该能够直接命令行调用
"""
from itertools import chain
from collections import Counter
import hashlib
import json
from queue import Empty
import os
import re
import multiprocessing as mp
import datetime
import shutil
import time
from typing import List, Union, Tuple
import unicodedata

import psutil
from pywinauto import Application # pywinauto
import win32com.client as win32
from win32com.client import constants
import datasets

import const

workdir = const.CONVERT_DOCX_CACHE_DIR
workdir.mkdir(exist_ok=True)
WINWORD_EXE = const.WINWORD_EXE

TEMP_DOC = str((workdir / 'temp.doc').absolute())
TEMP_DOC_LOCKFILE = str((workdir / '~$temp.doc').absolute())
TEMP_DOCX = str((workdir / 'temp.docx').absolute())
TEMP_DOCX_LOCKFILE = str((workdir / '~$temp.docx').absolute())


INPUT_DIR = const.DOWNLOAD_DOC_CACHE_DIR / 'doc'

ERR_DOCX_DIR = workdir / 'err'
ERR_DOCX_DIR.mkdir(exist_ok=True)

OUT_DOCX_DIR = workdir / 'docx'
OUT_DOCX_DIR.mkdir(exist_ok=True)

OUT_TEXT_DIR = const.CONVERT_TEXT_CACHE_DIR
OUT_TEXT_DIR.mkdir(exist_ok=True)

const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR.mkdir(exist_ok=True)

OUT_DATASET_DIR = const.CONVERT_DATASET_CACHE_DIR
FILEWISE_JSONL = const.FILEWISE_JSONL_OUTPUT_DIR

DOCX2TEXT_WORKERS = 8

ACCEPTED = 201
OK = 200
ERR = 500

def eliminate_top_window(app: Application):
    try:
        dialog = app.top_window()
        if dialog.texts() == ['显示修复']:
            dialog.close()
            return True

        for i in dialog.children():
            if "安全模式中启动" in ''.join(i.texts()):
                dialog.N.click()
                return True
            if "是否仍要打开它" in ''.join(i.texts()):
                dialog.Y.click()
                return True
    except RuntimeError as e:
        pass
        # traceback.print_exc()
    return False

def close_top_window(): # 很慢，所以超时才调用
    pids = scan_word()
    app = Application().connect(process=pids[-1])
    while eliminate_top_window(app):
        print('detected top window, closed')
        time.sleep(0.5)


def save_as_docx(qresult: mp.Queue, qtask: mp.Queue):
    """易错工作队列，随时需要处理被杀掉重启的情况"""
    last_time = datetime.datetime.now()
    word = win32.gencache.EnsureDispatch('Word.Application')
    absdoc = os.path.abspath(TEMP_DOC)
    absdocx = os.path.abspath(TEMP_DOCX)

    while 1:
        tid: str
        cont: bytes
        tid, cont = qtask.get()

        qresult.put((ACCEPTED, tid))

        if os.path.exists(TEMP_DOC_LOCKFILE):
            os.remove(TEMP_DOC_LOCKFILE)

        if os.path.exists(TEMP_DOCX_LOCKFILE):
            os.remove(TEMP_DOCX_LOCKFILE)

        try:
            with open(absdoc, 'wb') as f:
                f.write(cont)
                f.truncate()
        except PermissionError:
            print('detected permission error, kill word')
            time.sleep(3)
            kill_word()
            with open(absdoc, 'wb') as f:
                f.write(cont)
                f.truncate()
            word = win32.gencache.EnsureDispatch('Word.Application')

        if os.path.exists(absdocx):
            try:
                os.remove(absdocx)
            except PermissionError:
                print('detected permission error, kill word')
                time.sleep(3)
                kill_word()
                os.remove(absdocx)
                word = win32.gencache.EnsureDispatch('Word.Application')

        doc = None
        def post_error():
            nonlocal doc
            qresult.put((ERR, tid))
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'report error')
            if doc is not None:
                try:
                    doc.Close(False)
                except:
                    pass
                doc = None
        try:
            doc = word.Documents.Open(absdoc)
            doc.SaveAs(absdocx, FileFormat=constants.wdFormatXMLDocument)
            doc.Close(False)
            doc = None
            if os.stat(absdocx).st_size == 0:
                raise KeyError('空文件，视为错误')
            with open(absdocx, 'rb') as f:
                ok_res = f.read()
            qresult.put((OK, tid, ok_res))
            curr_time = datetime.datetime.now()
            print((curr_time - last_time).total_seconds(), 'submit done', tid)
        except win32.pywintypes.com_error as e:
            if 'RPC 服务器不可用。' in str(e):
                print('捕获【RPC 服务器不可用。】，重启word')
                kill_word()
                word = win32.gencache.EnsureDispatch('Word.Application')
                time.sleep(1)
            else:
                print(type(e), e)
                post_error()
        except Exception as e:
            print(type(e), e)
            post_error()
        last_time = datetime.datetime.now()
    qresult.put(None)

def scan_word():
    li = []
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            li.append(pid)
    return li

def kill_word():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if process.info['name'] == "WINWORD.EXE":
            pid = process.info['pid']
            p = psutil.Process(pid)
            p.kill()

def docx2txt_worker(q: mp.Queue):
    while 1:
        ipath, opath = q.get()
        if ipath is None:
            return
        if not os.path.exists(opath):
            pandoc_cmd = f"pandoc -i {ipath} -t plain -o {opath} --wrap=none --strip-comments"
            print('COMMAND:', pandoc_cmd)
            r = os.system(pandoc_cmd)
            # print('done', outp)
        else:
            pass
            # print('skip', outp)
    # print(r.read())

####
        
pat_comm_sp = re.compile(r'^\s*-+\s*$') # 找形如---------------------------------的表头和表尾
pat_sp = re.compile(r'^\s*-+[-\s]*\s*$') # 数据分割行--------- ------------------ ----------

def validate_line_length(lines: List[str], ref_spliter: str) -> bool:
    trailing_space_cnt = ref_spliter.find('-')
    trailing_spaces = ref_spliter[:trailing_space_cnt]
    for line in lines:
        sp_line = line.strip()
        if not sp_line: # 空行，跳过
            continue
        if line[:trailing_space_cnt] != trailing_spaces:
            return False
        # if line_width(line) > len(ref_spliter) + max(8, len(ref_spliter) * 0.1):
        if line_width(line) > len(ref_spliter):
            return False
    return True

def construct_out(mttb_map: List[Tuple[int, int, str]], lines: List[str], _log_filename: str, logfile) -> List[str]:
    out = []
    ptr = 0
    for l,r,text in mttb_map:
        with open(logfile, 'a', encoding='utf-8') as fdbg:
            fdbg.write(f'<{_log_filename}>\n'+ '\n'.join(lines[l:r+1]) + '\n\n')
        out.extend(lines[ptr:l])
        out.extend(text.split('\n'))
        ptr = r+1
    if ptr < len(lines):
        out.extend(lines[ptr:])
    return out


def four_line_table_replacer(lines: List[str], _log_filename: str) -> List[str]:
    """
    输入应该是一个用单个\n切开的字符串
    找四行表
    """
    match_line_idx = []

    for idx, line in enumerate(lines):
        if pat_comm_sp.match(line):
            match_line_idx.append(idx)
        # if pat_sp.match(line):
            # match_line_idx.append(idx)
    
    mttb_map = [] # (l, r, text)
    for p, lidx in enumerate(match_line_idx):
        if p <= 2: continue
        is_valid = True
        ref_line = lines[match_line_idx[p]]
        for j in range(3):
            if lines[match_line_idx[p-j-1]] != ref_line:
                is_valid = False
                break
            if not validate_line_length(lines[match_line_idx[p-j-1]: match_line_idx[p - j]], ref_line):
                is_valid = False
                break
        if is_valid:
            for j in range(2, -1, -1):
                l = match_line_idx[p - j - 1]
                r = match_line_idx[p - j]
                mttb_map.append((l, r, '\n\n'.join([''] + lines[l:r+1] + [''])))
    
    out = construct_out(mttb_map, lines, _log_filename, const.DBG_LOG_OUTPUT_FILE4)
    return out

table_spliter_pattern = re.compile(r'^\s*\+[-+=]+\+$')

def grid_table_detector(text: str, _log_filename: str) -> Union[None, List[str]]:
    """
    输入（一个段落）：
    +------+----------------------------------------------------+------+---+
    | 章次 |                                                    |      | 页 |
    |      |                                                    |      | 次 |
    +------+----------------------------------------------------+------+---+
    |   送 |                                                    |      | 5 |
    | 文函 |                                                    |      |   |
    | 和证 |                                                    |      |   |
    | 明函 |                                                    |      |   |
    +------+----------------------------------------------------+------+---+
    输出：
    ["章次  页次","  送文函和证明函  5"]
    
    pandoc 2023-2023_100-17=fr.docx -t plain --wrap=none -o output2.txt
    pandoc 2023-2023_104-21=zh.docx -t plain --wrap=none -o output.txt
    pandoc 2023-2023_104-21=zh.docx -t markdown --wrap=none -o output.md
    pandoc 2023-2023_104-21=zh.docx -t latex --wrap=none -o output.tex
    [TODO] 2023-2023_104-21=zh.txt 含有表中表
    [TODO] 2023-2023_100-17=fr.txt 含有表中表
    +--------------+-------------------------------------------------------+
    | 17.          | Dépenses au titre du budget consolidé consacrées au   |
    | Informations | secteur de l’enfance                                  |
    | réca         |                                                       |
    | pitulatives, | en milliards de roubles                               |
    | pour les     |                                                       |
    | trois        | +---------------------+--------+-------+--------+     |
    | dernières    | |                     | 2020   | 2021  | 2022   |     |
    | années, sur  | +---------------------+--------+-------+--------+     |
    | le budget    | | Produit intérieur   | 107    | 135   | 13 435 |     |
    | consacré au  | | brut (PIB)          |  658,1 | 295,0 |        |     |
    | secteur de   | |                     |        |       |        |     |
    | l’enfance et | | (en prix courants)  |        |       |        |     |
    | au secteur   | +---------------------+--------+-------+--------+     |
    | social, avec | | Dépenses au titre   | 42     | 47    | 55     |     |
    | indication   | | du budget consolidé |  503,0 | 072,7 |  182,0 |     |
    | du           | | de la Fédération de |        |       |        |     |
    | pourcentage  | | Russie et des fonds |        |       |        |     |
    | du budget    | | extrabudgétaires de |        |       |        |     |
    | national     | | l’État              |        |       |        |     |
    | total et du  | +---------------------+--------+-------+--------+     |
    | produit      | | Dépenses au titre   | 6      | 6     | 7      |     |
    | national     | | du budget consolidé |  190,7 | 303,1 |  813,8 |     |
    | brut que     | | consacrées          |        |       |        |     |
    | représente   | | au secteur de       |        |       |        |     |
    | chacun des   | | l’enfance           |        |       |        |     |
    | postes       | +---------------------+--------+-------+--------+     |
    | budgétaires  | | Pourcentage du PIB  | 5,8 %  | 4,7 % | 5,1 %  |     |
    | concernés    | +---------------------+--------+-------+--------+     |
    |              | | Pourcentage des     | 14,6 % | 1     | 14,2 % |     |
    |              | | dépenses totales au |        | 3,4 % |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé de la     |        |       |        |     |
    |              | | Fédération de       |        |       |        |     |
    |              | | Russie et des fonds |        |       |        |     |
    |              | | extrabudgétaires de |        |       |        |     |
    |              | | l’État              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | Dépenses au titre   | 1      | 1     | 2      |     |
    |              | | du budget fédéral   |  908,8 | 692,2 |  397,7 |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage du   | 1,8 %  | 1,3 % | 1,6 %  |     |
    |              | | PIB                 |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 4,5 %  | 3,6 % | 4,3 %  |     |
    |              | | dépenses totales au |        |       |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé de la     |        |       |        |     |
    |              | | Fédération de       |        |       |        |     |
    |              | | Russie et des fonds |        |       |        |     |
    |              | | extrabudgétaires de |        |       |        |     |
    |              | | l’État              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 30,8 % | 2     | 30,7 % |     |
    |              | | dépenses totales au |        | 6,8 % |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé           |        |       |        |     |
    |              | | consacrées au       |        |       |        |     |
    |              | | secteur             |        |       |        |     |
    |              | | de l’enfance        |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | Dépenses au titre   | 3      | 4     | 5      |     |
    |              | | des budgets         |  973,9 | 289,9 |  104,0 |     |
    |              | | consolidés          |        |       |        |     |
    |              | | des sujets de la    |        |       |        |     |
    |              | | Fédération de       |        |       |        |     |
    |              | | Russie              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage du   | 3,7 %  | 3,2 % | 3,3 %  |     |
    |              | | PIB                 |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 9,3 %  | 9,1 % | 9,2 %  |     |
    |              | | dépenses totales au |        |       |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé de la     |        |       |        |     |
    |              | | Fédération de       |        |       |        |     |
    |              | | Russie et des fonds |        |       |        |     |
    |              | | extrabudgétaires de |        |       |        |     |
    |              | | l’État              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 64,2 % | 6     | 65,3%  |     |
    |              | | dépenses totales au |        | 8,1 % |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé           |        |       |        |     |
    |              | | consacrées au       |        |       |        |     |
    |              | | secteur             |        |       |        |     |
    |              | | de l’enfance        |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | Dépenses au titre   | 308,0  | 321,0 | 312,1  |     |
    |              | | des fonds           |        |       |        |     |
    |              | | extrabudgétaires de |        |       |        |     |
    |              | | la Fédération de    |        |       |        |     |
    |              | | Russie              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage du   | 0,3%   | 0,2 % | 0,2 %  |     |
    |              | | PIB                 |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 0,7 %  | 0,7 % | 0,6 %  |     |
    |              | | dépenses totales au |        |       |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé de la     |        |       |        |     |
    |              | | Fédération de       |        |       |        |     |
    |              | | Russie et des fonds |        |       |        |     |
    |              | | extrabudgétaires de |        |       |        |     |
    |              | | l’État              |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    |              | | En pourcentage des  | 5,0 %  | 5,1 % | 4,0 %  |     |
    |              | | dépenses totales au |        |       |        |     |
    |              | | titre du budget     |        |       |        |     |
    |              | | consolidé           |        |       |        |     |
    |              | | consacrées au       |        |       |        |     |
    |              | | secteur de          |        |       |        |     |
    |              | | l’enfance           |        |       |        |     |
    |              | +---------------------+--------+-------+--------+     |
    +==============+=======================================================+
    """
    text = text.strip()
    if text == '': return None
    pivot_line_idx = 0
    table_column_count = None
    contents = []
    column_buffer = []
    plus_pos = []
    textlines = text.splitlines()
    for lineidx, line in enumerate(textlines):
        line = line.strip() # 一般来说不会有头尾空格，但是这里还是写上
        if table_spliter_pattern.match(line):
            if table_column_count is not None:
                table_width = line.count('+') - 1
                if table_width != table_column_count:
                    return None
                # 遇到+------+----------------------------------------------------+------+---+行，把column_buffer的东西按整行塞进contents里
                temp_row = []
                for idx, grid_content_list in enumerate(column_buffer):
                    replaced_paras, _, _, _ = table_replacer(grid_content_list, _log_filename)
                    # if "Стандарт 41 МСУГС «Финанс" in '\n'.join(replaced_paras):
                    #     print(1)
                    temp_row.extend(replaced_paras)
                    grid_content_list.clear()
                contents.append('\n\n'.join(temp_row))
            else:
                # 此处初始化 table_column_count，如果遇到之后和这个不等的，证明不是合法表格，直接return None
                pivot_line_idx = lineidx # 调试打印用
                table_column_count = line.count('+') - 1
                column_buffer = [[] for _ in range(table_column_count)]
                for cidx, char in enumerate(line):
                    if char == '+': plus_pos.append(cidx)
                
        elif table_column_count is not None:
            if line[0] == line[-1] == '|':
                unmatched_plus_pos = set(plus_pos)
                cptr = 0
                gbuf = []
                splited_grid_content = []
                for char in line:
                    if char == '|':
                        if cptr in unmatched_plus_pos:
                            splited_grid_content.append(''.join(gbuf))
                            gbuf.clear()
                            unmatched_plus_pos.discard(cptr)
                        else:
                            gbuf.append(char)
                    else:
                        gbuf.append(char)
                    cptr += char_wide(char)
                if unmatched_plus_pos:
                    print(unmatched_plus_pos, plus_pos)
                    print(len(textlines[pivot_line_idx]), len(line), line_width(line))
                    for cidx, char in enumerate(line):
                        print(cidx, char_wide(char), unicodedata.combining(char), unicodedata.east_asian_width(char), hex(ord(char)), ord(char), char.encode('utf-8'), char)
                    return None # 不是合法表格
                # splited_grid_content.pop()
                splited_grid_content.pop(0)
                # 列数相等，往temp_buf里对应的列桶塞东西
                for idx, column_text in enumerate(splited_grid_content):
                    # column_buffer[idx].append(column_text.removeprefix(' ').removesuffix(' ')) # 只删除头尾一个，避免把有意义的空格删了
                    column_buffer[idx].append(column_text.strip())
            else:
                return None
    if table_column_count is not None:
        with open(const.DBG_LOG_OUTPUT_FILE1, 'a', encoding='utf-8') as f:
            f.write(f'<{_log_filename}>\n'+ text + '\n\n') # 打下日志人肉看一下
    return (contents if table_column_count is not None else None)

ZERO_CHARS_ORD = { # east_asian_width 是 N，pandoc 3.1.1 和 3.4 都认这一部分阿拉伯字符的宽度是0
    # 77,

    # 西班牙语
    769,

    # 阿拉伯语
    # 1574,
    # 1600,
    # 1610,
    1611,
    1613,
    1614,
    1616,
    1615,
    1617,
    1618,

    # 8288, # 0x2060
    # 0x202c,
}

def char_wide(c, first_char=False): # 实际上暂时没有用到first_char
    codepoint = ord(c)
    # if codepoint in ZERO_CHARS_ORD:
        # return 0
    
    # 控制字符（0x0000 - 0x001F，0x007F - 0x009F）
    if codepoint <= 0x001F or (0x007F <= codepoint <= 0x009F):
        return 0
    
    # 软连字符（U+00AD）
    if codepoint == 0x00AD:
        return 0
    
    # 零宽度字符和格式控制字符
    if codepoint in (0x200C, 0x200D, 0xFE0E, 0xFE0F):
        return 0

    # 添加对 Unicode 分类为 'Cf' 的字符的处理
    if unicodedata.category(c) == 'Cf':
        return 0
    
    # 组合字符
    if unicodedata.combining(c):
        return 1 if first_char else 0
    
    # East Asian Wide or Full-width characters
    eaw = unicodedata.east_asian_width(c)
    if eaw in ('W', 'F'):
        return 2
    
    # 默认情况，宽度为 1
    return 1

# def char_wide(char): # 字宽，观察发现输出中文要占2个字符
    # if ord(char) in ARABIC_ZERO_CHARS_ORD:
    #     return 0
    # return 2 if unicodedata.east_asian_width(char) in ['W', 'F'] else 1

def line_width(line): # 行宽，中文占2个字符
    return sum([char_wide(c) for c in line])

def parse_spliter_line(spliter_line_text: str) -> List[int]:
    col_widths = []
    lborder = -1
    rborder = -1 # 左闭右闭区间下标
    for cidx, c in enumerate(spliter_line_text): # 遍历分割行的每一个字符，统计列宽
        if c == '-':
            rborder = cidx
            if lborder == -1:
                lborder = cidx
        else: # 空格，c == ' '，正则保证的
            if lborder != -1:
                col_widths.append((lborder, rborder)) # 记录列宽
                lborder = -1
                rborder = -1
    if lborder != -1:
        col_widths.append((lborder, rborder)) # 记录列宽
    return col_widths

def multiline_table_detector(lines: List[str], _log_filename: str) -> Union[None, List[str]]:
    """
    找出形如这样的表：
    -----------------------------------------------------------------------------------------------------------------
    公共部门会计准则分类           开发署金融资产类型
    ------------------------------ ----------------------------------------------------------------------------------
                                    

    持有至到期                     除离职后健康保险和服务终了投资之外的投资

    可供出售                       离职后健康保险和服务终了投资

    贷款和应收款                   现金及现金等价物、应收款(非交换交易和其他)、预付款(如给员工的预付款)、对政府贷款

    以公允价值计量且其变动计入     衍生工具资产
    盈余或赤字                     
    -----------------------------------------------------------------------------------------------------------------
    """
    header_ptr = -1 # 当前匹配中了表头，算一下表头多少个-号
    header_ptr_2nd = -1

    mttb_map = [] # (l, r, text)
    
    for idx,line in enumerate(lines):
        if not pat_comm_sp.match(line): continue
        if header_ptr < 0:
            header_ptr = idx
            header_ptr_2nd = -1
        elif lines[header_ptr] != line:
            header_ptr = idx
            header_ptr_2nd = -1
        else: # 如果前后两个---------相等，说明这可能是一个多行表
            spliter_idx = -1
            converted_text_buf = []
            for line_idx in range(header_ptr+1, idx): # 找一下有没有数据分割行--------- ------------------ ----------
                if len(lines[line_idx]) == len(line) and pat_sp.match(lines[line_idx]): # 找到分割行了，说明这是一个多行表
                    # ！注意！ 此处写入各列列宽，变量在外面没有定义
                    col_widths = parse_spliter_line(lines[line_idx])
                    spliter_idx = line_idx
                    break
            if spliter_idx == -1:
                # 没找到分割行，这部分应该不是表格，但不排除下一批次是
                # 实际上它还有4个 ----- 的case，参见2023-2023_1-87=en.txt，这个如果要处理要重构现在这个流程，做成类似行染色的做法，可靠性会更低
                # 实际上对于单列表，处不处理都行
                # if header_ptr_2nd == -1:
                #     header_ptr_2nd = idx
                # else:
                #     header_ptr = idx
                header_ptr = idx
            else:
                trailing_space_cnt = line.find('-')
                trailing_spaces = line[:trailing_space_cnt]
                assert trailing_spaces.count(' ') == trailing_space_cnt
                col_bufs = [[] for _ in col_widths]
                if not validate_line_length(lines[header_ptr+1:spliter_idx], line) or \
                    not validate_line_length(lines[spliter_idx+1:idx], line):
                    header_ptr = idx
                    header_ptr_2nd = -1
                    converted_text_buf.clear()
                    continue

                for line_idx in range(header_ptr+1, idx): # 对每一行做更严格的校验
                    cur_line = lines[line_idx]
                    stripped_line = cur_line.strip()
                    if not stripped_line or line_idx == spliter_idx:
                        # 处理col_bufs
                        temp_row = []
                        for cidx, col_list in enumerate(col_bufs):
                            temp_row.append(' '.join(col_list).strip())
                            col_list.clear()
                        if temp_row and not all([x == '' for x in temp_row]): # 如果这一行不是空行，则加入结果集
                            row_text = '  '.join(temp_row)
                            converted_text_buf.append(row_text)
                    else: # 有内容
                        coffset = 0
                        for cidx, col_list in enumerate(col_bufs):
                            col_list.append([])
                        for c in cur_line:
                            slot = -1
                            for col_idx, seg in enumerate(col_widths):
                                # if seg[0] <= coffset <= seg[1]:
                                if seg[0] <= coffset: # 存在越界情况，这里只拿左端点判断了
                                    slot = col_idx
                                    break
                            coffset += char_wide(c)
                            if slot == -1: continue
                            col_bufs[slot][-1].append(c)
                        for cidx, col_list in enumerate(col_bufs):
                            col_list[-1] = ''.join(col_list[-1]).strip()
                    # 末尾处理
                    temp_row = []
                    for cidx, col_list in enumerate(col_bufs):
                        temp_row.append(' '.join(col_list).strip())
                        col_list.clear()
                    if temp_row and not all([x == '' for x in temp_row]): # 如果这一行不是空行，则加入结果集
                        row_text = '  '.join(temp_row)
                        converted_text_buf.append(row_text)
                mttb_map.append((header_ptr, idx, '\n\n'.join([''] + converted_text_buf + [''])))
                converted_text_buf.clear()
                header_ptr = -1
                header_ptr_2nd = -1
    if not mttb_map: return None
    return construct_out(mttb_map, lines, _log_filename, const.DBG_LOG_OUTPUT_FILE2)


def multiline_table_without_spliter_detector(lines: List[str], _log_filename: str) -> Union[None, List[str]]:
    """
    还有这种形式的表:
    -------------------- ------------------------------------------------------
    主要事实             

    170                  开发署开展业务的国家和地区数

    7.74亿美元           执行局核准的2022年经常资源预算。[2]
                        其他资源尽管计入财务报表，但不属于执行局核定预算范围

    53.2亿美元           收入总额

    53.5亿美元           费用总额

    148.2亿美元          资产总额

    30.7亿美元           负债总额
    -------------------- ------------------------------------------------------
    """
    header_ptr = -1 # 当前匹配中了表头，算一下表头多少个-号
    mttb_map = [] # (l, r, text)
    
    for idx,line in enumerate(lines):
        if not pat_sp.match(line): continue
        if header_ptr < 0:
            header_ptr = idx
        elif lines[header_ptr] != line:
            header_ptr = idx
        else: # 如果前后两个---------相等，说明这可能是一个多行表
            col_widths = parse_spliter_line(line)
            converted_text_buf = []

            trailing_space_cnt = line.find('-')
            trailing_spaces = line[:trailing_space_cnt]
            assert trailing_spaces.count(' ') == trailing_space_cnt
            if not validate_line_length(lines[header_ptr+1:idx], line):
                header_ptr = idx
                converted_text_buf.clear()
                continue
            col_bufs = [[] for _ in col_widths]

            for line_idx in range(header_ptr+1, idx): # 对每一行做更严格的校验
                cur_line = lines[line_idx]
                stripped_line = cur_line.strip()
                if not stripped_line:
                    # 处理col_bufs
                    temp_row = []
                    for cidx, col_list in enumerate(col_bufs):
                        temp_row.append(' '.join(col_list).strip())
                        col_list.clear()
                    if temp_row and not all([x == '' for x in temp_row]): # 如果这一行不是空行，则加入结果集
                        row_text = '  '.join(temp_row)
                        converted_text_buf.append(row_text)
                else: # 有内容
                    coffset = 0
                    for cidx, col_list in enumerate(col_bufs):
                        col_list.append([])
                    for c in cur_line:
                        slot = -1
                        for col_idx, seg in enumerate(col_widths):
                            if seg[0] <= coffset:
                                slot = col_idx
                                break
                        coffset += char_wide(c)
                        if slot == -1: continue
                        col_bufs[slot][-1].append(c)
                    for cidx, col_list in enumerate(col_bufs):
                        col_list[-1] = ''.join(col_list[-1]).strip()
                # 末尾处理
                temp_row = []
                for cidx, col_list in enumerate(col_bufs):
                    temp_row.append(' '.join(col_list).strip())
                    col_list.clear()
                if temp_row and not all([x == '' for x in temp_row]): # 如果这一行不是空行，则加入结果集
                    row_text = '  '.join(temp_row)
                    converted_text_buf.append(row_text)
            mttb_map.append((header_ptr, idx, '\n\n'.join([''] + converted_text_buf + [''])))
            converted_text_buf.clear()
            header_ptr = -1
    if not mttb_map: return None
    return construct_out(mttb_map, lines, _log_filename, const.DBG_LOG_OUTPUT_FILE3)

# lines: 按\n切开的文本
def table_replacer(lines: List[str], _log_filename: str) -> Tuple[List[str], bool, bool, bool]:
    # lines = four_line_table_replacer(lines, _log_filename)
    is_mttb = False
    flatten_mttb_text = multiline_table_detector(lines, _log_filename)
    if flatten_mttb_text is not None:
        is_mttb = True
        lines = flatten_mttb_text
        # print('found mttb',i)
    is_mttb_wos = False
    flatten_mttb_wos_text = multiline_table_without_spliter_detector(lines, i)
    if flatten_mttb_wos_text is not None:
        is_mttb_wos = True
        lines = flatten_mttb_wos_text
        # print('found mttb wos',i)
    real_file_paras = []
    is_grid = False
    for pidx, para in enumerate('\n'.join(lines).split('\n\n')):
        # if para.find("21. Влияние этих стандартов")!=-1:
            # print(pidx)
        detect_res = grid_table_detector(para, i)
        if detect_res is not None:
            is_grid = True
            # if i not in contains_grid_tb_files:
                # contains_grid_tb_files.add(i)
                # print('found grid',i)
            real_file_paras.extend(detect_res)
        else:
            real_file_paras.append(para)
    
    return real_file_paras, is_grid, is_mttb, is_mttb_wos

if __name__ == '__main__':
    kill_word()
    mgr = mp.Manager()
    q = mgr.Queue()
    qtask = mgr.Queue()

    close_window_tries = 0

    todo = set() # doc另存为docx的任务表，会自动从上一次没完成的任务继续
    for rec in os.listdir(INPUT_DIR):
        if rec.startswith('~$'):
            continue
        todo.add(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(OUT_DOCX_DIR):
        todo.remove(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(ERR_DOCX_DIR):
        todo.remove(re.sub(r'\.\w+$', '', rec))

    for rec in os.listdir(INPUT_DIR):
        fn = INPUT_DIR / rec
        if re.sub(r'\.\w+$', '', rec) not in todo:
            continue
        with open(fn, 'rb') as f:
            cont = f.read()
        print(fn)
        qtask.put((rec, cont))
    print(len(todo))
    p = mp.Process(target=save_as_docx, args=(q, qtask))
    p.start()
    prvtask = None

    print('[save_as_docx] qsiz:', qtask.qsize())
    print('[save_as_docx] todo len:', len(todo))
    while len(todo) > 0:
        try:
            status, *args = q.get(timeout=40)
            close_window_tries = 0
            if status == ACCEPTED:
                prvtask = args[0]
            elif status == OK:
                tout = OUT_DOCX_DIR / re.sub(r'\.\w+$', '.docx', args[0])
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
                tout.parent.mkdir(exist_ok=True)
                with open(tout, 'wb') as f:
                    f.write(args[1])
            elif status == ERR:
                terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', args[0])
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
                terr.parent.mkdir(exist_ok=True)
                with open(terr, 'w') as f:
                    pass
        except Empty:
            if close_window_tries < 2:
                close_window_tries += 1
                close_top_window()
                continue
            p.kill()
            p.join()
            kill_word()
            if prvtask is not None:
                terr = ERR_DOCX_DIR / re.sub(r'\.\w+$', '.log', prvtask)
                todo.discard(re.sub(r'\.\w+$', '', args[0]))
                terr.parent.mkdir(exist_ok=True)
                with open(terr, 'w') as f:
                    pass
                print('timeout submit error:', prvtask)
            else:
                print('catch error without report:', prvtask)
            p = mp.Process(target=save_as_docx, args=(q, qtask))
            p.start()

    p.kill()
    p.join()
    kill_word()

    # 转docx完毕，docx转txt开始
    qd2t = mp.Queue()
    ps = [
        mp.Process(target=docx2txt_worker, args=(qd2t,)) for _ in range(DOCX2TEXT_WORKERS)
    ]

    for x in ps:
        x.start()

    docx2txt_task_cnt = 0
    for rec in os.listdir(OUT_DOCX_DIR):
        if not (OUT_TEXT_DIR / re.sub(r'\.\w+$', '.txt', rec)).exists(): # 跳过已经做过了的任务
            docx2txt_task_cnt += 1
            qd2t.put((
                (OUT_DOCX_DIR / rec).absolute(),
                (OUT_TEXT_DIR / re.sub(r'\.\w+$', '.txt', rec)).absolute(),
            ))
    print('[docx2txt] task_count:', docx2txt_task_cnt)
    for x in ps:
        qd2t.put((None, None))
    
    for x in ps:
        x.join()


    filename_mapping = {
        'es': 'es',
        'ru': 'ru',
        'fr': 'fr',
        'de': 'de',
        'ar': 'ar',
        'zh': 'zh',
        'en': 'en',
        'ot': 'de', # other先默认是德语
    }

    try: os.remove(const.DBG_LOG_OUTPUT_FILE4)
    except: pass
    try: os.remove(const.DBG_LOG_OUTPUT_FILE3)
    except: pass
    try: os.remove(const.DBG_LOG_OUTPUT_FILE2)
    except: pass
    try: os.remove(const.DBG_LOG_OUTPUT_FILE1)
    except: pass

    contains_grid_tb_files = set()
    contains_mttb_files = set()
    contains_mttb_wos_files = set()
    all_file_ctr = 0

    for i in list(os.listdir(OUT_TEXT_DIR)):
    # for i in ['2023-2023_103-65=en.txt']:
    # for i in ['2023-2023_1-13=ru.txt']:
    # for i in ['2023-2023_100-17=fr.txt']:
        if i.endswith('.t2'):
            os.remove(OUT_TEXT_DIR / i)
            continue
        text_path = OUT_TEXT_DIR / i
        print('scanning',i)
        all_file_ctr += 1
        with open(text_path, 'r', encoding='utf-8') as f:
            file_raw = f.read()
        # 换掉U+200E字符，会影响表格长度校验
        # print("u+200E count:", file_raw.count('\u200e'))
        file_raw = file_raw.replace('\u200e', '').replace('\u200f', '')
        # 还要换掉\xad,不然认表格会炸
        file_raw = file_raw.replace('\xad', '')
        real_file_paras, is_grid, is_mttb, is_mttb_wos = table_replacer(file_raw.split('\n'), i) # 表格替换
        if is_grid: contains_grid_tb_files.add(i)
        if is_mttb: contains_mttb_files.add(i)
        if is_mttb_wos: contains_mttb_wos_files.add(i)
        
        with open(const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR / i, 'w', encoding='utf-8') as f:
        # with open(OUT_TEXT_DIR / f"{i}.t2", 'w', encoding='utf-8') as f: # 仅调试用：放同目录下方便比对
            f.write('\n\n'.join((x.strip() for x in real_file_paras if x.strip())))

    print(f'all:{all_file_ctr}, mttb:{len(contains_mttb_files)}, grid_tb:{len(contains_grid_tb_files)}, mtwos:{len(contains_mttb_wos_files)}')
    # exit(0)
    def dataset_generator():
        json_info2langs = {}
        json_info2ds_row = {}
        for rec in os.listdir(const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR): # sample: 2023-2023_1-8=ar.txt
            json_info, lang = rec.removesuffix('.txt').split('=')
            json_info2langs.setdefault(json_info, set()).add(lang)
        
            json_fn, idx = json_info.rsplit('-', 1)
            with open(const.DOWNLOAD_FILELIST_CACHE_DIR / f'{json_fn}.json', 'r') as f:
                data = json.load(f)
                json_info2ds_row[json_info] = {
                    'ar': '',
                    'zh': '',
                    'en': '',
                    'fr': '',
                    'ru': '',
                    'es': '',
                    'de': '',
                    'inner_id': json_info, # 本批脚本自用id
                    'published': data['docs'][int(idx)]['Publication Date'],
                    'symbol': data['docs'][int(idx)]['symbol'],
                    'record': data['docs'][int(idx)]['id'],
                }
        print('SCANNING DIR:', const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR)
        for rec in os.listdir(const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR): # sample: 2023-2023_1-8=ar.txt
            json_info, lang = rec.removesuffix('.txt').split('=')
            json_info2langs[json_info].discard(lang)

            lang = filename_mapping[lang]
            with open(const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR / rec, 'r', encoding='utf-8') as f:
                print("READING", const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR / rec)
                fcontent = f.read()
                # if fcontent.count('\u200e') > 0:
                    # print(f"{rec} has zero-width non-joiner", fcontent.count('\u200e'),const.CONVERT_TEXT_FLATTEN_TABLE_CACHE_DIR / rec)
                    # raise NameError(f"{rec} has zero-width non-joiner", fcontent.count('\u200e'))
                    # exit(1)
                json_info2ds_row[json_info][lang] = fcontent

            if not json_info2langs[json_info]: # 
                yield json_info2ds_row.pop(json_info)
    
    dataset = datasets.Dataset.from_generator(dataset_generator)

    shutil.rmtree(OUT_DATASET_DIR, ignore_errors=True)
    dataset.save_to_disk(OUT_DATASET_DIR)

    def save_jsonl(row):
        fn = row['record']
        template = {
            '文件名': fn,
            '是否待查文件': False,
            '是否重复文件': False,
            '段落数': 1,
            '去重段落数': 0,
            '低质量段落数': 0,
            '段落': {
                '行号': 1,
                '是否重复': False,
                '是否跨文件重复': False,
                'zh_text_md5': hashlib.md5(row['zh'].encode('utf-8')).hexdigest(),
                'zh_text': row['zh'],
                'en_text': row['en'],
                'ar_text': row['ar'],
                'nl_text': '',
                'de_text': row['de'],
                'eo_text': '',
                'fr_text': row['fr'],
                'he_text': '',
                'it_text': '',
                'ja_text': '',
                'pt_text': '',
                'ru_text': row['ru'],
                'es_text': row['es'],
                'sv_text': '',
                'ko_text': '',
                'th_text': '',
                'other1_text': '',
                'other2_text': '',
                '拓展字段': r'{}',
                '时间': datetime.datetime.now().strftime("%Y%m%d")
            },
            '拓展字段': r'{}',
            '时间': datetime.datetime.now().strftime("%Y%m%d")
        }
        with FILEWISE_JSONL.open('a', encoding='utf-8') as f:
            f.write(json.dumps(template, ensure_ascii=False) + '\n')
    if FILEWISE_JSONL.exists():
        os.remove(FILEWISE_JSONL)
        # FILEWISE_JSONL.unlink()
    dataset.map(save_jsonl)