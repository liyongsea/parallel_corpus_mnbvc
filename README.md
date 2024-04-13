# parallel_corpus_mnbvc
parallel corpus dataset from the mnbvc project

# Install the requirements
```
pip install -r requirements.txt
```

### 运行管线
```shell
python pipeline_poc.py [项目名称] other-args...
```

#### 目前可以运行的项目:

- un_corpus_doc
    - 美国联合国doc文档数据
    - params:
        - "--start_time" 开始时间
        - "--end_time" 结束时间
        - "-o","--output_path" 保存文件的路径
    - 例子: ```python pipeline_poc.py "un_corpus_doc" --start_time="2023-01-01" --end_time="2023-01-11"```
    - 注意: 由于对方网站的ssl版本过低，所以可能需要以下命令```export OPENSSL_CONF=.../parallel_corpus_mnbvc/openssl.cnf && 下载命令```

- us_embassy
    - 美国大使馆
    - params: 
        - "--downloaded_data_file" 缓存的csv文件
    - 例子: ```python pipeline_poc.py "us_embassy" --downloaded_data_file="us_embassy_temp.csv"```

    


### 添加新的语料数据集的方法
可以整理成这个格式
- 代码做成PR到这个仓库，每个项目在根目录下创建一个项目名字，譬如联合国平行语料un_parallel_corpus 
- 跟新一下wiki
- 整理好的数据用[格式检查](https://wiki.mnbvc.org/doku.php/%E7%8E%B0%E6%9C%89%E8%AF%AD%E6%96%99%E6%A0%BC%E5%BC%8F)工具来来检查

### 输出的jsonl格式说明

对于每一个文件，他的json结构层次如下：

```
{
    '文件名': '文件.txt',
    '是否待查文件': False,
    '是否重复文件': False,
    '段落数': 0,
    '去重段落数': 0,
    '低质量段落数': 0,
    '段落': [],
    '拓展字段': json_str,
    '时间': str(yyyymmdd)
}
```

将每一行为一个段落，段落的json结构层次如下：

```
{
    '行号': line_number,
    '是否重复': False,
    '是否跨文件重复': False,
    'zh_text_md5': zh_text_md5,
    'zh_text': 中文,
    'cht_text': 繁体中文,
    'en_text': 英语,
    'ar_text': 阿拉伯语,
    'nl_text': 荷兰语,
    'de_text': 德语,
    'eo_text': 世界语,
    'fr_text': 法语,
    'he_text': 希伯来文,
    'it_text': 意大利语,
    'ja_text': 日语,
    'pt_text': 葡萄牙语,
    'ru_text': 俄语,
    'es_text': 西班牙语,
    'sv_text': 瑞典语,
    'ko_text': 韩语,
    'th_text': 泰语,
    'id_text': 印尼语,
    'vi_text': 越南语,
    'other1_text': 小语种1,
    'other2_text': 小语种2,
    '拓展字段': json_str,
    '时间': str(yyyymmdd)
}
```
