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
                aops_data = json.load(fp)
                formatted_data = []
                for post in aops_data['posts'][1:]:
                    formatted_data.append({
                        'question': {
                            'post_rendered': aops_data['posts'][0]['post_rendered'],
                            'post_canonical': aops_data['posts'][0]['post_canonical']
                        },
                        'answer': {
                            'post_rendered': post['post_rendered'],
                            'post_canonical': post['post_canonical']
                        }
                    })
            
            # Save as the original directory structure or a jsonl file.
            if not args.one:
                target_path = Path(_[0].replace(Path(args.dir).parts[-1], 'aops_format_result')) / file
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(target_path, 'w', encoding='utf-8') as fp_o1:
                    json.dump(formatted_data, fp_o1)
            else:
                with open('./aops_out.jsonl', 'a', encoding='utf-8') as fp_o2:
                    for fd in formatted_data:
                        fp_o2.write(json.dumps(fd) + '\n')
            progress.update(progress.n + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True, type=str)
    parser.add_argument('--one', action='store_true', required=False, help='Output to "aops_out.jsonl" file')
    args = parser.parse_args()

    if Path(args.dir).exists():
        main(args)
    else:
        print('The target directory was not found.')
