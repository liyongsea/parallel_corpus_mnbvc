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

- us_embassy
    - 美国大使馆
    - params: 
        - "--downloaded_data_file" 缓存的csv文件
    - 例子: ```python pipeline_poc.py "us_embassy" --downloaded_data_file="us_embassy_temp.csv"```

    


### 添加新的语料数据集的方法
可以整理成这个格式
- 代码做成PR到这个仓库，每个项目在根目录下创建一个项目名字，譬如联合国平行语料un_parallel_corpus 
- 更新一下wiki
- 整理好的数据用[DataCheck_MNBVC](https://github.com/X94521/DataCheck_MNBVC)工具来来检查

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
    '扩展字段': json_str,
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
    'cht_text': 繁体中文,
    'other1_text': 小语种1,
    'other2_text': 小语种2,
    '扩展字段': json_str
}
```

一份样例语料数据:
```
{"文件名": "Terraria-workshop-localization_test2.jsonl", "是否待查文件": false, "是否重复文件": false, "段落数": 17944, "去重段落数": 0, "低质量段落数": 0, "段落": [{"行号": 1, "是否重复": false, "是否跨文件重复": false, "it_text":"","zh_text": "正在生成海洋沙", "en_text": "Generating ocean sand", "ar_text": "", "nl_text": "", "de_text": "", "eo_text": "", "fr_text": "Génération du sable de l'océan", "he_text": "", "it_text": "", "ja_text": "", "pt_text": "Gerando areia do oceano", "ru_text": "Создание песка в океане", "es_text": "", "sv_text": "", "ko_text": "", "th_text": "", "other1_text": "", "other2_text": "", "id_text":"","cht_text":"","vi_text":"","扩展字段": "{}", "时间": "20240316", "hu_text": "Tengeri homok elhelyezése", "uk_text": "Генерація океанського піску", "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2"}], "扩展字段": "{}", "时间": "20240316"}
```