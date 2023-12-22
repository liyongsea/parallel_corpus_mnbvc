import os
import json
import argparse
from pathlib import Path
from tqdm import tqdm


def main(args):
    progress = tqdm()
    for _ in os.walk(args.dir):
        filelist = _[2]
        # If there are no files in the directory, skip
        if len(filelist) == 0:
            continue

        for file in filelist:
            # If the file suffix is not json, skip
            if Path(file).suffix != '.json':
                continue

            with open(Path(_[0]) / file, 'r', encoding='utf-8') as fp:
                formatted_data = json.load(fp)

                # filter no solution
                formatted_data['answers'] = [answer for answer in formatted_data['answers'] \
                                                if any(f'[hide={kw}]' in answer['post_canonical'].lower() \
                                                       or f'[hide="{kw}"]' in answer['post_canonical'].lower() \
                                                       or f'[hide=\'{kw}\']' in answer['post_canonical'].lower() \
                                                    for kw in ['solution', 'sol', 'my solution'])]

            if len(formatted_data['answers']) > 0:
                target_path = Path(_[0].replace(Path(args.dir).parts[-1], 'aops_contain_sol_result')) / file
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(target_path, 'w', encoding='utf-8') as fp_o1:
                    json.dump(formatted_data, fp_o1)

            progress.update(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True, type=str)
    args = parser.parse_args()

    if Path(args.dir).exists():
        main(args)
    else:
        print('The target directory was not found.')
