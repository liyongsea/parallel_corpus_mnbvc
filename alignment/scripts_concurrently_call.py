import concurrent.futures
import subprocess
import argparse
import os
from tqdm import tqdm

def run_script(script_path):
    # 调用系统命令执行Python脚本，并返回输出结果
    output = subprocess.check_output(script_path)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--concurrent_number', type=int, default=10, help='concurrent number')
    parser.add_argument('--total', type=int, help='concurrent number')
    args = parser.parse_args()

    def get_apikey(index):
        if (index & 1) == 0:
            return "sk-mlcga"
        else:
            return "sk-dyB"
 

    concurrent_number = args.concurrent_number
    total = args.total


    with concurrent.futures.ThreadPoolExecutor() as executor:
        scripts = []

        for i in tqdm(range(0, total)):
            script = ['python', f'{os.path.dirname(os.path.abspath(__file__))}/batch_sequential_for_one_file.py', f"--api_key={get_apikey(i)}", f"--dataset_index={i}"]
            scripts.append(script)
            
            if len(scripts) == concurrent_number or i == total:
                futures = {executor.submit(run_script, script): script for script in scripts}

                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    print(result)

                scripts = []
