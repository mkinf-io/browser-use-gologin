import json
import os
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig, Controller
from browser_use.browser.context import BrowserContextConfig
from gologin import GoLogin
from enum import Enum
import subprocess
import time


server = Server("browser-use-gologin")

class ServerTools(str, Enum):
  RUN_TASK = "run_task"


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name=ServerTools.RUN_TASK.value,
            description="Executes a specified task within a secure GoLogin browser session. Preloads cookies before execution and saves them to the cloud upon completion. Returns the actions performed during the session.",  # noqa: E501
            inputSchema={
              "type": "object",
              "required": ["profile_id", "task"],
              "properties": {
                "profile_id": {"type": "string"},
                "task": {"type": "string"},
                "max_steps": {"type": "number"},
              }
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name != ServerTools.RUN_TASK.value: raise ValueError(f"Unknown tool: {name}")
    # LLM
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key: raise ValueError("Missing LLM API key")
    # GoLogin
    gologin_api_key = os.getenv("GOLOGIN_API_KEY")
    if not gologin_api_key: raise ValueError("Missing GoLogin API key")
    # Arguments
    if not arguments: raise ValueError("Missing arguments")
    max_steps = arguments.get("max_steps") or 10
    task = arguments.get("task")
    if not task: raise ValueError("Missing task")
    profile_id = arguments.get("profile_id")
    if not profile_id: raise ValueError("Missing profile_id")

    cookies_path = "./cookies.json"
    controller = Controller()

    try:
        # Wait for Xvfb to be ready (it's started by entrypoint.sh)
        wait_for_xvfb()
        
        # Ensure display is set before starting the browser
        os.environ['DISPLAY'] = ':0'
        
        gologin = GoLogin({
            'token': gologin_api_key,
            'profile_id': profile_id,
            'executablePath': os.getenv("EXEC_PATH", "/.gologin/browser/orbita-browser/chrome"),
            'writeCookiesFromServer': True,
            'extra_params': [
                '--start-maximized',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--no-zygote',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--window-position=0,0',
                f'--window-size={os.getenv("SCREEN_WIDTH", "1920")},{os.getenv("SCREEN_HEIGHT", "1080")}',
            ],
        })

        cdp_address = gologin.start()

        browser = Browser(
            config = BrowserConfig(
                headless=False,
                cdp_url=f"http://{cdp_address}",
                new_context_config = BrowserContextConfig(cookies_file=cookies_path)
            )
        )

        model = ChatOpenAI(model=llm_model, api_key=llm_api_key, temperature=0.7)

        agent = Agent(
            task=task,
            llm=model,
            browser=browser,
            controller=controller
        )

        await agent.run(max_steps = max_steps)
        await browser.close()
        await save_cookies(cookies_path, gologin)
        gologin.stop()
    except Exception as e:
        print(e)
        raise ValueError(f"Error processing task: {str(e)}")

    # Convert agent history to a serializable format
    history = {
        "steps": len(agent.history.history),  # Use .history to get the list
        "actions": agent.history.model_actions(),  # These are already dictionaries
        "extracted_content": agent.history.extracted_content(),
        "final_result": agent.history.final_result(),
        "urls_visited": agent.history.urls(),
        "is_done": agent.history.is_done(),
        "errors": agent.history.errors()
    }

    return [types.TextContent(type="text", text=json.dumps(history))]


async def save_cookies(cookies_path: str, gologin: GoLogin):
    with open(cookies_path, "r") as f:
        gologin.uploadCookies(json.loads(f.read()))


def wait_for_xvfb():
    """Wait for Xvfb to be ready on display :0"""
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            subprocess.run(['xdpyinfo', '-display', ':0'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            attempt += 1
            time.sleep(1)
    raise RuntimeError("Xvfb failed to start within the timeout period")


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="browser-use-gologin",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
