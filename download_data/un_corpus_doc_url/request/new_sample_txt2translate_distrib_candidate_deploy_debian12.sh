apt update
apt install -y python3-pip python3-full
python3 -m venv MT
cd MT
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/refs/heads/pipeline_rework/download_data/un_corpus_doc_url/request/new_sample_txt2translate_distrib_candidate_client.py
bin/pip install argostranslate requests
# 改地址
nano new_sample_txt2translate_distrib_candidate_client.py
nohup bin/python new_sample_txt2translate_distrib_candidate_client.py &


# google cloud shell
cd /root
wget https://raw.githubusercontent.com/liyongsea/parallel_corpus_mnbvc/refs/heads/pipeline_rework/download_data/un_corpus_doc_url/request/new_sample_txt2translate_distrib_candidate_client.py
# 改地址
nano new_sample_txt2translate_distrib_candidate_client.py
apt update
apt install -y python3-pip python3-full screen
pip3 install argostranslate requests
screen -dmS mt bash -c 'python3 new_sample_txt2translate_distrib_candidate_client.py'