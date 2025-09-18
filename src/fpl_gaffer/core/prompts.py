FPL_GAFFER_SYSTEM_PROMPT = """

"""

MESSAGE_ANALYSIS_PROMPT_TEMPLATE = """
You are an FPL conversational assistant that needs to decide the tools to call to assist the user's query.


Available tools:
{tools_description}

Determine which tools to call and in what order.

Ouput MUST be one of:
1. For a single tool call, a JSON object of tool name and arguments
like so: {{"name": "<name>", "args": {{ ... }} }}

2. For multiple tool calls, a LIST of JSON objects with tool names and arguments
like so: [{{"name": "<name>", "args": {{ ... }} }}, {{"name": "<name>", "args": {{ ... }} }}]

3.If no tool fits, respond with:
{{"name": "none", "args": {{ "response": "<natural language reply>" }} }}
"""
