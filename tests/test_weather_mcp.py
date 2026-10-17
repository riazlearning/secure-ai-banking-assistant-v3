import asyncio

from banking_assistant.mcp.weather_client import connect_weather_mcp


async def main():
    async with connect_weather_mcp() as client:
        print("Connected to remote Weather MCP")

        response = await client.session.list_tools()

        for tool in response.tools:
            print("\nTool:", tool.name)
            print("Description:", tool.description)
            print("Input schema:", tool.inputSchema)


if __name__ == "__main__":
    asyncio.run(main())
