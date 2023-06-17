import concurrent.futures
import subprocess
import argparse
import os
import string
import random
import sys

def run_script(script_path):
    # 调用系统命令执行Python脚本，并返回输出结果
    output = subprocess.check_output(script_path)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--concurrent_number', type=int, default=10, help='concurrent number')
    args = parser.parse_args()

    concurrent_number = args.concurrent_number

    def generate_random_string(length):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(length))
 
    scripts = []

    for _ in range(concurrent_number):
        scripts.append(['python', f'{os.path.dirname(os.path.abspath(__file__))}/single_file_segment_builder.py', f"--api_key={generate_random_string(20)}", "--test_mode=0"])

    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交任务到线程池
        futures = [executor.submit(run_script, script) for script in scripts]

        record_set = set()
        apikey_set = set()
        
        # 获取每个线程的返回值/输出值
        for future in futures:
            result = future.result()
            result = str(result).replace("b'","")

            print_line = result.split("\\n")
            print(print_line)
            record_set.add(print_line[0].replace(" start", ""))
            apikey_set.add(print_line[1].replace(" api_key", ""))

            if not "success" in print_line[2]:
                print("test fail")
                sys.exit(0)


        if len(record_set) == concurrent_number and len(apikey_set) == concurrent_number:
            print("test success")
        else:
            print("test fail")
