apt install -y python3-pip python3-full
python3 -m venv MT
cd MT
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/doc2docx/alignment/align_undl_text/tr_client_argostranslate.py
bin/pip install argostranslate requests
nohup bin/python tr_client_argostranslate.py &
