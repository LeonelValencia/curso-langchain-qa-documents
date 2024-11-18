import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import SystemMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
db = SQLDatabase.from_uri("sqlite:///regulon.db")
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

SQL_PREFIX = """You are an agent designed to interact with a SQL database of RegulonDB.
Given an input question, create a syntactically correct SQLite query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 15 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.
if the result has several semicolons (;), then it is a list. The sigma factor is in a column of the table promotores."""

system_message = SystemMessage(content=SQL_PREFIX)

def initialize_chat_history():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = ChatMessageHistory()
    if "messages_ui" not in st.session_state:
        st.session_state.messages_ui = []
      
# Función para convertir mensajes a un formato compatible con Streamlit
def convert_messages_to_ui(chat_history):
    messages_ui = []
    for message in chat_history.messages:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        messages_ui.append({"role": role, "content": message.content})
    return messages_ui

def truncate_messages(messages, max_tokens=6):
    # Implementa una lógica para reducir el tamaño de `messages`
    # según el conteo de tokens
    return messages[-max_tokens:]
  
def invoke_with_memory(agent, chat_history, user_message):
    # Add the user's message
    chat_history.add_user_message(user_message)
    messages = truncate_messages(chat_history.messages)

    # Invoke the agent
    response = agent.invoke({"messages": messages},config={"recursion_limit": 50})
    response_content = response["messages"][-1].content

    # Agregar la respuesta del agente al historial
    chat_history.add_ai_message(response_content)

    # Convertir el historial actualizado para la interfaz
    st.session_state.messages_ui = convert_messages_to_ui(chat_history)
    return response_content

# Initialize chat history
initialize_chat_history()
chat_history = st.session_state.chat_history

agent_executor = create_react_agent(
    llm, 
    tools, 
    state_modifier=system_message
)

st.title("Chat with RegulonDB Assistant")
st.markdown("¡Hola! Soy el asistente de RegulonDB. Puedo ayudarte a encontrar información sobre genes, operones, promotores y más. ¡Hazme una pregunta!")

# Display chat messages from history on app rerun
for message in st.session_state.messages_ui:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Escribe tu consulta:"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Pensando...")

        # Generar respuesta del agente
        response = invoke_with_memory(agent_executor, chat_history, prompt)

        # Actualizar la respuesta en la interfaz
        message_placeholder.markdown(response)