import pickle
import os
from pathlib import Path

import datasets
from batch_sequential_detector import GPTBatchSequentialDetector
import logging
from text_segmenter import HardLineBreakDetector
import transformers
from sklearn.linear_model import LogisticRegression
import numpy as np
import torch

logging.basicConfig(level=logging.INFO)

LOCAL_WORK_DIR = Path(f'{os.path.dirname(os.path.abspath(__file__))}/batch_cache')
LOCAL_WORK_DIR.mkdir(exist_ok=True)

DATASET_CACHE_DIR = (LOCAL_WORK_DIR / 'dataset')
DATASET_CACHE_DIR.mkdir(exist_ok=True)

DETECTOR_CACHE_DIR = (LOCAL_WORK_DIR / 'batch_sequential_cache_dir') # 生产脚本给出的cache路径
DETECTOR_CACHE_DIR.mkdir(exist_ok=True)

def handle_fn(x):
    x = x.removeprefix('record_')
    return x[:x.find('_')]

def get_and_cache_dataset(path='ranWang/un_pdf_random_preprocessed', split='train'):
    """把hf的东西cache到工作目录，防止dns阻断导致不能验证本地缓存"""
    try:
        dataset = datasets.load_from_disk(DATASET_CACHE_DIR)
    except:
        dataset = datasets.load_dataset(path, split=split)
        dataset.save_to_disk(DATASET_CACHE_DIR)
    return dataset

def use_proxy():
    """全局用socks5代理"""
    import socks
    import socket
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 7890)
    socket.socket = socks.socksocket



class LogisticRegressionDetector(HardLineBreakDetector):
    """
    这份临时代码是用自己训练的模型解决分段问题的起步，包含了训练模型解决问题的所有步骤
    简单起见，直接在初始化阶段用GPT给的数据训练一个线性回归模型
    它并没有直接训练BERT模型
    
    我们只是把这个问题当成简单的句子二分类问题，没有做行与行之间overlap的感知
    """
    BATCH_ITER_LIMIT = 2200 # 根据显存和内存调，每次我们放多少个样本给它，看了一下500大约用掉5.6G显存，2200大约用掉15.4G显存

    @staticmethod
    def batch_spliter(iterable):
        for i in range(0, len(iterable), LogisticRegressionDetector.BATCH_ITER_LIMIT):
            yield iterable[i:i + LogisticRegressionDetector.BATCH_ITER_LIMIT]

    def text2feature(self, en: str):
        if isinstance(en, str):
            en = en.splitlines()
        tokenized = [self.tokenizer.encode(x, add_special_tokens=True) for x in en]
        max_len = max(map(len, tokenized))
        padded = np.array([i + [0]*(max_len-len(i)) for i in tokenized])
        attention_mask = np.where(padded != 0, 1, 0) # True给1，False给0
        input_ids = torch.tensor(padded).cuda()
        attention_mask = torch.tensor(attention_mask).cuda()
        with torch.no_grad():
            last_hidden_states = self.model(input_ids, attention_mask=attention_mask)
        return last_hidden_states[0][:,0,:].cpu().numpy()

    def __init__(self, name):
        super().__init__(name)
        use_proxy()
        model_class = transformers.DistilBertModel
        tokenizer_class = transformers.DistilBertTokenizer
        pretrained_weights = 'distilbert-base-uncased'
        self.tokenizer = tokenizer_class.from_pretrained(pretrained_weights)
        self.model = model_class.from_pretrained(pretrained_weights).cuda()
        self.lr_clf = lr_clf = LogisticRegression()
        recordset = {handle_fn(x) for x in os.listdir(DETECTOR_CACHE_DIR.absolute())}
        detector = GPTBatchSequentialDetector('', cache_dir=DETECTOR_CACHE_DIR.absolute(), token_limit=500, use_proxy=True, ignore_leading_noise_lines=True) # 如果需要用反代这里use_proxy改True
        for single_file_data in get_and_cache_dataset('ranWang/un_pdf_random_preprocessed', split='train').filter(lambda x: x['record'] in recordset).select(range(10)):
            record = single_file_data['record']
            en = single_file_data['en'].splitlines()
            is_hard_linebreak = detector.detect(en, record)
            for feature, label in zip(self.batch_spliter(en), self.batch_spliter(is_hard_linebreak + [True])):
                lr_clf.fit(self.text2feature(feature), label)

    def detect(self, lines: list[str], **kwargs):
        output = [] # 其实它本来就是bool数组，没必要再判>0了
        for feature in self.batch_spliter(lines):
            output.extend(self.lr_clf.predict(self.text2feature(feature)))
        return [True if x > 0 else False for x in output[:-1]]


# if __name__ == "__main__":
#     def text2feature(en: str):
#         tokenized = [tokenizer.encode(x, add_special_tokens=True) for x in en.splitlines()]
#         max_len = max(map(len, tokenized))
#         padded = np.array([i + [0]*(max_len-len(i)) for i in tokenized])
#         attention_mask = np.where(padded != 0, 1, 0) # True给1，False给0
#         input_ids = torch.tensor(padded).cuda()
#         attention_mask = torch.tensor(attention_mask).cuda()

#         with torch.no_grad():
#             last_hidden_states = model(input_ids, attention_mask=attention_mask)
#         return last_hidden_states[0][:,0,:].cpu().numpy()

#     use_proxy()
#     recordset = {handle_fn(x) for x in os.listdir(DETECTOR_CACHE_DIR.absolute())}
    
#     with open('LogisticRegression.pkl', 'wb') as f:
#         pickle.dump(lr_clf, f)
#     test_ds = datasets.load_dataset("bot-yaya/human_joined_en_paragraph_19", split="train", ignore_verifications=True)
#     for record in test_ds:
#         raw_text = record['raw_text']
#         ground_truth = record['is_hard_linebreak'] + [True]
#         record_id = record['record']

#         print(lr_clf.score(text2feature(raw_text), np.array(ground_truth, dtype=np.float32)))