FROM e2bdev/code-interpreter:latest

# Install vnc, xvfb in order to create a 'fake' display and chrome
RUN export DEBIAN_FRONTEND=noninteractive
RUN export DISPLAY=:0
RUN export SCREEN_WIDTH=1920
RUN export SCREEN_HEIGHT=1080

RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime

RUN apt-get update &&\
  apt-get install -y tzdata &&\
  dpkg-reconfigure --frontend noninteractive tzdata &&\
  apt-get install -y x11vnc xvfb zip wget curl psmisc supervisor gconf-service libasound2 libatk1.0-0 libatk-bridge2.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-bin libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils libgbm-dev nginx libcurl3-gnutls

RUN curl --silent --location https://deb.nodesource.com/setup_18.x | bash - &&\
  apt-get -y -qq install nodejs &&\
  apt-get -y -qq install build-essential &&\
  fc-cache -f -v

RUN wget https://orbita-browser-linux.gologin.com/orbita-browser-latest.tar.gz -O /tmp/orbita-browser.tar.gz

# Create browser directory
RUN mkdir -p /root/.gologin/browser

# Install fonts
COPY fonts /root/.gologin/browser/fonts

# install browser
RUN cd /tmp &&\
  tar -xzf /tmp/orbita-browser.tar.gz -C /root/.gologin/browser &&\
  rm -f /tmp/orbita-browser.tar.gz

RUN apt-get -qq clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install UV tool and dependencies
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Worker install
COPY ./ /opt/orbita/
RUN cd /opt/orbita/ && uv sync && uv add playwright && uv run playwright install && uv run playwright install-deps


RUN rm /etc/nginx/sites-enabled/default
COPY orbita.conf /etc/nginx/conf.d/orbita.conf
RUN chmod 777 /var/lib/nginx -R
RUN chmod 777 /var/log -R
RUN chmod 777 /run -R
RUN chmod 777 /root/.gologin/browser -R

COPY entrypoint.sh /entrypoint.sh

RUN	chmod 777 /entrypoint.sh \
  && mkdir /tmp/.X11-unix \
  && chmod 1777 /tmp/.X11-unix
