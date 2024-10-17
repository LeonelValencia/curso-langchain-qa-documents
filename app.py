import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from langchain_community.agent_toolkits import create_sql_agent

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
engine = create_engine("sqlite:///regulon.db")
db = SQLDatabase(engine=engine)
agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=False)

st.title("Chat with RegulonDB Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Listame todos los nombres de los promotores que esten regulados por el sigma factor sigma54"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

     # Usar historial de chat en la consulta
    chat_history = "\n".join([f'{msg["role"]}: {msg["content"]}' for msg in st.session_state.messages])
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Pensando...")

        # Crear la entrada para el agente SQL y agregar historial si es necesario
        response = agent_executor.invoke({"input": prompt})
        full_response = response['output']

        # Mostrar la respuesta del agente
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
