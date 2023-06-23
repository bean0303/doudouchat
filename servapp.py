# servapp.py

import re
import shutil
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

import fitz
import numpy as np
import openai
import tensorflow_text
import tensorflow_hub as hub
from fastapi import UploadFile
from lcserve import serving
from sklearn.neighbors import NearestNeighbors
import logging

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

recommender = None

def download_pdf(url, output_path):
    urllib.request.urlretrieve(url, output_path)


def preprocess(text):
    text = text.replace('\n', ' ')
    text = re.sub('\s+', ' ', text)
    return text


def pdf_to_text(path, start_page=1, end_page=None):
    doc = fitz.open(path)
    total_pages = doc.page_count

    if end_page is None:
        end_page = total_pages

    text_list = []

    for i in range(start_page - 1, end_page):
        text = doc.load_page(i).get_text("text")
        text = preprocess(text)
        text_list.append(text)

    doc.close()
    return text_list


def text_to_chunks(texts_list, word_length=150, start_page=1):
    text_toks = [get_word_list(w) for w in texts_list if len(w.strip()) > 0]  # 去掉为空的字符
    logging.debug(text_toks)
    chunks = []

    for idx, words in enumerate(text_toks):
        for i in range(0, len(words), word_length):
            chunk = words[i : i + word_length]
            if (
                (i + word_length) > len(words)
                and (len(chunk) < word_length)
                and (len(text_toks) != (idx + 1))
            ):
                text_toks[idx + 1] = chunk + text_toks[idx + 1]
                continue
            chunk = ' '.join(chunk).strip()
            chunk = f'[Page no. {idx+start_page}]' + ' ' + '"' + chunk + '"'
            chunks.append(chunk)
    logging.debug(chunks)
    return chunks


def get_word_list(texts):
    # 把句子按字分开，中文按字分，英文按单词，数字按空格
    regEx = re.compile('[\W+]')    # 我们可以使用正则表达式来切分句子，切分的规则是除单词，数字外的任意字符串
    res = re.compile(r"([\u4e00-\u9fa5])")    #  [\u4e00-\u9fa5]中文范围

    handle_en = regEx.split(texts)
    # logging.debug(handle_en)
    str_list = []
    for str in handle_en:
        if res.split(str) == None:
            str_list.append(str)
        else:
            ret = res.split(str)
            for ch in ret:
                str_list.append(ch)

    list_word = [w for w in str_list if len(w.strip()) > 0]  # 去掉为空的字符

    return  list_word



class SemanticSearch:
    def __init__(self):
        self.use = hub.load('../universal-mult/')
        self.fitted = False

    def fit(self, data, batch=1000, n_neighbors=5):
        self.data = data
        self.embeddings = self.get_text_embedding(data, batch=batch)
        n_neighbors = min(n_neighbors, len(self.embeddings))
        self.nn = NearestNeighbors(n_neighbors=n_neighbors)
        self.nn.fit(self.embeddings)
        self.fitted = True

    def __call__(self, text, return_data=True):
        inp_emb = self.use([text])
        neighbors = self.nn.kneighbors(inp_emb, return_distance=False)[0]

        if return_data:
            return [self.data[i] for i in neighbors]
        else:
            return neighbors

    def get_text_embedding(self, texts, batch=1000):
        embeddings = []
        for i in range(0, len(texts), batch):
            text_batch = texts[i : (i + batch)]
            emb_batch = self.use(text_batch)
            embeddings.append(emb_batch)
        embeddings = np.vstack(embeddings)
        return embeddings


def load_recommender(path, start_page=1):
    global recommender
    if recommender is None:
        recommender = SemanticSearch()

    texts_list = pdf_to_text(path, start_page=start_page)
    chunks = text_to_chunks(texts_list, start_page=start_page)
    recommender.fit(chunks)
    return 'Corpus Loaded.'


def generate_text(openAI_key, prompt, engine="text-davinci-003"):
    openai.api_key = openAI_key
    try:
        completions = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=512,
            n=1,
            stop=None,
            temperature=0.7,
        )
        message = completions.choices[0].text
    except Exception as e:
        message = f'API Error:{str(e)}'
    return message


def generate_answer(question, openAI_key):
    topn_chunks = recommender(question)
    logging.debug(topn_chunks)
    prompt = ""
    prompt += 'search results:\n\n'
    for c in topn_chunks:
        prompt += c + '\n\n'

    prompt += (
        "Instructions: Compose a comprehensive reply to the query using the search results given. "
        "Cite each reference using [ Page Number] notation (every result has this number at the beginning). "
        "Citation should be done at the end of each sentence. If the search results mention multiple subjects "
        "with the same name, create separate answers for each. Only include information found in the results and "
        "don't add any additional information. Make sure the answer is correct and don't output false content. "
        "If the text does not relate to the query, simply state 'Text Not Found in PDF'. Ignore outlier "
        "search results which has nothing to do with the question. Only answer what is asked. The "
        "answer should be short and concise. Answer step-by-step. \n\nQuery: {question}\nAnswer: "
    )

    prompt += f"Query: {question}\nAnswer:"
    answer = generate_text(openAI_key, prompt, "text-davinci-003")
    return answer


def load_openai_key() -> str:
    key = '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'
    if key is None:
        raise ValueError(
            "[ERROR]: Please pass your OPENAI_API_KEY. Get your key here : https://platform.openai.com/account/api-keys"
        )
    return key


@serving
def ask_url(url: str, question: str)-> str:
    download_pdf(url, 'corpus.pdf')
    load_recommender('corpus.pdf')
    openAI_key = load_openai_key()
    return generate_answer(question, openAI_key)


@serving
async def ask_file(file: UploadFile, question: str) -> str:
    suffix = Path(file.filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    load_recommender(str(tmp_path))
    openAI_key = load_openai_key()
    return generate_answer(question, openAI_key)

if __name__ == "__main__":
    # ask_url('https://arxiv.org/pdf/1706.03762.pdf','summarize the paper')
    ## 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

    s = "12、China's Legend Holdings will split its several business arms to go public on stock markets,  the group's president Zhu Linan said on Tuesday.该集团总裁朱利安周二表示，haha中国联想控股将分拆其多个业务部门在股市上市。"
    list_word1=get_word_list(s)
    print(list_word1)
