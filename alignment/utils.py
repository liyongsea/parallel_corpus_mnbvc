import os
import requests
import logging
import json

logging.basicConfig(filename='chatgptoutputs.log', level=logging.INFO, format='%(asctime)s %(message)s')


class ExceededContextLength(Exception):
    pass


class UnknownError(Exception):
    pass


def create_chat_prompt(input_text: str): 
    """
    Creates a prompt for the AI model based on the provided input text.

    Args:
        input_text (str): The input text for which the prompt needs to be created.

    Returns:
        A list containing the user's task and the AI model's responses.
    """
    return [
        {
            'role': 'user', 
            'content': '''Your task is to detect soft line breaks in text exported from a PDF and replace them with spaces, while keeping hard line breaks as they are.
            Please note that you should only determine which line breaks to keep or replace and leave other text unchanged. Do not add any words or characters to the input text or provide additional information beyond the requested output.
            Additionally, please ensure that pagination and indexing information remains on its own line and does not get joined with adjacent paragraphs. Your response should maintain the original structure of the input while eliminating unnecessary line breaks.
            '''
        },
        {"role": "assistant", "content": 'Please provide your text.'},
        {"role": "user", "content": input_text},
        {"role": "assistant", "content": 'Output:\n'}
    ]


def gpt_detect_handle_line_breaks(line_break_text: str, use_proxy: bool = False, retries: int = 3):
    """
    Sends the provided text to the AI model and returns its response.

    Args:
        line_break_text (str): The text with line breaks which needs to be processed by the AI model.

    Raises:
        ExceededContextLength: If the context length is exceeded.
        UnknownError: If an unknown error occurs.

    Returns:
        str: The AI model's response.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not use_proxy:
        url = "https://api.openai.com/v1/chat/completions"
    else:
        url = "https://openai-proxy-syhien.pages.dev/v1/chat/completions"

    for i in range(retries):
        try:
            response = requests.post(
                url, 
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": create_chat_prompt(line_break_text),
                },
                timeout = 60 * 5 
            )
            break
        except RequestException as e:
            if i < retries - 1:  # i is zero indexed
                logging.error(f"Request failed with {str(e)}, retrying.")
                continue
            else:
                logging.error(f"Request failed after {retries} retries.")
                raise e
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        response_json = json.loads('{' + response.text) 

    logging.info(response.text)

    if 'error' in response_json:
        error = response_json['error']
        if 'code' in error and error['code'] == 'invalid_request_error':
            raise ExceededContextLength(error['message'])
        else:
            raise UnknownError(error['message'])

    return response_json['choices'][0]['message']['content']


def compare_breaks(raw_text, output_text):
    """
    Compares the hard line breaks in the raw text with the output text.

    Args:
        raw_text (str): The raw text to be detected with soft line breaks and hard line breaks.
        output_text (str): The output text with hard line breaks. Soft line breaks are replaced with spaces.
    
    Returns:
        is_hard_line_break (list[bool]): A list of booleans where `True` signifies a hard line break.
    """
    assert len(raw_text) == len(output_text)
    is_hard_line_break = []
    for i in range(len(raw_text)):
        if raw_text[i] == '\n':
            is_hard_line_break.append(raw_text[i] == output_text[i])
    return is_hard_line_break



if __name__ == "__main__":
    raw_text = """– To strengthen or develop norms at the global, regional and national levels that
would reinforce and further coordinate efforts to prevent and combat the illicit
trade in small arms and light weapons in all its aspects;
– To develop agreed international measures to prevent and combat illicit arms
trafficking in and manufacturing of small arms and light weapons and to
reduce excessive and destabilizing accumulations and transfers of such
weapons throughout the world;"""
    output_text = gpt_detect_handle_line_breaks(raw_text)
    print(output_text)
    import pdb; pdb.set_trace()