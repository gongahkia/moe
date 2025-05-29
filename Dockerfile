FROM python:3.10-slim
RUN apt-get update && apt-get install -y redis-server
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["redis-server", "--daemonize yes", "&&", "python", "-m", "bot"]