import argparse
import os
import json
from pathlib import Path

import datasets
from batch_sequential_detector import GPTBatchSequentialDetector

LOCAL_WORK_DIR = Path('.') # 如需修改工作目录可以把这里改成绝对路径

def get_and_cache_dataset(path='bot-yaya/un_pdf_random10000_preprocessed', split='train'):
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(LOCAL_WORK_DIR.absolute())
    except:
        dataset = datasets.load_dataset(path, split=split)
        dataset.save_to_disk(LOCAL_WORK_DIR.absolute())
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', type=str, help='openai api key')
    parser.add_argument('--file_index', type=str, help='直接给下标吧，1~10032')
    # 我建议写死这个done_file，不管传参用默认值就行
    parser.add_argument('--done_file', type=str, default='done_file', help='一个目录，这个目录中会在脚本运行期间存一些文件，每个文件的文件名表示该标号的文件已经请求完毕，内容则为处理完毕后的is_hard_linebreak二值表。可以之后将这些表上传在线数据库或者是直接打包分发')


    args = parser.parse_args()

    done_directory: Path = LOCAL_WORK_DIR / args.done_file
    done_directory.mkdir(exist_ok=True)

    single_file_data = get_and_cache_dataset().select((args.file_index, args.file_index + 1))[0]
    record = single_file_data['record']

    os.environ['OPENAI_API_KEY'] = args.api_key

    detector = GPTBatchSequentialDetector('', cache_dir=(LOCAL_WORK_DIR / '').absolute(), use_proxy=True)
    is_hard_linebreak: list[bool] = detector.detect(single_file_data)
    with (done_directory / f'{record}.list').open('w') as f:
        json.dump(is_hard_linebreak, f)
