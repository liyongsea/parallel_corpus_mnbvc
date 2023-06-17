# Install the requirements
```
pip install -r requirements.txt
```


### 目录结构

> |------ single_file_segment_builder.py        启动脚本
> 
> |------ record_index_map.py           record对应一些相关状态/数据的映射表
>
> |------ detection_builder.py   并发测试
> 
> |------ record_index_map.json.lock    锁控制文件
>

## single_file_segment_builder.py

#### shell:

```shell
python single_file_segment_builder.py --key=sk-xxxxxx --test_mode=0
```

#### options:

  --key  openai的apiKey（必填）

  --test_mode 是否测试此脚本 （0/false）default=0


## detection_builder.py 

#### illustrate:

测试并发调用生产脚本的脚本，目前的脚本内容为并发是否可以拿到不同的record，并且是否造成'record_index_map.json'文件损坏，以及参数传递的apikey是否不同

#### shell:

```shell
python detection_builder.py --concurrent_number=10
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