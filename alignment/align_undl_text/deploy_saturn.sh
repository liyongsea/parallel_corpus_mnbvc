pip3 install argostranslate requests
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/doc2docx/alignment/align_undl_text/tr_client_argostranslate.py
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/doc2docx/alignment/align_undl_text/tr_install_argostranslate.py
python3 tr_install_argostranslate.py
nohup python3 tr_client_argostranslate.py &
