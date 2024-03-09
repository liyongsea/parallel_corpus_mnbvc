import uno
from com.sun.star.beans import PropertyValue

INPUT_WPF = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.wpf'
OUTPUT_DOCX = r'C:\Users\ATRI\Desktop\parallel_corpus_mnbvc\convert_data\temp.docx'

# 初始化LibreOffice连接
localContext = uno.getComponentContext()
resolver = localContext.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", localContext)
context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
desktop = context.ServiceManager.createInstanceWithContext(
    "com.sun.star.frame.Desktop", context)

# 打开WPS文件
input_file_path = INPUT_WPF
doc = desktop.loadComponentFromURL(input_file_path, "_blank", 0, ())

if doc is not None:
    try:
        # 构建输出文件的完整路径
        output_file_path = OUTPUT_DOCX

        # 配置保存参数
        save_props = (PropertyValue("FilterName", 0, "MS Word 2007 XML"),)

        # 保存文档为docx格式
        doc.storeToURL(output_file_path, save_props)

        # 关闭文档
        doc.close(True)
        print("Conversion completed successfully.")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Error: Unable to open the input document.")

# 退出LibreOffice连接
desktop.terminate()
