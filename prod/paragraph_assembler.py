import argparse


class ParagraphAssembler():

    def __init_(self):
        pass

    def select_data_by_record(self, record):
        """
        Select data based on record

        Args:
            record: file record numbe

        Returns: dict or text (pending)
            
        """
        pass

    def start(self, record, key):
        pass

    def post_process(self):
        """
        When the current file completes
            
        """
        pass

    def batch_post_process(self):
        """
        When each batch completes
            
        """
        pass
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', default=False, help='file record number')
    parser.add_argument('--key', type=str, default=False, help='openai api key')

    args = parser.parse_args()

    record = args.record if isinstance(args.record, int) else int(args.record)
    key = args.key

    
    print(type(record))
    print(type(key))
