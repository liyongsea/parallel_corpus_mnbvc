# Install the requirements
```
pip install -r requirements.txt
```

# start 

> 1.  Install the requirements
> 
> 2.  configure wandb
>
> - 打开 https://wandb.ai/ 网站，并登录到你的账户。
> 
> - 在页面的左上角，点击你的用户名，然后选择 "Account settings"（账户设置）选项。
> 
> - 在 "Account settings" 页面上，你将看到一个名为 "API keys"（API密钥）的选项。复制它，如果没有则创建它。
> 
> - bash> wandb login --relogin
>
> - 在展示"wandb: Paste an API key from your profile and hit enter, or press ctrl+c to quit:"时，粘贴key，并按下Enter
> 
> 3. 测试: ```bash> python ./alone_file_segmenter/detection_builder.py --concurrent_number=10```
>
> - 如输出"test success“测试成功
> 
> 4. 生产：```bash> python ./alone_file_segmenter/single_file_segment_builder.py --key=sk-xxxxxx --test_mode=0 (如果并发，按照这个命令调用即可)```





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