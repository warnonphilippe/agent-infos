from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# Création des outils
@tool
def multiply(a: int, b: int) -> int:
   """Multiply two numbers."""
   return a * b

@tool
def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b

# Initialisation du modèle LangChain avec OpenAI
llm = ChatOpenAI(model_name="llama-3.3-70b-versatile")

# Intégration des outils au LLM
llm_with_tools = llm.bind_tools([add, multiply])

# Appel au LLM qui engendre un appel à outil
user_input = "What is 2 multiplied by 3?"
messages = [HumanMessage(user_input)]
result = llm_with_tools.invoke(messages)
messages.append(result)

# Appel à la fonction et injection des résultats dans les messages
for tool_call in result.tool_calls:
  tool_name = tool_call["name"].lower()
  print(f"Tool call object : {tool_call}")
  print(f" > Tool calling : {tool_name}")
  selected_tool = {"add": add, "multiply": multiply}[tool_name]
  tool_msg = selected_tool.invoke(tool_call)
  messages.append(tool_msg)

# Appel au LLM avec les résultats de fonction
result = llm_with_tools.invoke(messages)
print(result.content)