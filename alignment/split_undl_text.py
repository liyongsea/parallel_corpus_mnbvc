from transformers import AutoTokenizer
import datasets
from datasets import Features, Value
from tqdm import tqdm
from multiprocessing import Pool
import re
import json


MODEL_NAME_MAP = {
    "de": "Helsinki-NLP/opus-mt-de-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en",
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "ar": "Helsinki-NLP/opus-mt-ar-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
    "es": "Helsinki-NLP/opus-mt-es-en",
}

MODEL_MAP = {}

SPLIT_SYMBOLS_MAP = {
    "zh": ["\n", "。", "；", ":", ",", " "],
    "de": ["\n", ".", ";", ":", ",", " "],
    "fr": ["\n", ".", ";", ":", ",", " "],
    "ar": ["\n", "،", ";", ".", ":", " "],
    "ru": ["\n", ".", ";", ":", ",", " "],
    "es": ["\n", ".", ";", ":", ",", " "],
}

FEATURES = Features(
    {
        "id": Value("string"),
        "content": Value("string"),
        "token_total": Value("int32"),
        "split_symbol": Value("string"),
        "record": Value("string"),
        "source": Value("string"),
        "target": Value("string"),
    }
)


def split_sentence(sentence, tokenizer, lang, token_limit=512):
    """
    将一个句子分成若干块，每块的token数量不超过token_limit。
    尝试使用不同的分隔符来拆分句子。
    """
    split_symbols = SPLIT_SYMBOLS_MAP.get(lang)

    for split_symbol in split_symbols:
        chunks = sentence.split(split_symbol)

        if len(chunks) == 1:
            continue

        chunked_results = []
        current_content = ""
        current_tokens = 0

        for chunk in chunks:
            tokens = tokenizer.encode(chunk)
            added_tokens = len(tokens) + (
                len(tokenizer.encode(split_symbol)) if current_content else 0
            )

            # 如果当前块与新的块合并后不超过token限制，则合并它们。
            if current_tokens + added_tokens <= token_limit:
                current_content += (split_symbol if current_content else "") + chunk
                current_tokens += added_tokens
            else:
                # 否则，保存当前块并开始一个新的块。
                if current_content:
                    chunked_results.append(
                        {
                            "content": current_content,
                            "token_total": tokenizer.encode(current_content),
                            "split_symbol": split_symbol,
                        }
                    )
                current_content = chunk
                current_tokens = len(tokens)

        # 添加最后一个块。
        if current_content:
            chunked_results.append(
                {
                    "content": current_content,
                    "token_total": tokenizer.encode(current_content),
                    "split_symbol": split_symbol,
                }
            )

        # 确保所有块的大小都不超过token限制。
        if chunked_results and all(
            [len(chunk["token_total"]) <= token_limit for chunk in chunked_results]
        ):
            return chunked_results

    return [
        {
            "content": sentence,
            "token_total": len(tokenizer.encode(sentence)),
            "split_symbol": "",
        }
    ]


def split_text_into_chunks(text, tokenizer, lang, token_limit=512):
    """
    将文本分成若干块，每块的token数量不超过token_limit。
    这是通过首先按段落拆分文本，然后进一步拆分长段落来实现的。
    """
    paragraphs = text.split("\n\n")
    results = []

    for index, para in enumerate(paragraphs):
        tokens = tokenizer.encode(para)

        # 如果段落的token数量小于token限制，直接添加到结果中。
        if len(tokens) < token_limit:
            results.append(
                {
                    "id": str(index),
                    "content": para,
                    "token_total": len(tokens),
                    "split_symbol": "\n\n",
                }
            )
        else:
            # 否则，进一步拆分段落。
            chunks = split_sentence(para, tokenizer, lang, token_limit)
            for idx, chunk in enumerate(chunks):
                results.append(
                    {
                        "id": f"{index}-{idx}",
                        "content": chunk["content"],
                        "token_total": len(chunk["token_total"]),
                        "split_symbol": chunk["split_symbol"],
                    }
                )

    return results


def reconstruct_text(chunks):
    """
    还原原始文章
    """
    reconstructed = []
    current_paragraph = []
    current_parent_id = None

    for chunk in chunks:
        id_split = chunk["id"].split("-")
        parent_id = id_split[0]

        if parent_id != current_parent_id:
            if current_paragraph:
                reconstructed.append(current_paragraph)
            current_paragraph = []
            current_parent_id = parent_id

        current_paragraph.append(chunk)

    if current_paragraph:
        reconstructed.append(current_paragraph)

    completed_reconstructed = []
    for arr_para in reconstructed:
        if len(arr_para) == 1:
            completed_reconstructed.append(arr_para[0]["content"])
        else:
            content = ""
            for para in arr_para:
                content += (para["split_symbol"] if content else "") + para["content"]
            completed_reconstructed.append(content)

    return completed_reconstructed


def clean_paragraph(paragraph):
    lines = paragraph.split("\n")
    para = ""
    table = []

    for line in lines:
        line = line.strip()

        # 表格线或其他分割线
        if re.match(r"^(\+[-=+]+\+|-+|=+|_+)$", line):
            if not para.endswith("\n"):
                para += "\n"
            if len(table) > 0:
                para += "\t".join(table)
                table = []

        # 表格中的空行
        elif re.match(r"^\|( +\|)+$", line):
            para += "\t".join(table) + " "
            table = []

        # 表格中的内容行
        elif re.match(r"^\|([^|]+\|)+$", line):
            if len(table) == 0:
                table = line[1:-2].split("|")
            else:
                arr = line[1:-2].split("|")
                if len(arr) == len(table):
                    table = [
                        table[i].strip() + arr[i].strip() for i in range(len(table))
                    ]
                elif len(arr) > len(table):
                    table = [
                        table[i].strip() + arr[i].strip()
                        if i < len(table)
                        else arr[i].strip()
                        for i in range(len(arr))
                    ]
                else:
                    table = [
                        table[i].strip() + arr[i].strip()
                        if i < len(arr)
                        else table[i].strip()
                        for i in range(len(table))
                    ]
        # 正文内容
        else:
            para += " " + line

    if len(table) > 0:
        if not para.endswith("\n"):
            para += "\n"

        para += "\t".join(table)


    return re.sub(r"[ \t]{2,}", " ", re.sub(r"\n{2,}", "\n", para)).strip()


def clean_dashes_in_line(line):
    """清理线中的“-”字符。"""
    num_dashes = line.count("-")
    if num_dashes / len(line) >= 0.2:
        line = line.replace("-", " ")
    return line


def process_paragraph(paragraph):
    """处理段落中的“-”字符并返回处理后的段落。"""
    lines = paragraph.splitlines()

    modified_lines = []
    for line in lines:
        modified_line = clean_dashes_in_line(line)
        if modified_line.strip() != "":
            modified_lines.append(modified_line)

    return "\n".join(modified_lines)

def preprocess(text):
    """预处理文本，清理段落和行中的“-”字符，并保存已舍弃的内容。"""
    cleaned_paragraphs = [clean_paragraph(para) for para in text.split("\n\n")]
    cleaned_paragraphs = list(filter(lambda x: x.strip() != "" and x != "[]", cleaned_paragraphs))

    processed_paragraphs = [process_paragraph(para) for para in cleaned_paragraphs]
    processed_paragraphs = list(filter(lambda x: x.strip() != "", processed_paragraphs))
   

    return "\n\n".join(processed_paragraphs)


def process_row(row):
    """
    根据输入的dataset row，处理其内容并为每种语言分块。

    返回:
        list: 包含处理后的文本块的列表。

    示例:
        输入： {"record": 123, "en": "English text", "zh": "中文文本", ...}
        输出： [{'content': '中文文本', 'record': 123, 'source': 'zh', 'target': 'en', 'id': 1, 'split_symbol': '\n\n', 'token_total': 512}]
    """
    results = []

    record = row["record"]
    for lang, content in row.items():
        if lang in ["en", "record"]:
            continue

        if content.strip() == "":
            continue

        processed_text = preprocess(content)
        tokenizer = MODEL_MAP[lang]
        chunks = split_text_into_chunks(processed_text, tokenizer, lang)

        for chunk in chunks:
            chunk.update({"record": record, "source": lang, "target": "en"})
            results.append(chunk)

    return results


def unique_items_generator(data_list):
    """
    根据token < 10的数据去重
    """
    seen_contents = set()
    for item in data_list:
        if item["content"] not in seen_contents:
            yield item

        if len(item["content"]) < 10:
            seen_contents.add(item["content"])


def generator_wrapper(data_to_process):
    def generator():
        return unique_items_generator(data_to_process)

    return generator


if __name__ == "__main__":
    dataset = datasets.load_dataset("bot-yaya/undl_text", split="train[:100]")

    for lang, model in MODEL_NAME_MAP.items():
        tokenizer = AutoTokenizer.from_pretrained(model)
        MODEL_MAP[lang] = tokenizer

    with Pool(8) as p:
        result_total = list(tqdm(p.imap(process_row, dataset), total=len(dataset)))

    flattened_result = [item for sublist in result_total for item in sublist]

    # results = []
    # for index, row in tqdm(enumerate(dataset)):
    #     results += process_row(row)

    new_dataset = datasets.Dataset.from_generator(
        generator_wrapper(flattened_result), features=FEATURES
    )
    new_dataset.save_to_disk("./split_undl_text_dataset")
