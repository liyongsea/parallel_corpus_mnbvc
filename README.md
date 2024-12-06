<!-- # parallel_corpus_mnbvc

parallel corpus dataset from the mnbvc project

# Install the requirements

```
pip install -r requirements.txt
``` -->

#  MNBVC 平行语料


欢迎来到 **MNBVC 平行语料小组** 的总仓库。本仓库主要用于：
- 存放零散代码
- 分配小组成员任务
- 公示统一的平行语料文件格式

**注意：** 对于独立性强、文件数量多、组织结构复杂的任务，我们建议自己建立**独立仓库**来维护代码。

## [平行语料是什么？](https://en.wikipedia.org/wiki/Parallel_text)

## 招募成员

### 字幕语料任务
- 需求（任一即可）：
    - 有在至少包含中英双语的字幕组工作的经验
    - 拥有相关人脉，能够与字幕数据持有者沟通
- 详情：[字幕语料任务](https://github.com/liyongsea/parallel_corpus_mnbvc/issues/77)
### 歌词语料任务
- 需求（任一即可）：
    - 曾在任意平台收集过含中英双语的歌词，手头有相关数据
    - 了解歌词版权相关问题
- 详情：[歌词语料任务](https://github.com/liyongsea/parallel_corpus_mnbvc/issues/92)
### 游戏语料任务
- 需求（任一即可）：
    - 热爱游戏，拥有丰富的游戏库，愿意提供大型游戏包体或者账号
    - 有时间研究游戏解包，提取本地化数据
- 详情：[游戏语料任务](https://github.com/liyongsea/parallel_corpus_mnbvc/issues/82)
### 探索其它平行语料
- 需求：
    - 有充足的时间进行网上冲浪
    - 能够理解平行语料是什么
    - 习惯于 markdown 语法，能够为其它成员调研、收集可以下手的网站链接


> 有其它任务的idea？欢迎来issues区提问开坑！

## 加入方式

1. 先去 [MNBVC 总仓库](https://github.com/esbatmop/MNBVC) 了解一下项目总体情况
2. 发送申请邮件至: MNBVC@253874.net 内容简要写写自己愿意做哪块工作即可
3. 通过后会拉微信小群，有后续问题直接在小群提问即可。在小群内讨论工作内容，每周六 16:00 同步一下进度

## 常用链接

[平行语料小组 wiki](https://wiki.mnbvc.org/doku.php/pxyl)

[语料格式检查工具 DataCheck_MNBVC](https://github.com/X94521/DataCheck_MNBVC)

[临时文件微云共享站](https://www.weiyun.com/disk/sharedir/e653b09abec4e5e80bb454ef6b7f202b), 加入微信小组群方可获得加入共享组链接

## 组织规范

- 每周六 16:00 组织例会同步进度
- 以 Issues 来管理进度、分配任务
- 对于每个独立的任务如果需要传至本仓库，请建一个能够用小写英文+数字+下划线的，能够说明任务内容的文件夹，然后提起 pull request，并且在该文件夹下建立一个 README 来介绍上传内容
- 微信群内发出来的文件，如果是重要的需要在未来下载的，应该在共享站内也传一份

## 语料文件格式

语料文件是多行 `jsonl` 格式，这是其中一行的样例（实际上一行即为一个json，不需要缩进打印）：
```json
{
    "文件名": "Terraria-workshop-localization_test2.jsonl",
    "是否待查文件": false,
    "是否重复文件": false,
    "段落数": 17944,
    "去重段落数": 0,
    "低质量段落数": 0,
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
    "id_text":"",
    "cht_text":"",
    "vi_text":"",
    "扩展字段": "{\"other_texts\": {\"cs\": \"Generování mořského písku\", \"pl\": \"Generowanie piasku morskiego\", \"hu\": \"Tengeri homok elhelyezése\", \"uk\": \"Генерація океанського піску\", \"tr\": \"Okyanus kumu üretme\"}}",
    "时间": "20240316",
    "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2"
}
```

为了防止迷惑，这里给出一份实际上已收录的 `底特律：变人` 的语料的前三行样例：

```json
{"ar_text": "", "cht_text": "我不認為我們還能找到比這裡更好的……", "de_text": "Wir werden nichts Besseres finden ...", "en_text": "I don't think we'll find anything better…", "eo_text": "", "es_text": "No encontraremos nada mejor.", "fr_text": "Je doute qu'on trouve mieux que ça.", "he_text": "", "id_text": "", "it_text": "Sarà difficile trovare di meglio...", "ja_text": "ここが一番マシそうね", "ko_text": "여기보다 나은 곳은 없는 것 같아...", "nl_text": "Ik denk niet dat we iets beters zullen vinden.", "pt_text": "Não vamos encontrar melhor do que isto...", "ru_text": "Вряд ли мы найдем что-то лучше.", "sv_text": "Jag tror inte att vi kommer hitta något bättre än så här.", "th_text": "", "vi_text": "", "zh_text": "我不认为我们还能找到比这里更好的……", "zh_text_md5": "dfa2ca6972a916ec64680d8f1453f85c", "低质量段落数": 0, "去重段落数": 2102, "扩展字段": "{\"other_texts\": {\"cs\": \"Myslím, že nic lepšího nenajdeme.\", \"da\": \"Vi finder nok ikke noget bedre.\", \"el\": \"Δεν νομίζω ότι θα βρούμε κάτι καλύτερο από αυτό...\", \"es_MX\": \"No creo que encontremos algo mejor...\", \"fi\": \"En usko, että löydämme mitään parempaakaan...\", \"hu\": \"Nem hiszem, hogy találunk ennél jobbat.\", \"nb\": \"Jeg tror ikke vi finner noe bedre enn dette.\", \"pl\": \"Nic lepszego raczej nie znajdziemy...\", \"pt_BR\": \"Não vamos encontrar um lugar melhor...\", \"sl\": \"\", \"tr\": \"Daha iyisini bulacağımızdan şüpheliyim...\"}}", "文件名": "DetroitBecomeHuman-parallel_corpus.jsonl", "时间": "20241001", "是否待查文件": false, "是否跨文件重复": false, "是否重复": false, "是否重复文件": false, "段落数": 12407, "行号": 1}
{"ar_text": "", "cht_text": "就在這裡過夜吧。", "de_text": "Machen wir‘s uns gemütlich.", "en_text": "Let's settle in for the night.", "eo_text": "", "es_text": "Nos quedaremos hoy aquí.", "fr_text": "Installons-nous pour la nuit.", "he_text": "", "id_text": "", "it_text": "Passeremo la notte qui.", "ja_text": "ここで寝ましょう", "ko_text": "오늘 밤은 여기서 보내자.", "nl_text": "Laten we hier vannacht blijven.", "pt_text": "Vamos instalar-nos para a noite.", "ru_text": "Будем ночевать здесь.", "sv_text": "Vi får slå oss ned för natten.", "th_text": "", "vi_text": "", "zh_text": "就在这里过夜吧。", "zh_text_md5": "59bbf0b5cef5cd943cd0ba59acd1e7c4", "低质量段落数": 0, "去重段落数": 2102, "扩展字段": "{\"other_texts\": {\"cs\": \"Tak se na noc utáboříme tady.\", \"da\": \"Lad os sove her.\", \"el\": \"Ας μείνουμε εδώ τη νύχτα.\", \"es_MX\": \"Instalémonos por hoy.\", \"fi\": \"Asetutaan tänne yöksi.\", \"hu\": \"Húzódjunk be éjszakára.\", \"nb\": \"Vi slår oss ned her for natten.\", \"pl\": \"Spróbujmy się rozgościć.\", \"pt_BR\": \"Vamos ficar aqui.\", \"sl\": \"\", \"tr\": \"Bu gecelik yerleşelim.\"}}", "文件名": "DetroitBecomeHuman-parallel_corpus.jsonl", "时间": "20241001", "是否待查文件": false, "是否跨文件重复": false, "是否重复": false, "是否重复文件": false, "段落数": 12407, "行号": 2}
{"ar_text": "", "cht_text": "我來生火。", "de_text": "Ich mache ein Feuer an.", "en_text": "I'll get a fire going.", "eo_text": "", "es_text": "Encenderé un fuego.", "fr_text": "Je vais faire du feu.", "he_text": "", "id_text": "", "it_text": "Accendo un fuoco.", "ja_text": "火をおこすよ", "ko_text": "내가 불 피울게.", "nl_text": "Ik zal vuur maken.", "pt_text": "Vou fazer uma fogueira.", "ru_text": "Я разведу огонь.", "sv_text": "Jag tänder en brasa.", "th_text": "", "vi_text": "", "zh_text": "我来生火。", "zh_text_md5": "552f113da3617f26fa2c6ca9dfa21836", "低质量段落数": 0, "去重段落数": 2102, "扩展字段": "{\"other_texts\": {\"cs\": \"Rozdělám oheň.\", \"da\": \"Jeg tænder et bål.\", \"el\": \"Θα ανάψω φωτιά.\", \"es_MX\": \"Yo prenderé una fogata.\", \"fi\": \"Minä sytytän tulen.\", \"hu\": \"Gyújtok tüzet.\", \"nb\": \"Jeg tenner opp.\", \"pl\": \"Zajmę się ogniskiem.\", \"pt_BR\": \"Vou acender o fogo.\", \"sl\": \"\", \"tr\": \"Ben ateşle uğraşayım.\"}}", "文件名": "DetroitBecomeHuman-parallel_corpus.jsonl", "时间": "20241001", "是否待查文件": false, "是否跨文件重复": false, "是否重复": false, "是否重复文件": false, "段落数": 12407, "行号": 3}
```

**注意：** 所有语种字段的双字母缩写优先参考 [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) 的定义，并且优先填写如 `ar_text` 的主要字段中，如果没有，则根据 iso 双字母简写填入扩展字段中。如果所收录语言并不在 iso 639-1 双字母简写表中，请自己起一个不与其他双字母简写有冲突的key名写到扩展字段中，并将其 key 名和对应的语种作为注释写到文件级扩展字段中。

实际语料样例：
- [杀戮尖塔](corpus_sample/slay_the_spire.jsonl)
- [泰拉瑞亚](corpus_sample/Terraria-workshop-and-vanilla.jsonl)

### 字段定义

**文件名**: 建议和输出的 jsonl 文件名保持一致。对于每份独立的语料，以文件名为唯一依据。每份文件独立计算的 `时间`, `是否待查文件`, `是否跨文件重复`, `是否重复`, `是否重复文件`, `段落数`,  `低质量段落数`,  `去重段落数` 会随文件名冗余多份，保证文件名相等的情况下这几个字段结果相等。所以建议取一个**能够精确描述这份语料来源**的文件名。

**是否待查文件**: 如果是 True 就是不怎么靠谱，告诉大家尽量别用，平行语料小组收录的语料的此字段若无特殊情况将**全部给 False**

**是否重复文件**: 留给其它小组的进行去重工作的字段，平行语料小组收录的语料的此字段将**全部给 False**

**段落数**: 等于整份文件中jsonl的行数

**去重段落数**: 以 `zh_text` 为依据，“重复了的段落”的个数，注意**不是去重后不同的段落个数**

**低质量段落数**: `zh_text` 或者 `en_text` 有缺（为空字符串）的段落数量

**行号**: 段落下标，是一个取值范围在 `[1, 段落数]` 之间的整数

**是否重复**: 由 `zh_text` 是否重复来决定，每个非重复段落第一次出现时是 False, 此后再次出现发现已重复时是 True

**是否跨文件重复**: 留给其它小组的进行去重工作的字段，平行语料小组收录的语料的此字段将**全部给 False**

**时间**: `yyyymmdd` 格式的日期字符串，表示这份语料被转换为本文所定义的标准平行语料格式的时间。可以参考样例

### 关于扩展字段

扩展字段应该是 json 序列化后的字符串，如在 python3 中，应该是某个 `json.dumps(obj, ensure_ascii=False)` 的产物。

目前的扩展字段约定如下：

```python
{
    other_texts: { # 填写主字段中没有的，但源数据中存在的其它语言
        {lang1_iso}: "",
        {lang2_iso}: ""
    },
    k: "_SCENE1_TEXT_TITLE" # 可选，如果有必要的话，可以用于填写源数据中的 key，即对齐依据
    ...
}
```

**注意：** 扩展字段内容的定义可能会频繁更新，但至少需要是一个有效的 json 字符串。即使没有东西填写，也应该保留一个 `{}`。

### 添加新的语料数据集的规范

1. 复制以下模板，你的脚本或者你的方法应该尽可能填写其中未标明 `【不用手填】` 的所有字段。如果某个主字段中的语言没有出现，则应该填写 `""` 。

```json
{
    "文件名": "Terraria-workshop-localization_test2.jsonl",
    "是否待查文件": false,      【不用手填】
    "是否重复文件": false,      【不用手填】
    "段落数": 17944,            【不用手填】
    "去重段落数": 0,            【不用手填】
    "低质量段落数": 0,          【不用手填】
    "行号": 1,                  【不用手填】
    "是否重复": false,          【不用手填】
    "是否跨文件重复": false,    【不用手填】
    "zh_text_md5": "b656579704c6ca5acc29f2aa36159ce2",   【不用手填】
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
    "id_text":"",
    "cht_text":"",
    "vi_text":"",
    "扩展字段": "{\"other_texts\": {\"cs\": \"Generování mořského písku\", \"pl\": \"Generowanie piasku morskiego\", \"hu\": \"Tengeri homok elhelyezése\", \"uk\": \"Генерація океанського піску\", \"tr\": \"Okyanus kumu üretme\"}}",
    "时间": "20240316"
}
```

**注意：** 出于小组工作性质，我们应该收录的是至少包含 **简体中文或繁体中文** 且包含对应的 **英文** 的语料。

2. 将得到的语料通过本仓库下的 [jsonl_chk.py](jsonl_chk.py) 的后处理，以完成简单去重和 `【不用手填】` 字段的自动填写，用法为 `python out.jsonl` 或者用 `python -d outdir/` 的方式处理整个目录下的 jsonl 文件。在其 `jsonl_rework` 文件夹下会得到后处理完毕的 jsonl 文件。

3. 将得到的语料通过 [语料格式检查工具 DataCheck_MNBVC](https://github.com/X94521/DataCheck_MNBVC) 的检测，`python check_data.py --dataset your_folder_path`，其中 `your_folder_path` 为待检测语料数据所在的文件夹。

> datachecker执行完毕后，如果日志文件 ``\logs\check_log.txt`` 显示：
> 
> ```
> checking dataset: your_file_path
> the type of dataset your_file_name is 平行语料格式
> check dataset your_file_name finished, right line 1 / total check line 1
> ```
> 
> 则表示格式检测通过

4. 带着第 3 步通过的截图在小组群内发布你的 jsonl 语料，并且在中转站中传一份避免日后丢失。


<details> <summary>【旧版语料，已废弃】</summary>

```json
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

</details>