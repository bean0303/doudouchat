import json
from tempfile import _TemporaryFileWrapper

import gradio as gr
import requests
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s')


api_key = 'sec_b3Xha5nYq2Lt2XTaCgftai7CN0km2lmu'


def chat(sourceid,question):

    data = {
        'sourceId': sourceid,
        'messages': [
            {
                'role': "user",
                'content': question,
            }
        ]
    }

    headers = {
        'x-api-key': api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            'https://api.chatpdf.com/v1/chats/message', headers=headers, json=data)

        if response.status_code == 200:
            message = {'Result':response.json()['content']}
        else:
            message = {'Status': response.status_code , 'Error':  response.text }
    except requests.exceptions.RequestException as e:
        message = f'chat Error:{str(e)}'
    return message

def delete(sources):

    data = {
    'sources': sources,
    }

    headers = {
        'x-api-key': api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
             'https://api.chatpdf.com/v1/sources/delete', json=data, headers=headers)
        response.raise_for_status()
        message = {'Status': response.status_code , 'Error':  response.text }
    except requests.exceptions.RequestException as e:
        message = f'delete Error:{str(e)}'
    return message



def add_file(file):
    # files = {'file':  open(file.name, 'rb')}
    headers = {
        'x-api-key': api_key
    }
    logging.debug(file.name)
    logging.debug(headers)
    try:
        with open(file.name, 'rb') as f:
            response = requests.post(
                f'https://api.chatpdf.com/v1/sources/add-file',
                headers=headers,
                files={'file': f},
            )


        # response = requests.post(
        #     'https://api.chatpdf.com/v1/sources/add-file', headers=headers, files=files)

        if response.status_code == 200:
            logging.debug(response.json())
            message = {'Source ID': response.json()['sourceId']}
        else:
            message = {'Status': response.status_code , 'Error':  response.text }
    except Exception as e:
        message = f'add_file Error:{str(e)}'
    logging.debug(message)
    return message



def add_file_url(url):
    data = {'url': url}
    headers = {
        'x-api-key': api_key,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            'https://api.chatpdf.com/v1/sources/add-url', headers=headers, json=data)
        if response.status_code == 200:
           message = {'Source ID': response.json()['sourceId']}
        else:
            message = {'Status': response.status_code , 'Error':  response.text }
    except Exception as e:
        message = f'add_file_url Error:{str(e)}'
    return message


def answer_chat(file, question, history=[], sourceid=''):
    history.append(question)
    if sourceid != '':
        message = chat(sourceid,question)
    else:
        sourceid = add_file(file)['Source ID']
        message = chat(sourceid,question)

    history.append(message)
    responses = [(u,b) for u,b in zip(history[::2], history[1::2])]
    question = ''
    return responses, history, sourceid


    
with gr.Blocks(css="#chatbot{height:530px} .overflow-y-auto{height:500px}",title="doudouchat") as rxbot:
    # pdf_url = gr.Textbox(label='Enter PDF URL here')
    # gr.Markdown("<center><h4>OR<h4></center>")
    file = gr.File(
        label='请上传pdf文件', file_types=['.pdf']
    )
    chatbot = gr.Chatbot(elem_id="chatbot")
    state = gr.State([])
    sourceid = ''
    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="请输入你的问题").style(container=False)
        sourceid = gr.Textbox(show_label=False, placeholder="id").style(container=False)
    txt.submit(answer_chat,
            inputs=[file, txt, state, sourceid],
            outputs=[chatbot, state, sourceid],
    )

    
rxbot.launch(server_name="0.0.0.0",server_port=7861,auth=("admin","douchat"))

