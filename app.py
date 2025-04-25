import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
    # Load environment variables
    load_dotenv()

    # Create MCPClient from config file
    client = MCPClient.from_config_file(
        os.path.join(os.path.dirname(__file__), "browser_mcp.json")
    )

    # Create LLM
    llm = ChatOpenAI(model="gpt-4o")

    # Create agent with the client
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    print("\n🤖 Slack Assistant is ready. Type your queries below!")
    print("Type 'exit' to quit.\n")

    try:
        while True:
            # Get query from terminal input
            query = input("🗨️ You: ").strip()

            # Exit condition
            if query.lower() in ("exit", "quit"):
                print("👋 Goodbye!")
                break

            # Run the query
            try:
                result = await agent.run(query)
                print(f"✅ Response: {result}\n")
            except Exception as e:
                print(f"❌ Error: {e}\n")

    finally:
        if client.sessions:
            await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())
