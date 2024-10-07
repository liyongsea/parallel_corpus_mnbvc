"""
本文件仅演示整个pipeline的执行顺序
想要接入命令行参数时，建议只修改new_sample_get_list的FROM_YEAR和TO_YEAR，其他的都不要动
"""
import os

pipeline = [
    'new_sample_get_list.py',
    'new_sample_get_doc_async_candidate.py',
    'new_sample_doc2txt.py',
    # 瓶颈，建议单独换成new_sample_txt2translate_distrib_candidate_server.py和new_sample_txt2translate_distrib_candidate_client.py进行分布式计算，等trcache_pkl缓存生成完毕后再进行下一步
    'new_sample_txt2translate.py',
    'new_sample_translate2align.py',
    'new_sample_align2mergedjsonl.py',
]
for proc in pipeline:
    os.system('python ' + proc)