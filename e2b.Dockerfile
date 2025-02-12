FROM e2bdev/code-interpreter:latest

# Install GoLogin
RUN curl -LO https://dl.gologin.com/gologin.tar \
    && tar -xvf gologin.tar -C /opt/ \
    && rm gologin.tar \
    && ln -s /opt/GoLogin-3.3.78/gologin /usr/local/bin/gologin \
    && chmod +x /opt/GoLogin-3.3.78/orbita-browser/chrome

# Install UV tool
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV tool to PATH
ENV PATH="/root/.local/bin/:$PATH"

# Clone the repository
RUN git clone https://github.com/mkinf-io/browser-use-gologin

# Change directory and run UV sync
WORKDIR browser-use-gologin

RUN uv sync

# Install Playwright
RUN uv pip install playwright
RUN uv run playwright install
RUN uv run playwright install-deps