# Install the requirements
```bash
pip install -r requirements.txt

```

## How to Use:

  1. download_all_pdf_url
     `> python ./download_all_pdf_url.py`

  2. get_pdf_link_information
     `> python ./get_pdf_link_information.py`

## Command Line Syntax:

### download_all_pdf_url.py

从 "https://digitallibrary.un.org/sitemap_index.xml.gz" 作为根url下载所有的sitemap，并把sitemap中所有的url保存到本地为"SixLanguagePDF-URLS.json"的文件中

    > download_all_pdf_url.py [--file_save_dir FILE_SAVE_DIR]

  * `--file_save_dir FILE_SAVE_DIR` : json文件保存的文件夹路径，默认"./download_pdf"

### get_pdf_link_information.py

解析由"download_all_pdf_url.py"生成的JSON文件，并通过网络下载相应的html资源来获得pdf文件的详细信息，并保存到本地为"SixLanguageURL-Information.json"的文件中

    > sort_by_time.py [--file_save_dir FILE_SAVE_DIR]
                      [--downloaded_pdf_url_dir DOWNLOADED_PDF_URL_DIR]
                      [--erroe_file_local ERROE_FILE_LOCAL]
                      [--worker_thread WORKER_THREAD]

  * `--file_save_dir FILE_SAVE_DIR` : json文件保存的文件夹路径，默认"./download_pdf"
  * `--downloaded_pdf_url_dir DOWNLOADED_PDF_URL_DIR` : 由"download_all_pdf_url.py"生成的文件夹路径
  * `--erroe_file_local ERROE_FILE_LOCAL` : 网络错误的url文件保存路径，默认"./error_url.txt"
  * `--worker_thread WORKER_THREAD` : 并行线程数，默认0 | 0:根据cpu核心数决定线程（1:1）| 1:单线程 | 其余:线程数等于"--worker_thread"填入的数量
