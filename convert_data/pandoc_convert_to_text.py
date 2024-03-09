import os
import docx

SOURCE_DOCX_DIR = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\sample_100'

for i in os.listdir(SOURCE_DOCX_DIR):
    dirpath = os.path.join(SOURCE_DOCX_DIR, i)
    for j in os.listdir(dirpath):
        filepath = os.path.join(dirpath, j)
        print(f"pandoc -i {filepath} -t plain > {filepath}.txt")
        r = os.popen(f"pandoc -i {filepath} -t plain > {filepath}.txt")
        print(r.read())

    
    # os.system(f'pandoc -i {fp} -t plain > {fp}.txt')
    # fp = os.path.join(SOURCE_DOCX_DIR, '中文-2210193C.docx')
    # d = docx.Document(fp)

    # for paragraph in d.paragraphs:
    #     for blk in paragraph._element.xpath(".//w:r"):
    #         lnk = blk.xpath(".//w:hyperlink", namespaces=blk.nsmap)
    #         if lnk:

    #     [[link.xpath("w:r",namespaces=link.nsmap)[0].text for link in paragraph._element.xpath(".//w:hyperlink")] for run in paragraph.runs]
    #     text_block = paragraph.text
    #     if text_block.strip():  # 确保文本块不是空白行
    #         print(text_block)
            