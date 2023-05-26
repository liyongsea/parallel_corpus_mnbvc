import sys
import os
from typing import Tuple
from pathlib import Path
from argparse import ArgumentParser

import datasets
import pylcs

### 工作路径相关代码
WORKDIR_ABSOLUTE = r'C:\Users\Administrator\Documents\parallel_corpus_mnbvc\alignment\bertalign' # 工作区绝对路径，实际使用换成.即可

def cat(*args): 
    return '/'.join(args)

def my_path(*args):
    """相对路径"""
    return cat(WORKDIR_ABSOLUTE, *args)
###

def get_and_cache_dataset():
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(my_path())
        return dataset
    except:
        dataset = datasets.load_dataset('bot-yaya/UN_PDF_SUBSET_PREPROCESSED', split='train')
        dataset.save_to_disk(my_path())
        return dataset


def lcs_sequence_alignment(ibatch: list[str] | str, obatch: list[str] | str) -> Tuple[dict[int, set[int]], list[float], list[float]]:
    """将ibatch每行的单词用最长公共子序列对齐到obatch每行的单词中。
    
    Args:
        ibatch(str): 输入的一段话
        obatch(str): chatgpt给对齐好的一段话
    
    Returns:
        mapping(dict[int, set[int]]): 输出行号对应输入的行号
        irate(list[float]): 输入每行的匹配率（匹配的单词总长度/本行总单词总长度）
        orate(list[float]): 输出每行的匹配率
    """
    if isinstance(ibatch, str):
        ibatch = ibatch.splitlines()
    if isinstance(obatch, str):
        obatch = obatch.splitlines()
    offset = 19968
    dic = {}
    
    ibuf = [] # 输入token
    ilen = []

    obuf = []
    olen = []
    # 手写的token转换，优化lcs的效率，这里换成中文字形式编码这些token，只判等
    offset = 19968 # 中文unicode起点
    dic = {}
    for ilineid, iline in enumerate(ibatch):
        sp = iline.split()
        ilen.append(sum(map(len, sp)))
        for i in sp:
            ibuf.append((
                chr(offset + dic.setdefault(i, len(dic))),
                len(i),
                ilineid,
                ))
    
    for olineid, oline in enumerate(obatch):
        sp = oline.split()
        olen.append(sum(map(len, sp)))
        for i in oline.split():
            if i in dic: # 为子序列写的优化
                obuf.append((
                    chr(offset + dic[i]),
                    len(i),
                    olineid,
                    ))
    

    irate = [0 for _ in ilen]
    orate = [0 for _ in olen]

    n1 = ''.join(map(lambda x: x[0], ibuf))
    n2 = ''.join(map(lambda x: x[0], obuf))
    # print(f'n1:{len(n1)}, n2:{len(n2)}')
    idxs = pylcs.lcs_sequence_idx(n1, n2)
    mapping = {}
    for iidx, oidx in enumerate(idxs):
        if oidx != -1:
            _, iklen, ikgroup = ibuf[iidx]
            _, oklen, okgroup = obuf[oidx]
            mapping.setdefault(okgroup, set()).add(ikgroup)
            irate[ikgroup] += iklen
            orate[okgroup] += oklen
    
    for p, i in enumerate(irate):
        irate[p] = i / ilen[p]
    for p, i in enumerate(orate):
        orate[p] = i / olen[p]

    # 额外处理：匹配率低于50%的olineid不要
    print(mapping)
    print('orate', orate)
    for p, i in enumerate(orate):
        if i < 0.5:
            if p in mapping:
                mapping.pop(p)

    return mapping, irate, orate

def get_br_indexes_from_alignmap(align_map: dict[int, set[int]]) -> list[int]:
    br = []
    for igroups in align_map.values():
        for i in igroups:
            if i + 1 in igroups:
                br.append(i)
    br.sort()
    return br

if __name__ == "__main__":
    Path(my_path('converted')).mkdir(exist_ok=True)
    print(sys.argv)
    ap = ArgumentParser(prog=sys.argv[0])
    ap.add_argument('labeled_file', help='labeled plain text file, paragraphs separated by \\n')
    args = ap.parse_args()

    with open(args.labeled_file, 'r', encoding='utf-8') as f:
        output = f.read()

    ds = get_and_cache_dataset()
    rec = input('record id:')
    for i in ds.filter(lambda x: x['record'] == rec):
        pos = my_path('converted', f'{rec}.idx')
        ilines = i['en']
        align_map, irate, orate = lcs_sequence_alignment(ilines, output)
        br = get_br_indexes_from_alignmap(align_map)
        with open(pos, 'w', encoding='utf-8') as f:
            f.write(','.join(map(str, br)))

        br = set(br) # br就是需要干掉的换行下标
        concated = []
        for lineid, iline in enumerate(ilines.splitlines()):
            if lineid - 1 in br:
                concated[-1] += ' ' + iline
            else:
                concated.append(iline)

        with open(my_path('converted', f'{rec}.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(concated))

        print('indexing file saved to', os.path.abspath(pos))

