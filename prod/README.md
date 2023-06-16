# Install the requirements
```
pip install -r requirements.txt
```


### 目录结构

> |------ paragraph_assembler.py        启动脚本（main）
> 
> |------ record_index_map.py           record对应一些相关状态/数据的映射表
>
> |------ test_paragraph_assembler.py   并发测试
> 
> |------ record_index_map.json.lock    锁控制文件（脚本内容涉及到修改本地文件并要求原子性）
>

## paragraph_assembler.py

#### shell:

```shell
python paragraph_assembler.py --key=sk-xxxxxx --test=false
```

#### options:

  --key  openai的apiKey（必填）

  --test 是否测试此脚本 （true/false）default=false


## test_paragraph_assembler.py 

#### illustrate:

目前的脚本内容为并发是否可以拿到不同的record，并且是否造成'record_index_map.json'文件损坏

#### shell:

```shell
python test_paragraph_assembler.py --concurrent_number=10
```
options:

  --concurrent_number 并发线程数 default=10


## record_index_map.json

#### 说明：
record映射相关状态以及信息

#### 例子：
```json
{"record": {"processing": "是否正在请求中true/false", "completed": "是否处理完毕true/false", "index": "对应的dataset index"}, ...}
```