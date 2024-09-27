apt update
apt install -y python3-pip python3-full
python3 -m venv MT
cd MT
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/refs/heads/pipeline_rework/download_data/un_corpus_doc_url/request/new_sample_txt2translate_distrib_candidate_client.py
bin/pip install argostranslate requests
nohup bin/python new_sample_txt2translate_distrib_candidate_client.py &
