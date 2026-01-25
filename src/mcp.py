#!/usr/bin/env python
import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

# MCP Imports
from mcp import ClientSession
from mcp.client.sse import sse_client

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

async def run_mcp_agent():
    # 1. Server Connection Details
    # Using the official remote Exa MCP server directly (no local npx bridge)
    exa_mcp_url = "https://mcp.exa.ai/mcp"
    api_key = os.getenv("EXA_API_KEY")

    if not api_key:
        print("❌ Error: EXA_API_KEY environment variable is not set.")
        return

    headers = {
        "x-api-key": api_key,
        "User-Agent": "agent-infos-mcp-dynamic/1.0"
    }

    print(f"🔌 Connecting to remote Exa MCP Server at {exa_mcp_url}...")

    try:
        async with sse_client(exa_mcp_url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 2. Dynamic Tool Discovery
                # We ask the server what tools it has.
                list_tools_result = await session.list_tools()
                mcp_tools = list_tools_result.tools
                
                tool_names = [t.name for t in mcp_tools]
                print(f"🛠️  Discovered tools: {tool_names}")

                # 3. Dynamic Conversion to OpenAI Tools
                # Instead of manually wrapping functions with @tool, we verify the schema
                # and pass it directly to the LLM.
                openai_tools = []
                for tool in mcp_tools:
                    # Construct the OpenAI function schema from MCP tool definition
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema 
                        }
                    }
                    openai_tools.append(openai_tool)

                # 4. Configure LLM with Dynamic Tools
                llm = ChatOpenAI(model="gpt-4o", temperature=0)
                # Bind the raw tool schemas
                llm_with_tools = llm.bind_tools(openai_tools)

                # 5. Prepare the Query
                one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                query = "Quels sont les 3 meilleurs articles techniques sortis cette semaine à propos de LangChain ?"
                
                messages = [
                    SystemMessage(content=f"You are a tech watcher assistant. Today is {datetime.now().strftime('%Y-%m-%d')}. "
                                          f"For recent searches, generally use startPublishedDate='{one_week_ago}' (or similar) if the tool supports it."),
                    HumanMessage(content=query)
                ]

                print(f"🤖 User Query: '{query}'")

                # 6. Execution Loop (LLM -> Tool Decision -> MCP Call -> LLM)
                # First call to LLM to decide what to do
                ai_msg = await llm_with_tools.ainvoke(messages)
                messages.append(ai_msg)

                # If the LLM wants to call tools
                if ai_msg.tool_calls:
                    for tool_call in ai_msg.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        
                        print(f"🔎 LLM chose to call: '{tool_name}' with args: {tool_args}")
                        
                        # Execute the tool generically via MCP session
                        # We don't need a specific python function for each tool!
                        try:
                            result = await session.call_tool(tool_name, arguments=tool_args)
                            
                            # Format result for LLM (usually a string or JSON)
                            # We take the text content from the result
                            tool_content = []
                            if result.isError:
                                tool_content.append(f"Error: {result.content}")
                            else:
                                for c in result.content:
                                    if c.type == "text":
                                        tool_content.append(c.text)
                                    # Handle other content types (images, resources) if needed
                            
                            tool_output_str = "\n".join(tool_content)
                            
                        except Exception as e:
                            print(f"❌ Tool execution failed: {e}")
                            tool_output_str = f"Error executing tool {tool_name}: {str(e)}"

                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "content": tool_output_str,
                            "tool_call_id": tool_call["id"]
                        })

                    # 7. Final Response Generation
                    print("📝 Generating final answer...")
                    final_response = await llm_with_tools.ainvoke(messages)
                    
                    print("\n" + "="*50)
                    print("📝 FINAL RESULT:")
                    print("="*50)
                    print(final_response.content)
                else:
                    print("The LLM did not call any tools.")
                    print(ai_msg.content)

    except Exception as e:
        print(f"❌ Connection or Runtime Error: {e}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
         print("❌ Error: OPENAI_API_KEY is not set.")
    else:
        asyncio.run(run_mcp_agent())