import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.schema import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from sqlalchemy import create_engine
from langchain_community.agent_toolkits import create_sql_agent

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
engine = create_engine("sqlite:///regulon.db")
db = SQLDatabase(engine=engine)
agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=False)
# Palabras clave para activar el agente SQL
sql_keywords = ["transcription unit", "tu", "tus","transcription units", "promoter", "promotor", 
                "promotores", "sigma factor", "regulon", "evidence","evidencia","ri","regulatory interaction",
                "terminator","terminators","gene","gene product","gene products","operon","operons",
                "regulador","regulator","regulators","tf","transcription factor","transcription factors"]

# Almacén de memoria de conversaciones
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Obtiene o crea el historial de conversación para una sesión."""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Crear un wrapper con memoria
agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

def process_prompt(prompt: str, session_id: str):
    """Procesa el prompt, decide si usar el agente SQL o solo el LLM, y maneja el historial."""
    chat_history = get_session_history(session_id)
    
    # Decidir si usar el agente SQL o el LLM
    if any(keyword in prompt.lower() for keyword in sql_keywords):
        # Ajustar el límite en las consultas
        if "limit" not in prompt.lower():
            prompt += " sin límite"
        
        # Ejecutar con el agente SQL
        response = agent_with_chat_history.invoke(
            {"input": prompt},
            config={"configurable": {"session_id": session_id}},
        )["output"]
    else:
        # Ejecutar directamente con el modelo, usando el historial
        llm_response = llm.invoke(prompt)
        chat_history.add_message(HumanMessage(content=prompt))
        chat_history.add_message(AIMessage(content=llm_response.content))
        response = llm_response.content

    return response

session_id = "123" 

st.title("Chat with RegulonDB Assistant")
st.markdown("¡Hola! Soy el asistente de RegulonDB. Puedo ayudarte a encontrar información sobre genes, operones, promotores y más. ¡Hazme una pregunta!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Escribe tu consulta:"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Pensando...")

        # Crear la entrada para el agente SQL y agregar historial si es necesario
        response = process_prompt(prompt, session_id)
        full_response = response

        # Mostrar la respuesta del agente
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
