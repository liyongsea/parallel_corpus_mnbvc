from collections import namedtuple
import traceback
from typing import Tuple
import itertools
from pathlib import Path
import json

import tiktoken
import pylcs

from text_segmenter import HardLineBreakDetector
import utils

LCSTokenInfo = namedtuple('LCSTokenInfo', ('token', 'length', 'source_line_id'))

class GPTBatchSequentialDetector(HardLineBreakDetector):
    def __init__(self, name, cache_dir, token_limit=1400, use_proxy=False, re_ask_times=3):
        super().__init__(name)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        self.token_limit = token_limit
        self.use_proxy = use_proxy
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.re_ask_times = re_ask_times

    @staticmethod
    def clearup_output(raw_output_from_chatgpt: str) -> list[str]:
        """处理返回的数据中包含\n\n的情况"""
        return list(filter(lambda x: len(x.strip()), raw_output_from_chatgpt.splitlines()))

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
    def lcs_sequence_alignment(input_lines: list[str] | str, output_lines: list[str] | str) -> Tuple[dict[int, set[int]], list[float], list[float]]:
        """
        将input_lines每行的单词用最长公共子序列对齐到output_lines每行的单词中。
        这个函数同时还会计算每行输入输出的单词命中率（此行的已匹配单词总长度/此行单词总长度），
        将命中率低于0.6的输出行连带其对应的输入行扔掉。
        
        Args:
            input_lines(str): 输入的一段话
            output_lines(str): chatgpt给对齐好的一段话
        
        Returns:
            mapping(dict[int, set[int]]): 输出行号对应输入的行号
            irate(list[float]): 输入每行的匹配率（匹配的单词总长度/本行总单词总长度）
            orate(list[float]): 输出每行的匹配率
        """
        if isinstance(input_lines, str):
            input_lines = input_lines.splitlines()
        if isinstance(output_lines, str):
            output_lines = output_lines.splitlines()
        
        # 考虑到运行效率，我们切分粒度采用空格隔开的单词而不是字母
        input_tokens_info, output_tokens_info = GPTBatchSequentialDetector.tokenize_by_space_splited_word(input_lines, output_lines)

        # 算输入输出的每行的单词命中率，即：匹配的单词总字符数 / 单词总字符数
        input_hit_rate = [0 for _ in input_lines] 
        output_hit_rate = [0 for _ in output_lines]

        input_tokens = ''.join(map(lambda x: x[0], input_tokens_info))
        output_tokens = ''.join(map(lambda x: x[0], output_tokens_info))
        # print(f'input_tokens:{len(input_tokens)}, output_tokens:{len(output_tokens)}')
        aligned_indexes = pylcs.lcs_sequence_idx(input_tokens, output_tokens)
        mapping = {}
        for input_token_index, output_token_index in enumerate(aligned_indexes):
            if output_token_index != -1:
                _, input_word_length, input_line_id = input_tokens_info[input_token_index]
                _, output_word_length, output_line_id = output_tokens_info[output_token_index]
                mapping.setdefault(output_line_id, set()).add(input_line_id)
                input_hit_rate[input_line_id] += input_word_length
                output_hit_rate[output_line_id] += output_word_length
        
        for p, i in enumerate(input_hit_rate):
            input_hit_rate[p] /= sum(map(len, input_lines[p].split()))
        for p, i in enumerate(output_hit_rate):
            output_hit_rate[p] /= sum(map(len, output_lines[p].split()))

        if len(mapping) > 1:
            mapping.pop(max(mapping.keys())) # 干掉最后一个分组，避免不完全成段

        # 为了防止加段现象影响准确率，匹配率低于60%的output_line_id直接扔掉
        for p, i in enumerate(output_hit_rate):
            if i < 0.6:
                if p in mapping:
                    mapping.pop(p)

        return mapping, input_hit_rate, output_hit_rate

    def align_gpt_linebreak_detection_request(self, raw_text: str, record_id: str, batch_index: int) -> dict[int, set[int]]:
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

        Returns:
            dict[int, set[int]]: The aligned paragragh group, indicating a output line refers to which input lines.
        """

        filename = self.cache_dir / f'record_{record_id}_processed_batch_{batch_index}.json'
        if not filename.exists():
            for re_ask_time in range(self.re_ask_times):
                try:
                    output_text = utils.gpt_detect_hard_line_breaks(raw_text, use_proxy=self.use_proxy)
                    # 隐含一个风险点：align_map是空的，会直接导致后续的整个文件不能执行
                    # 这种情况在GPT说胡话的时候会发生，多发地是文件的结尾部分
                    align_map, _, _ = GPTBatchSequentialDetector.lcs_sequence_alignment(raw_text, self.clearup_output(output_text))
                    assert len(align_map) >= 1 # 卡掉align_map == 0的情况，避免死循环浪费api，在挂机跑文件的情况下可以抓掉这个错，标记致命错误的异常文件
                    break
                except:
                    traceback.print_exc()
                    print(raw_text)
                    print('=====')
                    print(output_text)
                    if re_ask_time == self.re_ask_times - 1:
                        raise

            with filename.open('w') as f: # 只有有用的output才会被cache
                json.dump(output_text, f)
        else:
            with filename.open('r') as f:
                output_text = json.load(f)
                align_map, _, _ = GPTBatchSequentialDetector.lcs_sequence_alignment(raw_text, self.clearup_output(output_text))
            
        return align_map

    def generate_batch(self, lines: list[str], begin_lineid: int) -> Tuple[str, int]:
        """
        从begin_lineid开始构造一个连续若干行的batch，使这个batch尽可能大，同时不超出self.token_limit指定的限制。

        Args:
            lines (list[str]): 源输入文件按行隔开的文本
            begin_lineid (int): 欲开始构造的行下标，包含此行

        Returns:
            Tuple[str, int]: 构造的batch本身，以及游标处理到的下一行（即当前batch对应于原文的最后一行的*下一行*）行下标

        """
        assert begin_lineid < len(lines)
        buffer = ''
        for lineid in range(begin_lineid, len(lines)):
            line = lines[lineid]
            pending_text = (buffer + '\n' if len(buffer)>0 else '') + line
            tokens = self.encoder.encode(pending_text)
            if len(tokens) >= self.token_limit:
                return buffer, lineid # 本行还没加上，所以是开区间
            buffer = pending_text
        if buffer:
            return buffer, lineid + 1

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
        detections = [False] * (len(lines) - 1)

        todo_lineid = 0
        batch_id = 0

        while todo_lineid < len(lines):
            batch, next_line_id = self.generate_batch(lines, todo_lineid) # 利用已有的结果生成input_batch
            if len(self.encoder.encode(batch)) < 20: # 结尾不能成段的噪声可能会让gpt疯狂道歉，这种情况下我们放过
                break

            align_map = self.align_gpt_linebreak_detection_request(batch, record_id, batch_id)
            # Compare the hard line breaks in the raw text with the output text

            input_line_offset = next_line_id - len(batch.splitlines()) # 第一行在本文件中的下标
            assert lines[input_line_offset] == batch.splitlines()[0]
            if next_line_id < len(lines):
                todo_lineid = max(itertools.chain(*align_map.values())) + input_line_offset + 1 
            else:
                # 已经做完了本文件，接下来不再请求了
                todo_lineid = len(lines)

            for igroups in align_map.values():
                for igroup in igroups:
                    if igroup + 1 in igroups:
                        detections[igroup + input_line_offset] = True
            
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
