import asyncio

from banking_assistant.mcp.github_client import connect_github_mcp


async def main():
    async with connect_github_mcp() as client:
        print("Connected to GitHub MCP Server")

        response = await client.session.list_tools()

        print("\nAvailable tools:")
        for tool in response.tools:
            print("-", tool.name)

        print("\nCalling GitHub get_me tool...")

        result = await client.session.call_tool(
            "get_me",
            arguments={},
        )

        if result.isError:
            raise RuntimeError("GitHub MCP get_me failed")

        for block in result.content:
            if block.type == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
