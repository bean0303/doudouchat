FROM python:3.8-slim-buster as langchain-serve-img

RUN pip3 install langchain-serve
RUN pip3 install servapp

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "lc-serve", "deploy", "local", "servapp" ]

FROM python:3.8-slim-buster as doudou-img

WORKDIR /app

CMD [ "python3", "botapp.py" ]