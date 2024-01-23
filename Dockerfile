FROM ubuntu

ENV DEBIAN_FRONTEND noninteractive
ENV PYENV_ROOT /pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

ADD . /bot
WORKDIR /bot

# Update system
RUN apt-get update && apt-get upgrade -y
RUN apt-get install software-properties-common build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev cron curl wget git -y --no-install-recommends

# Setup pyenv
RUN git clone https://github.com/pyenv/pyenv.git /pyenv
RUN pyenv install 3.11.5
RUN pyenv global 3.11.5
RUN pyenv rehash
RUN python --version

# Init cleanup job
RUN crontab -l | { cat; echo "0 3 * * * python /bot/data/cleanup.py"; } | crontab -

# Run bot
RUN python -m pip install -r requirements.txt

CMD ["python", "bot.py"]
