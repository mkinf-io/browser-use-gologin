FROM e2bdev/code-interpreter:latest

# Install system dependencies
RUN apt update && apt install -y \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xvfb \
    libgbm1 \
    libxcb-dri3-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download and install GoLogin browser
RUN curl -LO https://dl.gologin.com/gologin.tar \
    && tar -xvf gologin.tar \
    && rm gologin.tar \
    && mv GoLogin-3.3.78 /usr/local/bin/gologin-browser \
    && chmod +x /usr/local/bin/gologin-browser

# Install UV tool
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Clone repository and install Python dependencies
RUN git clone https://github.com/mkinf-io/browser-use-gologin
WORKDIR /browser-use-gologin
RUN uv sync && uv pip install playwright && uv run playwright install

# Install browser dependencies
RUN uv run playwright install-deps

# Add wrapper script for GoLogin
RUN echo '#!/bin/sh\nxvfb-run -a /usr/local/bin/gologin-browser "$@"' > /usr/local/bin/run-gologin \
    && chmod +x /usr/local/bin/run-gologin