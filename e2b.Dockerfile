FROM e2bdev/code-interpreter:latest

# Install UV tool
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV tool to PATH
ENV PATH="/root/.local/bin/:$PATH"

# Clone the repository
RUN git clone https://github.com/mkinf/browser-use-gologin

# Change directory and run UV sync
WORKDIR browser-use-gologin

RUN uv sync

# Install playwright
RUN uv pip install playwright
RUN uv run playwright install
RUN uv run playwright install-deps