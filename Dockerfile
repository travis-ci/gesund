FROM python:3-alpine
ENV PYTHONPATH /usr/src/app
ENV PATH /bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/src/app/bin
EXPOSE 8192
COPY . /usr/src/app
CMD ["gesund"]
