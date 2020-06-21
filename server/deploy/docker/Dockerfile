FROM ubuntu:14.04
LABEL maintainer="anqiang@12sigma.ai"

ENV LD_LIBRARY_PATH /usr/local/lib:$LD_LIBRARY_PATH
RUN mkdir -p /root/.pip
COPY ./pip.conf /root/.pip/pip.conf
COPY ./sigmaocr-supervisord.conf /etc/supervisord.conf
COPY ./tesseract /usr/local/
COPY ./sigma-ocr /opt/sigma-ocr
COPY ./sources.list /etc/apt/sources.list
COPY ./get-pip.py /get-pip.py
RUN apt-get update && apt-get install -y build-essential libpq-dev libssl-dev openssl libffi-dev zlib1g-dev software-properties-common wget supervisor
RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update && apt-get install -y python3.6 python3.6-dev libpng-dev libjpeg-dev libtiff5-dev libsm6 libxext6 libxrender1
RUN python3.6 /get-pip.py
RUN pip install -r /opt/sigma-ocr/requirements.txt
RUN chmod +x /usr/local/lib/liblept.so.5.0.3
RUN chmod +x /usr/local/lib/libtesseract.so.3.0.5
RUN chmod +x /usr/local/bin/tesseract
RUN ln -sf /usr/local/lib/liblept.so.5.0.3 /usr/local/lib/liblept.so.5
RUN ln -sf /usr/local/lib/liblept.so.5.0.3 /usr/local/lib/liblept.so
RUN ln -sf /usr/local/lib/libtesseract.so.3.0.5 /usr/local/lib/libtesseract.so.3
RUN ln -sf /usr/local/lib/libtesseract.so.3.0.5 /usr/local/lib/libtesseract.so
RUN rm /get-pip.py
RUN ln -s /tmp/supervisor.sock /var/run/supervisor.sock
COPY ./init.py /opt/sigma-ocr/init.py
