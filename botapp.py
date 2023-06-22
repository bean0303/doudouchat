import json
from tempfile import _TemporaryFileWrapper

import gradio as gr
import requests



def ask_api(
    file: _TemporaryFileWrapper,
    question: str,
    url: str = '',
    lcserve_host:str ='http://localhost:8080',
) -> str:

    if url.strip() == '' and file == None:
        return '[ERROR]: Both URL and PDF is empty. Provide at least one.'

    if url.strip() != '' and file != None:
        return '[ERROR]: Both URL and PDF is provided. Please provide only one (either URL or PDF).'

    if question.strip() == '':
        return '[ERROR]: Question field is empty'

    _data = {
        'question': question,
    }

    if url.strip() != '':
        r = requests.post(
            f'{lcserve_host}/ask_url',
            json={'url': url, **_data},
        )

    else:
        with open(file.name, 'rb') as f:
            r = requests.post(
                f'{lcserve_host}/ask_file',
                params={'input_data': json.dumps(_data)},
                files={'file': f},
            )

    if r.status_code != 200:
        print(lcserve_host)
        print(url)
        raise ValueError(f'[ERROR]: {r.text}')

    return r.json()['result']

def answer(file, question, history=[]):
    history.append(question)
    message = ask_api(file,  question)
    history.append(message)
    responses = [(u,b) for u,b in zip(history[::2], history[1::2])]
    question = ''
    print(responses)
    return responses, history


with gr.Blocks(css="#chatbot{height:530px} .overflow-y-auto{height:500px}",title="doudouchat") as rxbot:
    # pdf_url = gr.Textbox(label='Enter PDF URL here')
    # gr.Markdown("<center><h4>OR<h4></center>")
    file = gr.File(
        label='请上传pdf文件', file_types=['.pdf']
    )
    chatbot = gr.Chatbot(elem_id="chatbot")
    state = gr.State([])
    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="请输入你的问题").style(container=False)
    txt.submit(answer,
            inputs=[file, txt, state],
            outputs=[chatbot, state],
    )

    
rxbot.launch(server_name="www.doudou.chat",server_port=80,auth=("admin","douchat"))
