FROM ubuntu:latest

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /bot

# Update system
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-venv python3-pip
# Verify python version in logs
RUN python3.11 --version

# Init cleanup job
RUN crontab -l | { cat; echo "0 3 * * * python3.11 /bot/data/cleanup.py"; } | crontab -

# Install dependencies & run bot
COPY . /bot/
RUN python3.11 -m pip install -r requirements.txt
CMD ["python3.11", "bot.py"]
