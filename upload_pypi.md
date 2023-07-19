## 依赖库（以下依赖不可放入requirements）

- wheel: 二进制分发
- twine: pypi上传


## 指令

### 1 打包

```bash
python setup.py sdist bdist_wheel

```

options:
    sdist 源码分发
    bdist_wheel 二进制分发

### 2 上传

```bash
twine upload dist/*

```