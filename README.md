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
