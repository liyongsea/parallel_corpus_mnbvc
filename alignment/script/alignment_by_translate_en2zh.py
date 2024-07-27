from collections import namedtuple
from typing import Tuple
from itertools import chain

import pylcs
from transformers import pipeline


LCSTokenInfo = namedtuple('LCSTokenInfo', ('token', 'length', 'source_line_id'))
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

def tokenize_by_char(input_lines: list[str], output_lines: list[str], offset=0) -> Tuple[list[LCSTokenInfo], list[LCSTokenInfo]]:
        """
        """
        char_set = set(chain(*input_lines))
        input_tokens_info = []
        output_tokens_info = []
        for input_line_id, input_line in enumerate(input_lines):
            for char in input_line:
                input_tokens_info.append(LCSTokenInfo(
                    char,
                    1,
                    input_line_id,
                    ))
        
        for output_line_id, output_line in enumerate(output_lines):
            for char in output_line:
                if char in char_set: # 为子序列写的优化
                    output_tokens_info.append(LCSTokenInfo(
                        char,
                        1,
                        output_line_id,
                        ))
        return input_tokens_info, output_tokens_info

def lcs_sequence_alignment(input_lines: list[str] , output_lines: list[str], drop_th=0.6, tokenizer=tokenize_by_space_splited_word) -> Tuple[dict[int, Tuple[int, int]], list[float], list[float]]:
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
    if isinstance(input_lines, str):
        input_lines = input_lines.splitlines()
    if isinstance(output_lines, str):
        output_lines = output_lines.splitlines()
    # 考虑到运行效率，我们切分粒度采用空格隔开的单词而不是字母
    input_tokens_info, output_tokens_info = tokenizer(input_lines, output_lines)

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

    for p, _ in enumerate(input_hit_rate):
        input_hit_rate[p] /= sum(map(len, input_lines[p].split())) + 1e-3
    for p, _ in enumerate(output_hit_rate):
        output_hit_rate[p] /= sum(map(len, output_lines[p].split())) + 1e-3

    # 额外处理：匹配率低于60%的olineid不要
    print(align_map)
    print('orate', output_hit_rate)
    for p, i in enumerate(output_hit_rate):
        if i < drop_th:
            if p in align_map:
                align_map.pop(p)
    
    return align_map, input_hit_rate, output_hit_rate

def translate(en: str | list[str]) -> list[str]:
    # 这一步初始化translator的开销不小
    # 为了性能优化，这个translator应该在大规模数据传入时在本函数外层初始化
    # 也要考虑是否把整个pipeline放cuda:0里
    translator = pipeline("translation", model=f"Helsinki-NLP/opus-mt-en-zh", device='cuda:0')
    if isinstance(en, str):
        en = en.splitlines()
    translated = []
    for paragraph in en:
        word_buffer = []
        translated.append('')
        for word in paragraph.split():
            word_buffer.append(word)
            # 这里有两个根据经验调的magic number，为了避免翻译pipeline的token count超过512报错
            if len(word_buffer) >= 350 or sum(map(len, word_buffer)) >= 1024:
                translated[-1] += ''.join(translator(' '.join(word_buffer))[0]['translation_text'])
                word_buffer.clear()
        if word_buffer:
            translated[-1] += ''.join(translator(' '.join(word_buffer))[0]['translation_text'])
    return translated
    

def align(en: str | list[str], zh: str | list[str], en_translated: str | list[str] = None) -> Tuple[list[Tuple[str, str]], list[str]]:
    """
    Args:
        en: 英文已成段文本
        zh: 中文未成段文本
        en_translated: 英翻中之后的段落。应该是中文段落。列表长度应该跟en一样长
    Returns:
        aligned (list[Tuple[str, str]]): 对齐好的文本，每条是(英, 中)的格式
        dropped (list[Tuple[str, str]]): 对不上的英语段落文本
    """
    if isinstance(en, str):
        en = en.splitlines()
    if isinstance(zh, str):
        zh = zh.splitlines()
    if isinstance(en_translated, str):
        en_translated = en_translated.splitlines()

    if not en_translated:
        en_translated = translate(en)

    aligned = []
    dropped = []

    align_map, irate, orate = lcs_sequence_alignment(zh, en_translated, 0.2, tokenize_by_char)
    # irate表示中文原文本对齐命中率，orate表示英翻中文本对齐命中率
    print(irate) # 这两个变量仅用于诊断，这里用print输出而不是打日志
    print(orate)
    for paragraph_id, (line_id_lowerbound, line_id_upperbound) in align_map.items():
        aligned.append((''.join(zh[line_id_lowerbound:line_id_upperbound + 1]), en[paragraph_id]))
    
    for paragraph_id, paragraph in enumerate(en):
        if paragraph_id not in align_map:
            dropped.append(paragraph)
    
    return aligned, dropped

if __name__ == "__main__":
    en = '''1. Takes note of the report of the Secretary-General;6
2. Welcomes the contributions made in the lead-up to the midterm comprehensive global review of the implementation of the Programme of Action for the Least Developed Countries for the Decade 2001-2010,2 including the elaboration of the Cotonou Strategy for the Further Implementation of the Programme of Action for the Least Developed Countries for the Decade 2001-20107 as an initiative owned and led by the least developed countries;
3. Reaffirms its commitment to the Declaration8 adopted by Heads of State and Government and heads of delegations participating in the high-level meeting of the General Assembly on the midterm comprehensive global review of the implementation of the Programme of Action for the Least Developed Countries for the Decade 2001-2010, in which they recommitted themselves to addressing the special needs of the least developed countries by making progress towards the goals of poverty eradication, peace and development;
4. Acknowledges the findings of the midterm comprehensive global review, which stressed that despite some progress in the implementation of the Programme of Action for the Least Developed Countries for the Decade 2001-2010, the overall socio-economic situation in the least developed countries continues to be precarious and requires attention and that, given current trends, many least developed countries are unlikely to achieve the goals and objectives set out in the Programme of Action;
5. Stresses that the internationally agreed development goals, including the Millennium Development Goals, can be effectively achieved in the least developed countries through, in particular, the timely fulfilment of the seven commitments of the Programme of Action;
6. Reaffirms that the Programme of Action constitutes a fundamental framework for a strong global partnership, whose goal is to accelerate sustained economic growth, sustainable development and poverty eradication in the least developed countries;
7. Also reaffirms that progress in the implementation of the Programme of Action will require effective implementation of national policies and priorities for the sustained economic growth and sustainable development of the least developed countries, as well as strong and committed partnership between the least developed countries and their development partners;
8. Underscores that for the further implementation of the Programme of Action, the least developed countries and their development partners must be guided by an integrated approach, a broader genuine partnership, country ownership, market considerations and results-oriented actions;
9. Urges the least developed countries to strengthen the implementation of the Programme of Action through their respective national development framework, including, where they exist, poverty reduction strategy papers, the common country assessment and the United Nations Development Assistance Framework;
10. Also urges development partners to exercise individual best efforts to continue to increase their financial and technical support for the implementation of the Programme of Action;
11. Encourages the United Nations resident coordinator system to assist the least developed countries in translating goals and targets of the Programme of Action into concrete actions in the light of their national development priorities;
12. Also encourages the resident coordinator system and country teams, as well as country-level representatives of the Bretton Woods institutions, bilateral and multilateral donors and other development partners, to collaborate with and provide support to, as appropriate, the relevant development forums and follow-up mechanisms;
13. Invites the organizations of the United Nations system and other multilateral organizations that have not yet done so to mainstream the implementation of the Brussels Declaration1 and the Programme of Action within their programmes of work as well as in their intergovernmental processes and to undertake within their respective mandates multi-year programming of actions in favour of the least developed countries;
14. Stresses, within the context of the annual global reviews, as envisaged in the Programme of Action, the need to assess the implementation of the Programme of Action sector by sector, and in this regard invites the United Nations system and all relevant international organizations, consistent with their respective mandates, to report on the progress made in its implementation using quantifiable criteria and indicators to be measured against the goals and targets of the Programme of Action and to participate fully in reviews of the Programme of Action at the national, subregional, regional and global levels;
15. Also stresses the crucial importance of integrated and coordinated follow-up, monitoring and reporting for the effective implementation of the Programme of Action at the national, subregional, regional and global levels;
16. Requests the Secretary-General to ensure, at the Secretariat level, the full mobilization and coordination of all parts of the United Nations system to facilitate coordinated implementation as well as coherence in the follow-up to and monitoring and review of the Programme of Action at the national, subregional, regional and global levels, including through such coordination mechanisms as the United Nations System Chief Executives Board for Coordination, the United Nations Development Group, the Executive Committee on Economic and Social Affairs and the Inter-agency Expert Group on the Millennium Development Goals Indicators;
17. Reiterates its invitation to the organs, organizations and bodies of the United Nations system, and other relevant multilateral organizations, to provide full support to and cooperation with the Office of the High Representative for the Least Developed Countries, Landlocked Developing Countries and Small Island Developing States;
18. Requests the Secretary-General to elaborate and submit to the General Assembly at its sixty-second session a detailed and clearly defined advocacy strategy aimed at raising awareness about the objectives, goals and commitments of the Programme of Action with a view to facilitating its effective and timely implementation;
19. Also requests the Secretary-General to submit an annual analytical and results-oriented progress report on the further implementation of the Programme of Action and to make available adequate resources, within existing resources, for the preparation of such a report.'''
    zh='''1. 注意到秘书长的报告；6
2. 欢迎直到《2001-2010 十年期支援最不发达国家行动纲领》2
执行情况
全球综合中期审查之时所作的贡献，包括制定《进一步执行 2001-2010 十年期支
援最不发达国家行动纲领科托努战略》，7
这是一项由最不发达国家掌控和主导
的倡议；
3. 重申其对参加大会《2001-2010 十年期支援最不发达国家行动纲领》执
行情况全球综合中期审查高级别会议的国家元首和政府首脑以及代表团团长通
过的《宣言》8
的承诺，其中他们再次承诺在迈向脱贫、和平与发展目标的路上
取得进展，以满足这些国家的特殊需要；
4. 确认全球综合中期审查的结论，其中着重指出虽然在执行《2001-2010
十年期支援最不发达国家行动纲领》方面取得了一些进展，但最不发达国家的总
体社会经济状况仍然岌岌可危，需要予以注意，并着重指出鉴于当前各种趋势，
许多最不发达国家不大可能实现《行动纲领》中所定的各项目标；
5. 着重指出各项国际商定的发展目标，包括千年发展目标，是能够有效地
在最不发达国家得到实现的，特别是通过按时履行《行动纲领》中的七项承诺；
6. 重申《行动纲领》是建立牢固的全球伙伴关系的基本框架，目标在于加
快最不发达国家的持续经济增长和可持续发展，加快消除贫穷；
7. 又重申要在执行《行动纲领》方面取得进展，就需要切实执行促进最不
发达国家经济增长和可持续发展的国家政策和优先项目，而且需要最不发达国家
及其发展伙伴建立牢固和坚定的伙伴关系；
8. 强调为了进一步执行《行动纲领》，最不发达国家及其发展伙伴必须以
综合办法、更广泛的真正伙伴关系、国家掌有权、市场因素和面向成果的行动为
指导；
9. 敦促最不发达国家通过其各自的国家发展框架，包括现有的减贫战略文
件、共同国家评估和联合国发展援助框架，加强执行《行动纲领》；
10. 又敦促发展伙伴各自尽全力继续增加对执行《行动纲领》的财政和技术
支助；
11. 鼓励联合国驻地协调员系统协助最不发达国家按照本国发展优先事项，
把《行动纲领》所载各项目标和指标变为具体行动；
12. 又鼓励联合国驻地协调员系统和国家工作队以及布雷顿森林机构、双边
和多边捐助者及其他发展伙伴的国家一级代表同有关发展论坛和国家后续行动
机制协作，并酌情向这些论坛和机制提供支助；
13. 请尚未这样做的联合国系统组织和其他多边组织，把执行《布鲁塞尔宣
言》1
和《行动纲领》的工作纳入其工作方案及其政府间进程，并在各自授权任
务内采取有利于最不发达国家的多年行动方案；
14. 着重指出正如《行动纲领》所设想的，需要在年度全球审查范围内按每
一个部门评估《行动纲领》的执行情况，并在这方面请联合国系统和所有相关国
际组织，根据它们各自的授权任务，利用拟按照《行动纲领》的各项目标来衡量
的量化准则和指标报告在执行方面取得的进展，并充分参与在国家、次区域、区
域和全球各级对《行动纲领》进行的审查；
15. 又着重指出极为重要的是采取综合和协调的后续行动，监测和报告在国
家、次区域、区域和全球各级有效执行《行动纲领》的情况；
16. 请秘书长确保在秘书处一级充分调动和协调联合国系统的所有组成部
分，促进在国家、次区域、区域和全球各级协调地执行《行动纲领》以及统筹采
取后续行动，并监测和审查执行情况，包括通过诸如联合国系统行政首长协调理
事会、联合国发展集团、经济和社会事务执行委员会和千年发展目标指标问题机
构间专家组等协调机构来这样做；
17. 重申邀请联合国系统各机关、组织和机构以及其他相关多边组织向最不
发达国家、内陆发展中国家和小岛屿发展中国家高级代表办公室提供充分支持与
合作；
18. 请秘书长编写并向大会第六十二届会议提交一份详尽清晰的宣传战略，
旨在提高对《行动纲领》各项目的、目标和承诺的认识，促进有效和及时执行；
19. 又请秘书长就进一步执行《行动纲领》的情况提交年度面向成果的分析
性进度报告，并在现有资源范围内为编写这份报告提供足够的资源。'''
    print(align(en, zh))