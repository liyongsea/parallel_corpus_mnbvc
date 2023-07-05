from collections import namedtuple
from datetime import datetime
import traceback
from typing import Tuple
import itertools
from pathlib import Path
import json
import re
from difflib import SequenceMatcher

import tiktoken
import pylcs

from text_segmenter import HardLineBreakDetector
import utils

LCSTokenInfo = namedtuple('LCSTokenInfo', ('token', 'length', 'source_line_id'))

class GPTBatchSequentialDetector(HardLineBreakDetector):
    LEADING_NOISE_SCAN_LINE_LIMIT = 12 # 

    def __init__(self, name, cache_dir, token_limit=500, use_proxy=False, re_ask_times=3, ignore_leading_noise_lines=True):
        super().__init__(name)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        self.token_limit = token_limit
        self.use_proxy = use_proxy
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.re_ask_times = re_ask_times
        self.ignore_leading = ignore_leading_noise_lines

    @staticmethod
    def clearup_output(raw_output_from_chatgpt: str) -> list[str]:
        """
        处理返回的数据中包含多个空行（整行为空或仅含空字符）的情况，保证文本以\n分开之后不会出现空行
        返回原文本以\n切分后的列表
        """
        return re.sub(r'\n\s*', '\n', raw_output_from_chatgpt, flags=re.M).strip().splitlines()

    @staticmethod
    def tokenize_by_space_splited_word(input_lines: list[str], output_lines: list[str], offset=0) -> Tuple[list[LCSTokenInfo], list[LCSTokenInfo]]:
        """
        Encode `input_lines` and `output_lines` by space splited word as utf-8 single character, to speedup LCS procedure.
        
        Args:
            input_lines (list[str]): The list of lines from source text.
            output_lines (list[str]): The list of lines from the processed text.
            offset (int): utf-8 encoding begin offset for tokenizing.

        Returns:
            list[list[str]]: The batched lines.
        """
        word_dict = {}
        input_tokens_info = []
        output_tokens_info = []
        for input_line_id, input_line in enumerate(input_lines):
            for word in input_line.split():
                input_tokens_info.append(LCSTokenInfo(
                    chr(offset + word_dict.setdefault(word, len(word_dict))),
                    len(word),
                    input_line_id,
                    ))
        
        for output_line_id, output_line in enumerate(output_lines):
            for word in output_line.split():
                if word in word_dict: # 为子序列写的优化
                    output_tokens_info.append(LCSTokenInfo(
                        chr(offset + word_dict[word]),
                        len(word),
                        output_line_id,
                        ))
        return input_tokens_info, output_tokens_info

    @staticmethod
    def lcs_sequence_alignment(input_lines: list[str] , output_lines: list[str]) -> Tuple[dict[int, Tuple[int, int]], list[float], list[float]]:
        """
        将input_lines每行的单词用最长公共子序列对齐到output_lines每行的单词中。
        这个函数同时还会计算每行输入输出的单词命中率（此行的已匹配单词总长度/此行单词总长度）。
        
        Args:
            input_lines(str): 输入的一段话
            output_lines(str): chatgpt给对齐好的一段话
        
        Returns:
            align_map(dict[int, set[int]]): 输出行号对应输入的行号
            input_hit_rate(list[float]): 输入每行的匹配率（匹配的单词总长度/本行总单词总长度）
            output_hit_rate(list[float]): 输出每行的匹配率

        Example:
            输入:
                行号    input_lines
                0       1. it's a beautiful
                1       day outside.
                2       2. birds are singing,
                3       flowers are
                4       blooming...
                5       3. on days like these,
                6       kids like you...
                7       4. Should
                8       be
                9       burning
                10      in hell.

                行号    output_lines
                0       1. it's a beautiful day outside.
                1       2. birds are singing, flowers are blooming...
                2       3. on days like these, kids like you...
                3       4. Should be burning in hell.

            输出:
                align_map: {0: {0, 1}, 1: {2, 3, 4}, 2: {5, 6}, 3: {7, 8, 9, 10}}
                input_hit_rate: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] (全部命中)
                output_hit_rate: [1.0, 1.0, 1.0, 1.0] (全部命中)

        """
        # 考虑到运行效率，我们切分粒度采用空格隔开的单词而不是字母
        input_tokens_info, output_tokens_info = GPTBatchSequentialDetector.tokenize_by_space_splited_word(input_lines, output_lines)

        # 算输入输出的每行的单词命中率，即：匹配的单词总字符数 / 单词总字符数
        input_hit_rate = [0 for _ in input_lines] 
        output_hit_rate = [0 for _ in output_lines]

        input_tokens = ''.join(map(lambda x: x[0], input_tokens_info))
        output_tokens = ''.join(map(lambda x: x[0], output_tokens_info))
        aligned_indexes = pylcs.lcs_sequence_idx(input_tokens, output_tokens) # 输入的每个单词的下标对应于输出的每个单词下标，不为-1失配的情况下保证是递增的
        align_map = {}
        for input_token_index, output_token_index in enumerate(aligned_indexes):
            if output_token_index != -1:
                _, input_word_length, input_lineid = input_tokens_info[input_token_index]
                _, output_word_length, output_lineid = output_tokens_info[output_token_index]
                # 每个output_lineid对应一段input_lineid的区间，是一个2元素的列表[l, r]，代表本段包含了源文本中行号区间为[l, r]之间的行
                align_map.setdefault(output_lineid, [input_lineid, input_lineid])[1] = input_lineid # 左区间(即[0])用setdefault填入，右区间由[1] = input_lineid更新
                input_hit_rate[input_lineid] += input_word_length
                output_hit_rate[output_lineid] += output_word_length

        return align_map, input_hit_rate, output_hit_rate

    @staticmethod
    def align_and_drop_bad_alignment(input_lines: list[str] | str, output_lines: list[str] | str, drop_last_paragraph=True) -> dict[int, Tuple[int, int]]:
        """
        这个函数是lcs_sequence_alignment的封装，用于丢掉其对齐得*不好*的段落。
        具体来说：
            1. 在输出段落output_lines不止一段时，这个函数会丢掉output_lines中指定的成段段落的最后一段
            2. 丢掉output_lines中命中率(output_hit_rate)低于0.6的段落

        在执行规则2后，align_map可能会变为空，这种情况下应该视为GPT的返回对于成段任务没有意义，并在外层函数中特殊处理。

        Args:
            input_lines(str): 输入的一段话，需要保证不存在空行
            output_lines(str): chatgpt给对齐好的一段话，需要保证不存在空行
            drop_last_paragraph(bool): 是否丢掉成出来的最后一个大段，如果当前batch已经跑完剩余的所有文本，则不需要丢掉最后一个大段
        
        Returns:
            align_map(dict[int, Tuple[int, int]]): 输出行号对应输入的行号，可以参见函数lcs_sequence_alignment的样例

        ========= 以下是整理出来的一些实际错误，这些错误直接指导了本函数的规则设计

        目前已知，GPT在一些极端情况，如，输入了文件末尾的噪声行或是乱码行，会道歉，如：
            I'm sorry, it seems like the input text is corrupted and does not make sense. Would you 
        please provide a proper input text for me to solve the breakline elimination problem?

        或者遇到空输入：
            Sorry, I cannot provide an output without the input. Please provide the text.
        
        罕见的情况下它会复读：
            The input text has unexpected line breaks that split paragraphs in some sections. These 
        breaklines will be removed and adjacent lines will be joined if they form a meaningful paragraph. 
        This will be done for sections 1, 2, 3, 5, 6, 9, and section D. Pagination and indexing information 
        should not be joined with adjacent paragraphs.\n\n1. Assuming you would...（接下来才是正文）
        """
        if isinstance(input_lines, str):
            input_lines = input_lines.splitlines()
        if isinstance(output_lines, str):
            output_lines = output_lines.splitlines()

        align_map, input_hit_rate, output_hit_rate = GPTBatchSequentialDetector.lcs_sequence_alignment(input_lines, output_lines)
        for p, i in enumerate(input_hit_rate):
            input_hit_rate[p] /= sum(map(len, input_lines[p].split()))
        for p, i in enumerate(output_hit_rate):
            output_hit_rate[p] /= sum(map(len, output_lines[p].split()))

        if len(align_map) > 1 and drop_last_paragraph:
            align_map.pop(max(align_map.keys())) # 干掉最后一个大段，避免不完全成段

        # 为了防止加段现象影响准确率，匹配率低于60%的output_line_id直接扔掉
        for p, i in enumerate(output_hit_rate):
            if i < 0.6:
                if p in align_map:
                    align_map.pop(p)
        
        return align_map

    @staticmethod
    def construct_segment_list_from_output_text(raw_text: str, output_text: str, use_identical_mapping_when_failure=False, drop_last_paragraph=True) -> list[Tuple[int, int]]:
        """
        从输出中构造段落区间表。
        use_identical_mapping_when_failure参数用于控制是否在output_text跟输入完全
        对不上时使用恒等映射作为段落区间表。即认为输入raw_text中已经成好段，原样返回。
        
        Example:
            输入:
                行号    raw_text
                0       I've got some bad news for you guys.
                1       My server crashed last night and I've
                2       misplaced all of my data...
                3       including your login details and password
                4       information!

                行号    output_text
                0       I've got some bad news for you guys.
                1       My server crashed last night and I've misplaced all of my data...
                2       including your login details and password information!

            输出:
                [[0, 0], [1, 2], [3, 4]]

        """
        align_map = GPTBatchSequentialDetector.align_and_drop_bad_alignment(raw_text, GPTBatchSequentialDetector.clearup_output(output_text), drop_last_paragraph)
        if len(align_map) == 0:
            if use_identical_mapping_when_failure:
                # 如果反复重问都没有办法解决，就令换行原样返回，这里处理方式是构造一个恒等映射表作为替代，如[[0, 0], [1, 1], [2, 2], [3, 3]]
                return [[x, x] for x in range(len(raw_text.splitlines()))] 
        return list(align_map.values())


    def align_gpt_linebreak_detection_request(self, raw_text: str, record_id: str, batch_index: int, drop_last_paragraph=True) -> list[Tuple[int, int]]:
        """
        Sends a request to the GPT-3.5 API to detect hard line breaks in the given text, 
        and align the given text to its output text on the fly.
        Use `record_id` and `batch_index` to cache the output.
        Unexpected output will not be cached and cause re-asking procedure.
        Use `re_ask_times` to set the retry times for re-asking gpt when unexpected answer generated.

        Args:
            raw_text (str): The raw text to be processed.
            record_id (int): The unique id of the record.
            batch_index (int): The index of the batch.
            drop_last_paragraph (bool): set to False if the current batch is the last batch, so that the last paragraph will not be dropped.

        Returns:
            list[Tuple[int, int]]: The aligned paragragh group intervals indicating a output line refers to which input lines.
        """

        filename = self.cache_dir / f'record_{record_id}_processed_batch_{batch_index}.json'
        if not filename.exists():
            for re_ask_time in range(self.re_ask_times):
                output_text = utils.gpt_detect_hard_line_breaks(raw_text, use_proxy=self.use_proxy)
                segment_list = GPTBatchSequentialDetector.construct_segment_list_from_output_text(raw_text, output_text,
                    re_ask_time == self.re_ask_times - 1, drop_last_paragraph)
                if len(segment_list) == 0: # 记录一下GPT说的胡话以便日后分析
                    with Path('unexpected_outputs.jsonl').open('a', encoding='utf-8') as f:
                        json.dump({'time': str(datetime.now()), 'record': record_id, 'batch': batch_index, 'input': raw_text, 'output': output_text})
                        f.write('\n')
                else:
                    break
            with filename.open('w') as f: # 只有有用的output才会被cache
                json.dump(output_text, f)
        else:
            with filename.open('r') as f:
                output_text = json.load(f)
                segment_list = GPTBatchSequentialDetector.construct_segment_list_from_output_text(raw_text, output_text,
                    True, drop_last_paragraph)
            
        return segment_list

    def generate_batch(self, lines: list[str], begin_lineid: int) -> str:
        """
        从begin_lineid开始构造一个连续若干行的batch，使这个batch尽可能大，同时不超出self.token_limit指定的限制。

        Args:
            lines (list[str]): 源输入文件按行隔开的文本
            begin_lineid (int): 欲开始构造的行下标，包含此行

        Returns:
            str: 构造的batch本身

        """
        # assert begin_lineid < len(lines)
        buffer = ''
        for lineid in range(begin_lineid, len(lines)):
            line = lines[lineid]
            pending_text = (buffer + '\n' if len(buffer)>0 else '') + line
            tokens = self.encoder.encode(pending_text)
            if len(tokens) >= self.token_limit:
                return buffer
            buffer = pending_text
        if buffer:
            return buffer

    def ignore_first_page_leading_noises(self, lines: list[str]) -> int:
        """
        忽略掉首行的一些疑似首页噪声的东西，避免第一个batch成段效果不好。
        
        这里给一个样本：
        United Nations E/2004/93
        Economic and Social Council Distr.: General
        14 July 2004
        Original: English
        04-42475 (E) 140704
        *0442475*
        Substantive session of 2004
        New York, 28 June-23 July 2004
        Agenda item 13 (a)

        输入：lines: list[str]，detect中传入的lines，不再赘述
        输出：int，表示一个行下标，我建议从此行开始往后构造第一个batch
        """
        for lineid, leading_line in enumerate(lines[:self.LEADING_NOISE_SCAN_LINE_LIMIT]):
            if leading_line.lower().find("agenda") != -1: # 
                return lineid + 1 # Agenda item xx是一个比较好的leading noise和正文的分界线，这里判断前12行有没有
        
        # 以下一系列闭包方法为判断一行是否为噪声行的规则
        def match_static_pattern(line: str) -> bool:
            """匹配静态字符串规则"""
            for static_pattern in [
                    'Economic and Social Council Distr.:',
                    'United Nations',
                ]:
                if static_pattern in line or line in static_pattern: # 包含关系，认为满足规则
                    return True
                matcher = SequenceMatcher(a=static_pattern, b=leading_line, autojunk=False)
                if matcher.ratio() > 0.7: # 相似关系，认为满足规则
                    return True
            return False

        def match_re_pattern(line: str) -> bool:
            """匹配正则规则"""
            for re_pattern in [
                    re.compile(r'\d{1,2} [a-zA-Z]+ \d{4}'), # 日期
                    re.compile(r'Original: [a-zA-Z]+') # 源语言
                ]:
                if re.search(re_pattern, line):
                    return True
            return False
        
        def low_en_proportion(line: str) -> bool:
            """英语字母占比规则"""
            return len(line) * 0.5 > len(re.findall(r'[a-zA-Z]', line)) # 英语字母占比小于整行长度一半

        def short_line(line: str) -> bool:
            """行长度规则"""
            return len(line) < 40

        # 我们连续的从上至下一行行匹配已有的规则，一旦有一行不满足规则，则后面的行我们认为已经达到了正文行，直接返回
        for lineid, leading_line in enumerate(lines[:self.LEADING_NOISE_SCAN_LINE_LIMIT]):
            if not (
                    match_static_pattern(leading_line) or
                    match_re_pattern(leading_line) or
                    low_en_proportion(leading_line) or
                    short_line(leading_line)
                ):
                    return lineid

        return self.LEADING_NOISE_SCAN_LINE_LIMIT # 如果前12行都疑似噪声行，则返回第12行



    def detect(self, lines: list[str], record_id: str, **kwargs) -> list[bool]:
        """
        Applies the GPT-3.5 detection technique to the given lines.
        This method first batches the lines, processes the batches, and then post-processes the results.

        Args:
            lines (list[str]): The lines to be detected.
            record_id (int): The unique id of the record. Use to cache the output of GPT

        Returns:
            list[bool]: The detection results.
        """
        # processed_batches = []
        detections = [True] * (len(lines) - 1)

        new_batch_begin_lineid = 0
        batch_id = 0

        if self.ignore_leading:
            new_batch_begin_lineid = self.ignore_first_page_leading_noises(lines)
            print(f'[{record_id}]first batch begin at:{new_batch_begin_lineid}')

        while new_batch_begin_lineid < len(lines):
            batch = self.generate_batch(lines, new_batch_begin_lineid) # 利用已有的结果生成input_batch
            batch_line_count = batch.count('\n') + 1
            next_lineid = new_batch_begin_lineid + batch_line_count
            if len(self.encoder.encode(batch)) < 20: # 结尾不能成段的噪声可能会让gpt疯狂道歉，这种情况下我们放过
                break

            # 获取成段区间表
            segment_list = self.align_gpt_linebreak_detection_request(batch, record_id, batch_id,
                drop_last_paragraph=next_lineid < len(lines)) # 如果是最后一批，就不要丢掉最后一个大段

            for l_border, r_border in segment_list:
                detections[new_batch_begin_lineid + l_border:new_batch_begin_lineid + r_border] = [False] * (r_border - l_border) # 每个段落的区间赋值为False
                
            if next_lineid < len(lines):
                # max(itertools.chain(*segment_list)) 取最大已成段行号
                new_batch_begin_lineid += max(itertools.chain(*segment_list)) + 1 
            else:
                # 已经做完了本文件，接下来不再请求了
                new_batch_begin_lineid = len(lines)

            batch_id += 1

        return detections


if __name__ == '__main__':
    # Test the GPTBatchSequentialDetector
    detector = GPTBatchSequentialDetector('gpt-remote', "./batch_sequential_cache_dir", use_proxy=True)
    # read val_files 432549.txt
    record_id = '453500'
    with open(f'{record_id}.txt', 'r') as f:
        lines = f.readlines()
    lines = [line.strip() for line in lines]

    post_processed_detections = detector.detect(lines, record_id)
    print(post_processed_detections)
    print(len(post_processed_detections), len(lines))
