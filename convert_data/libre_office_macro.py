
import uno
import time

from com.sun.star.beans import PropertyValue

def wpf_to_docx():
    INPUT_WPF = r'file:///C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.wpf'
    OUTPUT_DOCX = uno.systemPathToFileUrl(r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.docx')

    # 初始化LibreOffice连接
    ctx = uno.getComponentContext()
    # resolver = localContext.ServiceManager.createInstanceWithContext(
        # "com.sun.star.bridge.UnoUrlResolver", localContext)
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    open_mode = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    open_mode.Name = "ReadOnly"
    open_mode.Value = True
    # context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    # desktop = context.ServiceManager.createInstanceWithContext(
    #     "com.sun.star.frame.Desktop", context)

    # 打开WPS文件
    input_file_path = INPUT_WPF
    # doc = desktop.loadComponentFromURL(input_file_path, "_blank", 0, ())
    doc = desktop.loadComponentFromURL(input_file_path, "_blank", 0, (open_mode, ))
    # time.sleep(10)

    if doc is not None:
        try:
            # 构建输出文件的完整路径
            output_file_path = OUTPUT_DOCX
            # time.sleep(10)

            # 配置保存参数
            save_props = (
                PropertyValue("FilterName", 0, "MS Word 2007 XML", 0),
                PropertyValue("Overwrite", 0, True, 0),
            )
            print(dir(save_props))
            # print(dir(PropertyValue))

            # 保存文档为docx格式
            doc.storeToURL(output_file_path, save_props)
            # time.sleep(10)

            # 关闭文档
            doc.close(True)
            print("Conversion completed successfully.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Error: Unable to open the input document.")

    # 退出LibreOffice连接
    desktop.terminate()


g_exportedScripts = wpf_to_docx,

# vim: set shiftwidth=4 softtabstop=4 expandtab:
