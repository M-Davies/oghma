FROM ubuntu

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /app
RUN mkdir logs/
RUN mkdir data/

COPY requirements.txt .
COPY bot.py .
COPY cleanup.py data/.
COPY .env .

# Update system
RUN apt-get update && apt-get upgrade -y
RUN apt-get install software-properties-common build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev cron curl wget git -y --no-install-recommends

# Setup pyenv
RUN git clone https://github.com/pyenv/pyenv.git /pyenv
ENV PYENV_ROOT /pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN pyenv install 3.11.5
RUN pyenv global 3.11.5
RUN pyenv rehash
RUN python --version

# Init cleanup job
RUN crontab -l | { cat; echo "0 3 * * * python /app/data/cleanup.py"; } | crontab -

# Run bot
RUN python -m pip install -r requirements.txt

CMD ["python", "bot.py"]
