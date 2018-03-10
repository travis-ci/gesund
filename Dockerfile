FROM python:3-alpine

WORKDIR /usr/src/app

COPY . .

EXPOSE 8192
CMD ["python", "/usr/src/app/gesund.py"]
