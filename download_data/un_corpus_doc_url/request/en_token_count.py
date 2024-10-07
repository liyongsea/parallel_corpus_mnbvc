import json
import csv


input_jsonl = r'F:\undl_text_file_info.jsonl'

out_para_counter = r'F:\para_counter.csv'

out_token_counter = r'F:\token_counter.csv'

file_cnt = 0
sum_para = 0
sum_token = 0

# file_para_counter = {} # 文件有多少个段落，统计一下 {paracount: filecount}

para_token_counter = {} # 段落有多少个token，统计一下 {tokencount: paracount}

with open(input_jsonl, 'r', encoding='utf-8') as f:
    for line in f:
        file_cnt += 1
        fileresult = json.loads(line.strip())
        paras = fileresult['段落']
        # file_para_counter[len(paras)] = file_para_counter.get(len(paras), 0) + 1
        sum_para += len(paras)
        for para in paras:
            tokencount = len(para['en_text'].split())
            para_token_counter[tokencount] = para_token_counter.get(tokencount, 0) + 1
            sum_token += tokencount
        # if file_cnt % 1000 == 0:
            # print(f'已处理{file_cnt}个文件')

# with open(out_para_counter, 'w', encoding='utf-8', newline='\n') as f:
#     writer = csv.writer(f)
#     writer.writerow(['段落数', '文件数'])
#     for k, v in file_para_counter.items():
#         writer.writerow([k, v])

with open(out_token_counter, 'w', encoding='utf-8', newline='\n') as f:
    writer = csv.writer(f)
    writer.writerow(['token数', '段落数'])
    for k, v in para_token_counter.items():
        writer.writerow([k, v])

print(f'文件数: {file_cnt}, 总段落数: {sum_para}, 总token数: {sum_token}')
