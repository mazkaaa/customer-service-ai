from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from agents.tools.ticket_tools import create_ticket, update_session_customer_id

system_prompt = """
You are a helpful customer service agent...
Use the following knowledge base context if relevant: {context}.
Use the knowledge base to guide your tone, information gathering, troubleshooting, and ticket management. 
Always follow the documented escalation, priority, and tool usage rules from the knowledge base.
If the documentation is not sufficient to answer the user's question, ask clarifying questions to gather more information.
If the knowledge base not provided yet, respond with "Knowledge base not provided yet." 
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tools = [create_ticket, update_session_customer_id]

def get_customer_service_agent(llm, **kwargs):
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=3, handle_parsing_errors=True, **kwargs)
