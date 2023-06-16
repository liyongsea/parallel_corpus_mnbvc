import concurrent.futures
import subprocess
import argparse
import os

def run_script(script_path):
    # 调用系统命令执行Python脚本，并返回输出结果
    output = subprocess.check_output(script_path)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--concurrent_number', type=str, default=10, help='concurrent number')
    args = parser.parse_args()

    concurrent_number = args.concurrent_number

    scripts = [
        ['python', f'{os.path.dirname(os.path.abspath(__file__))}/paragraph_assembler.py', "--key='sk-xxxxxx", "--test=true"]
    ] * concurrent_number


    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交任务到线程池
        futures = [executor.submit(run_script, script) for script in scripts]

        result_set = set()

        # 获取每个线程的返回值/输出值
        for future in futures:
            result_set.add(future.result())
        
        if len(result_set) == concurrent_number:
            print("test success")
        else:
            print("test fail")
