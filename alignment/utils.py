import os
import requests
import logging
import json
import time

import numpy as np

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
            Do not add addition \n.
            Additionally, please ensure that pagination and indexing information remains on its own line and does not get joined with adjacent paragraphs. Your response should maintain the original structure of the input while eliminating unnecessary line breaks.
            '''
        },
        {"role": "assistant", "content": 'Please provide your text.'},
        {"role": "user", "content": input_text},
        {"role": "assistant", "content": 'Output:\n'}
    ]


def gpt_detect_hard_line_breaks(line_break_text: str, use_proxy: bool = False, retries: int = 1000):
    """
    Sends the provided text to the AI model and returns its response.

    Args:
        line_break_text (str): The text with line breaks which needs to be processed by the AI model.
        The token number of line_break_text should be < 1400

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
                    "temperature": 0,
                },
                timeout = 60 * 5, verify=False
            )
            break
        # add requests.exceptions.SSLError
        except requests.exceptions.RequestException as e:
            if i < retries - 1:  # i is zero indexed
                logging.error(f"Request failed with {str(e)}, retrying.")
                continue
            else:
                logging.error(f"Request failed after {retries} retries.")
                raise e
        # wait 10 sec between each retry
        time.sleep(10)

    logging.info(response.text)

    try:
        response_json = response.json()
    except json.JSONDecodeError:
        response_json = json.loads('{' + response.text) 

    if 'error' in response_json:
        error = response_json['error']
        if 'code' in error and error['code'] == 'invalid_request_error':
            raise ExceededContextLength(error['message'])
        else:
            raise UnknownError(error['message'])

    return response_json['choices'][0]['message']['content']


def find_char(string, char):
    return [i for i, letter in enumerate(string) if letter == char]


def find_closest_within_margin(target, candidates, margin):
    """
    Find the closest element within a given margin to a target in a sorted array.

    Args:
        target (int): The target value.
        candidates (list): The sorted list of candidate values.
        margin (int): The acceptable margin for matching.

    Returns:
        idx (int): The index of the closest value within margin. If no such value exists, returns None.
        closest_val (int): The closest value within margin. If no such value exists, returns None.
    """
    idx = np.searchsorted(candidates, target, side='left')

    if idx > 0 and (idx == len(candidates) or abs(target - candidates[idx-1]) <= abs(target - candidates[idx])):
        idx -= 1

    if abs(candidates[idx] - target) <= margin:
        return idx, candidates[idx]
    else:
        return None, None


def index_near_match(indice_true, indice_pred, margin):
    """
    This function identifies and matches indices in 'indice_pred' that are closest to indices in 'indice_true', 
    within a specified margin. The offset is corrected each time an index is matched. The function returns two 
    lists of booleans: 'is_match_true' and 'is_match_pred'. 'is_match_true' indicates whether an index in 
    'indice_true' is matched, while 'is_match_pred' indicates whether an index in 'indice_pred' is used for matching.

    If the mean of 'is_match_pred' is less than 0.9, an error is raised.

    Args:
        indice_true (list): The list of true indices.
        indice_pred (list): The list of predicted indices.
        margin (int, optional): The acceptable margin for matching indices. Defaults to 5.

    Returns:
        is_match_true (list): A list indicating which indices in 'indice_true' are matched.
        is_match_pred (list): A list indicating which indices in 'indice_pred' are used for matching.

    Raises:
        ValueError: If the mean of 'is_match_pred' is less than 0.9.

    Example:
        indice_true = [1, 100, 200, 300, 400, 500]
        indice_pred = [101, 301, 402]
        The result will be:
        is_match_true = [False, True, False, True, True, False]
        is_match_pred = [True, True, True]
    """
    is_match_true = [False]*len(indice_true)
    is_match_pred = [False]*len(indice_pred)
    indice_true = np.array(indice_true)
    indice_pred = np.array(indice_pred)
    
    offset = 0
    for j in range(len(indice_pred)):
        index_pred = indice_pred[j]
        i, index_true = find_closest_within_margin(index_pred + offset, indice_true, margin)
        if index_true is not None:
            is_match_true[i] = True
            is_match_pred[j] = True
            offset = index_true - index_pred
    
    return is_match_true, is_match_pred


def compute_near_linebreak_match(raw_text, output_text, margin):
    """
    This function computes the near linebreak match between the raw text and the output text. The raw text is
    assumed to contain all line breaks, while the output text is assumed to contain only hard line breaks.
    The location of the linebreaks might differ within the margin
    """
    raw_linebreaks = find_char(raw_text, '\n')
    output_linebreaks = find_char(output_text, '\n')
    is_hard_line_break, _ = index_near_match(raw_linebreaks, output_linebreaks, margin=margin)
    return is_hard_line_break


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
    indice_true = [1, 100, 200, 300, 400, 500]
    indice_pred = [101, 301, 402]

    print(index_near_match(indice_true, indice_pred)) 