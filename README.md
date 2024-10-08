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
    - "--downloaded_data_file" 缓存的 csv 文件
  - 例子: `python pipeline_poc.py "us_embassy" --downloaded_data_file="us_embassy_temp.csv"`

### 添加新的语料数据集的方法

可以整理成这个格式

- 如果你觉得代码能够整理出来分享，可以做成本仓库的PR，PR里提及涉及的对应Issue区的单子；或者如果代码不便合入这里，也可以另外建立仓库维护，这点不做要求

- 在平行语料组的 [wiki](https://wiki.mnbvc.org/doku.php/pxyl) 和 Issue 区中更新进度

- 整理好的数据用[DataCheck_MNBVC](https://github.com/X94521/DataCheck_MNBVC)工具来来检查：在DataCheck_MNBVC目录下运行终端命令：``python check_data.py --dataset your_folder_path``，其中``your_folder_path``为待检测语料数据所在的文件夹

- datachecker执行完毕后，如果日志文件 ``\logs\check_log.txt`` 显示：

  ```
  checking dataset: your_file_path
  the type of dataset your_file_name is 平行语料格式
  check dataset your_file_name finished, right line 1 / total check line 1
  ```

  则表示格式检测通过

- 【新】对于下文提到的`可以留空，用jsonl_chk.py自动填写`的字段，我们不推荐手动填写。你可以**先**为这些字段留对应类型的默认值以通过DataCheck，然**后**用本项目根目录的 `jsonl_chk.py` 来填写这些相对通用的字段：
- - 命令样例（单文件）：`python jsonl_chk.py your_file_name.jsonl -ea`
- - 命令样例（处理整个目录的所有jsonl）：`python jsonl_chk.py -d F:\path\to\your\workdir -ea`

**注意：** jsonl_chk.py 脚本只能接受 jsonl 格式，即一行一个的 json 字符串，请不要把自动格式化的 json 文件贴进去尝试用这个脚本处理。

### 输出的 jsonl 格式说明

对于每一个文件，他的 json 结构层次如下：

```
{
    '文件名': '文件.txt', # 过滤语料种类,取中文的输入文件的文件名
    '是否待查文件': False, # 【可以留空，用jsonl_chk.py自动填写】如果是True就是不怎么靠谱，告诉大家尽量别用
    '是否重复文件': False, # 【可以留空，用jsonl_chk.py自动填写】留给其它小组的字段，我们给False就行
    '段落数': 0, # 【可以留空，用jsonl_chk.py自动填写】
    '去重段落数': 0, # 【可以留空，用jsonl_chk.py自动填写】只看中文zh_text，完全相等就算重，这里统计【重复】的段落数
    '低质量段落数': 0, # 【可以留空，用jsonl_chk.py自动填写】zh_text或者en_text有缺（为空字符串）的段落数量
    '段落': [],
    '扩展字段': '{}' # json.dumps(xxx, ensure_ascii=False)得出的字符串，现在要求为有效的json字符串并且能被json.loads解析，所以为空时请填写{}
    '时间': str(yyyymmdd) # 例子: 20240801
}
```

将每一行为一个段落，段落的 json 结构层次如下：

**注意：**所有语种字段的双字母缩写优先参考[ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)的定义，并且优先填写下文所注的段落级主要字段，如果没有，则根据iso双字母简写填入扩展字段中。如果所收录语言并不在 iso 639-1 双字母简写表中，请自己起一个不与其他双字母简写有冲突的key名写到扩展字段中，并将其key名和对应的语种作为注释写到文件级扩展字段中。

```
{
    '行号': 如果源文件有行号信息，可以记在此处，否则取从1开始递增的值，尽量保证每个段落的行号都不同,
    '是否重复': False, # 【可以留空，用jsonl_chk.py自动填写】用zh_text全等进行判断，第一次出现的是False，后面重复的就是True
    '是否跨文件重复': False, # 【可以留空，用jsonl_chk.py自动填写】留给其它小组的字段，我们给False就行
    'zh_text_md5': "b656579704c6ca5acc29f2aa36159ce2" # 【可以留空，用jsonl_chk.py自动填写】十六进制的中文语句的md5，可以直接用hashlib.md5(zh_text).hexdigest()得到,
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
    'other1_text': 原小语种1，因为意义不明确，每个语料的语种不统一，不建议使用，请固定给空字符串,
    'other2_text': 原小语种2，因为意义不明确，每个语料的语种不统一，不建议使用，请固定给空字符串,
    '扩展字段': json格式字符串，详细约定见下文
    '时间': str(yyyymmdd)
}
```

`other1_text`、`other2_text` 必须存在，但是建议为空字符串，所有未在上述字段中出现的其他语言可放到`扩展字段`中.

文件以及段落的`扩展字段`为 json 字符串，目前的约定为:


**段落**

```
{
    other_texts: {
        {lang1_iso}: "",
        {lang2_iso}: ""
    },
    ...
}
```

**文件**

```
{
    other_texts_iso_map: {
        {lang1_iso}: "语种1",
        {lang2_iso}: "语种2"
    }
}
```

如果没有别的需要收录的语种，并且也没有其它信息需要用扩展字段记录时，扩展字段这里约定填{}来保证json.loads不会出问题。

一份样例语料数据（注意，扩展字段直接用json.dumps(obj,ensure_ascii=False)生成，故会带反斜杠将内部字符串的双引号转义）:

```
{
    "文件名": "Terraria-workshop-localization_test2.jsonl",
    "是否待查文件": false,
    "是否重复文件": false,
    "段落数": 17944,
    "去重段落数": 0,
    "低质量段落数": 0,
    "段落": [
        {
            "行号": 1,
            "是否重复": false,
            "是否跨文件重复": false,
            "it_text": "",
            "zh_text": "正在生成海洋沙",
            "en_text": "Generating ocean sand",
            "ar_text": "",
            "nl_text": "",
            "de_text": "",
            "eo_text": "",
            "fr_text": "Génération du sable de l'océan",
            "he_text": "",
            "ja_text": "",
            "pt_text": "Gerando areia do oceano",
            "ru_text": "Создание песка в океане",
            "es_text": "",
            "sv_text": "",
            "ko_text": "",
            "th_text": "",
            "other1_text": "",
            "other2_text": "",
            "id_text":"",
            "cht_text":"",
            "vi_text":"",
            "扩展字段": "{\"other_texts\": {\"cs\": \"Generování mořského písku\", \"pl\": \"Generowanie piasku morskiego\", \"hu\": \"Tengeri homok elhelyezése\", \"uk\": \"Генерація океанського піску\", \"tr\": \"Okyanus kumu üretme\"}}",
            "时间": "20240316",
            "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2"
        }
    ],
    "扩展字段": "{\"other_texts_iso_map\": {\"cs\": \"捷克语\", \"pl\": \"波兰语\", \"hu\": \"匈牙利语\", \"uk\": \"乌克兰语\", \"tr\": \"土耳其语\"}}",
    "时间": "20240316"
}
```
