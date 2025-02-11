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


server = Server("gitingest")

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
    llm_model = os.getenv("LLM_MODEL") or "gpt-4o-mini"
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
        gologin = GoLogin({
            'token': gologin_api_key,
            'profile_id': profile_id,
            'writeCookiesFromServer': True,
            # 'uploadCookiesToServer': True, # The library doesn't handle it
        })

        cdp_address = gologin.start()

        browser = Browser(
            config = BrowserConfig(
                headless=False,
                cdp_url=f"http://{cdp_address}",
                new_context_config = BrowserContextConfig(cookies_file=cookies_path)
            )
        )

        model = ChatOpenAI(model=llm_model, temperature=0.7)

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

    return [types.TextContent(type="text", text=json.dumps(agent.history))]


async def save_cookies(cookies_path: str, gologin: GoLogin):
    with open(cookies_path, "r") as f:
    	gologin.uploadCookies(json.loads(f.read()))


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
