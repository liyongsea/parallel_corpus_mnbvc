## 依赖库（以下依赖不是开发依赖，不可放入requirements）

- wheel: 二进制分发
- twine: pypi上传


## 上传到pypi

### 1 打包

```bash
python setup.py sdist bdist_wheel
```

options:
- sdist 源码分发
- bdist_wheel 二进制分发


### 2 上传

```bash
# 需要有pypi帐号
twine upload dist/*
```

## 使用方式

### 安装

#### 从本地安装
```bash
git clone git@github.com:liyongsea/parallel_corpus_mnbvc.git

cd parallel_corpus_mnbvc

pip install .
```

#### 从pypi安装

```bash
pip install parallel_corpus_mnbvc
```


### 使用

> 例如我想使用alignment中utils的create_chat_prompt方法生成prompt

```python
from parallel_corpus_mnbvc import alignment

prompt = alignment.utils.create_chat_prompt()
```

```python 
# 因为本质是将"alignment"这个包上传到pypi，"parallel_corpus_mnbvc"只作为一个引入脚本使用，所以我们可以直接引入"alignment"(但是这样如果包名与其它依赖产生冲突，则此方案不可以使用)
import alignment

prompt = alignment.utils.create_chat_prompt("")
or------------------------------------------------------------
import alignment.utils as utils

prompt = utils.create_chat_prompt("")
```

```python 
# 但是这种不可以，"parallel_corpus_mnbvc"只作为一个引入脚本使用，并不是包
from parallel_corpus_mnbvc.alignment import utils
```