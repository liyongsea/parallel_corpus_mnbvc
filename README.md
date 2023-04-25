# parallel_corpus_mnbvc
parallel corpus dataset from the mnbvc project

# Install the requirements
```
pip install -r requirements.txt
```

# output data format
```
features = datasets.Features(
 {
  "zh_text": datasets.Value("string"),
  "en_text": datasets.Value("string"),
  "aa_text": datasets.Value("string"),
  "bb_text": datasets.Value("string"),
  "cc_text": datasets.Value("string"),
  "meta": datasets.Value("string")
 }
)
```

### 输出的jsonl格式说明

3. 对于每一个文件，他的json结构层次如下：

   ```python
   {
       '文件名': '文件.txt',
       '是否待查文件': False,
       '是否重复文件': False,
       '段落数': 0,
       '去重段落数': 0,
       '低质量段落数': 0,
       '段落': []
   }
   ```

   将每一行为一个段落，段落的json结构层次如下：

   ```python
   {
       '行号': line_number,
       '是否重复': False,
       '是否跨文件重复': False,
       'zh_text_md5': zh_text_md5,
       'zh_text': zh_text,
       'en_text_md5': en_text_md5,
       'en_text': en_text,
       'aa_text_md5': aa_text_md5,
       'aa_text': aa_text,
       'bb_text_md5': bb_text_md5,
       'bb_text': bb_text,
       'cc_text_md5': cc_text_md5,
       'cc_text': cc_text,
   }
   ```
