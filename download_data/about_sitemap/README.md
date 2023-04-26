# Install the requirements
```bash
pip install -r requirements.txt

```

## Command Line Syntax:

### download_all_pdf_url.py

从 "https://digitallibrary.un.org/sitemap_index.xml.gz" 作为根url下载所有的sitemap，并把sitemap中所有的url保存到本地为"SixLanguagePDF-URLS.json"的文件中

    > download_all_pdf_url.py [--file_save_dir FILE_SAVE_DIR]

  * `--file_save_dir FILE_SAVE_DIR` : json文件保存的文件夹路径，默认"./download_pdf"

### get_pdf_link_information.py

解析由"download_all_pdf_url.py"生成的JSON文件，并通过网络下载相应的html资源来获得pdf文件的详细信息，并保存到本地为"SixLanguageURL-Information.json"的文件中

    > get_pdf_link_information.py [--file_save_dir FILE_SAVE_DIR]
                      [--downloaded_pdf_url_dir DOWNLOADED_PDF_URL_DIR]
                      [--erroe_file_local ERROE_FILE_LOCAL]
                      [--worker_thread WORKER_THREAD]

  * `--file_save_dir FILE_SAVE_DIR` : json文件保存的文件夹路径，默认"./download_pdf"
  * `--downloaded_pdf_url_dir DOWNLOADED_PDF_URL_DIR` : 由"download_all_pdf_url.py"生成的文件夹路径
  * `--erroe_file_local ERROE_FILE_LOCAL` : 网络错误的url文件保存路径，默认"./error_url.txt"
  * `--worker_thread WORKER_THREAD` : 并行线程数，默认0 | 0:根据cpu核心数决定线程（1:1）| 其余:线程数等于"--worker_thread"填入的数量

### make_pdf_information_dataset_and_upload.py

制作pdf链接信息的datasets，并上传到huggingface

    > get_pdf_link_information.py [--datasets_repository DATASETS_REPOSITORY] 
                      [--token TOKEN] 
                      [--file_saved_dir FILE_SAVED_DIR]

  * `--datasets_repository DATASETS_REPOSITORY` : huggingface的仓库名（可以不创建仓库，直接上传，会自动创建）
  * `--token TOKEN` : huggingface的'Access Tokens'，在huggingface的profile中选择'Access Tokens'可查看
  * `--file_saved_dir FILE_SAVED_DIR` : 由'get_pdf_link_information'脚本保存的json文件的文件夹路径     



### download_after_2000_year_pdf_to_loacl.py

从huggingfase的仓库下载有关于2000年之后的pdf url

    > download_after_2000_year_pdf_to_loacl.py [--file_save_dir FILE_SAVE_DIR] 
                      [--erroe_file_local ERROE_FILE_LOCAL] 
                      [--worker_thread WORKER_THREAD]

  * `--file_save_dir FILE_SAVE_DIR` : json文件保存的文件夹路径，默认"./download_pdf"
  * `--erroe_file_local ERROE_FILE_LOCAL` : 网络错误的url文件保存路径，默认"./error_url.txt"
  * `--worker_thread WORKER_THREAD` : 并行线程数，默认0 | 0:根据cpu核心数决定线程（1:1）| 其余:线程数等于"--worker_thread"填入的数量


### translate_pdf_to_text.py

将下载下来的pdf转化成文字并保存

    > download_after_2000_year_pdf_to_loacl.py [--downloaded_pdf_path DOWNLOADED_PDF_PATH] [--pdf_text_save_dir_path PDF_TEXT_SAVE_DIR_PATH]

  * `--downloaded_pdf_path DOWNLOADED_PDF_PATH` : 下载的pdf文件位置，默认"./download_pdf"
  * `--pdf_text_save_dir_path PDF_TEXT_SAVE_DIR_PATH` : 保存的pdf中text文件的位置，默认"./pdf_text"
