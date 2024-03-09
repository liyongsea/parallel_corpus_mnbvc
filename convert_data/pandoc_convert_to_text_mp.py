import os
import multiprocessing as mp
from pathlib import Path 



WORKERS = 8
SOURCE_DOCX_DIR = r'E:\doc2docxWD\docxoutput'
OUTPUT_DIR = r'E:\doc2docxWD\docxoutput_text'

def cv(q: mp.Queue):
    while 1:
        filepath = q.get()
        if filepath is None:
            break
        outp = os.path.join(OUTPUT_DIR, f"{filepath[:-4]}txt")
        filepath = os.path.join(SOURCE_DOCX_DIR, filepath)
        if not os.path.exists(outp):
            r = os.system(f"pandoc -i {filepath} -t plain -o {outp} --strip-comments")
            # print('done', outp)
        else:
            pass
            # print('skip', outp)
    # print(r.read())

if __name__ == '__main__':
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    mgr = mp.Manager()
    q = mgr.Queue(WORKERS + 1)
    ps = [
        mp.Process(target=cv, args=(q,)) for _ in range(WORKERS)
    ]
    for x in ps:
        x.start()

    for idx, i in enumerate(os.listdir(SOURCE_DOCX_DIR)):
        # dirpath = os.path.join(SOURCE_DOCX_DIR, i)
        # for j in os.listdir(dirpath):
        # filepath = os.path.join(SOURCE_DOCX_DIR, i)
        q.put(i)
        print(idx, i)

    for _ in ps:
        q.put(None)
    
    for x in ps:
        x.join()
    


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
            