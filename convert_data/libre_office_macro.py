
import uno
import os
import pickle
import re
import shutil

from com.sun.star.beans import PropertyValue

def wpf_to_docx():
    BASE_DIR = r'E:\doc2docxWD'
    ERR_LOG_DIR = BASE_DIR + r'\err'
    SOURCE_DIR = BASE_DIR + r'\MNBVC—UN文件'
    SAVED_DIR = BASE_DIR + r'\wpf_libre_converted'
    RECOVER_DIR = BASE_DIR + r'\wpf_err_recovered'

    GROUP_CACHE_DIR = BASE_DIR + r'\wpf_mapping.pkl'
    
    def err_path(file_abs): return os.path.join(ERR_LOG_DIR, re.sub(r'\.\w+$', '.wpf', file_abs.split('\\')[-1]))
    def recover_path(file_abs): return os.path.join(RECOVER_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))
    def saved_path(file_abs): return os.path.join(SAVED_DIR, re.sub(r'\.\w+$', '.docx', file_abs.split('\\')[-1]))
    def lock_path(file_abs): return os.path.join(SAVED_DIR, '.~lock.' + re.sub(r'\.\w+$', '.docx#', file_abs.split('\\')[-1]))

    todo = set()
    with open(GROUP_CACHE_DIR, 'rb') as f:
        wpf_mapping = pickle.load(f)

    for subdir, filenames in wpf_mapping.items():
        for dfn in filenames:
            absfn = os.path.join(SOURCE_DIR, subdir, dfn)
            if not os.path.exists(recover_path(absfn)) : # and not os.path.exists(err_path(absfn))
                todo.add(os.path.join(subdir, dfn))

    # 初始化LibreOffice连接
    ctx = uno.getComponentContext()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    open_mode = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    open_mode.Name = "ReadOnly"
    open_mode.Value = True
    save_props = (
        PropertyValue("FilterName", 0, "Office Open XML Text", 0),
        PropertyValue("Overwrite", 0, True, 0),
    )

    # INPUT_WPF = r'file:///C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.wpf'
    # OUTPUT_DOCX = uno.systemPathToFileUrl(r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.docx')
    for task in todo:
        task = os.path.join(SOURCE_DIR, task)
        if os.path.exists(saved_path(task)) or os.path.exists(lock_path(task)) or os.path.exists(err_path(task)):
            continue
        # 打开WPS文件
        shutil.copy(task, err_path(task))
        input_file_path = uno.systemPathToFileUrl(task)
        # doc = desktop.loadComponentFromURL(input_file_path, "_blank", 0, ())
        doc = desktop.loadComponentFromURL(input_file_path, "_blank", 0, (open_mode, ))
        # time.sleep(10)

        if doc is not None:
            try:
                # 构建输出文件的完整路径
                output_file_path = uno.systemPathToFileUrl(saved_path(task))

                # 保存文档为docx格式
                doc.storeToURL(output_file_path, save_props)

                # 关闭文档
                doc.close(True)
                print("Conversion completed successfully.")
                os.remove(err_path(task))
            except Exception as e:
                print(f"Error: {e}")
                with open(err_path(task), 'w') as f:
                    f.write(str(e))
        else:
            print("Error: Unable to open the input document.")

    desktop.terminate()


g_exportedScripts = wpf_to_docx,

# vim: set shiftwidth=4 softtabstop=4 expandtab:

