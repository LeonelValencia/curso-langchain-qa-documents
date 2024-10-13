from functools import partial
from operator import itemgetter
from typing import Sequence

import streamlit as st
from dotenv import load_dotenv
from langchain.base_language import BaseLanguageModel
from langchain_community.document_transformers import LongContextReorder
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.indexes import SQLRecordManager
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
# from langchain_community.retrievers import BM25Retriever
# from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.schema import (
    AIMessage,
    BaseRetriever,
    Document,
    HumanMessage,
    StrOutputParser,
)
from langchain.schema.messages import BaseMessageChunk
from langchain.schema.runnable import Runnable, RunnableMap
from langchain_chroma import Chroma

load_dotenv()
# vectorstore = Chroma(
#     collection_name="langchain_docs_app",
#     persist_directory="data/chroma/langchain_docs_app/",
#     embedding_function=OpenAIEmbeddings(),
# )

# record_manager = SQLRecordManager(
#     namespace="chroma/langchain_docs_app",
#     db_url="sqlite:///data/langchain_docs_app.db",
# )

# vector_keys = vectorstore.get(
#     ids=record_manager.list_keys(), include=["documents", "metadatas"]
# )

# docs_in_vectorstore = [
#     Document(page_content=page_content, metadata=metadata)
#     for page_content, metadata in zip(
#         vector_keys["documents"], vector_keys["metadatas"]
#     )
# ]

# keyword_retriever = BM25Retriever.from_documents(docs_in_vectorstore)
# keyword_retriever.k = 6

# semantic_retriever = vectorstore.as_retriever(
#     search_type="mmr",
#     search_kwargs={
#         "k": 6,
#         "fetch_k": 20,
#         "lambda_mult": 0.3,
#     },
# )

# queries_llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k")
# multi_query_retriever = MultiQueryRetriever.from_llm(
#     retriever=semantic_retriever,
#     llm=queries_llm,
# )

# retriever = EnsembleRetriever(
#     retrievers=[keyword_retriever, multi_query_retriever],
#     weights=[0.3, 0.7],
#     c=0,
# )
# agen_executer = create_csv_agent(llm, "tablePromoters.tsv", pandas_kwargs={"sep":"\t"},verbose=False)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

vectorstore = Chroma(
    persist_directory="data/chroma/regulondb", 
    embedding_function=embeddings,
    collection_name="promotores"
)

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 100,
        # "fetch_k": 20,
        # "lambda_mult": 0.3,
    },
)

CONDENSE_QUESTION_TEMPLATE = """\
Given the following conversation and a follow up question, rephrase the follow up \
question to be a standalone question.

Questions generally contains different entities, so you should rephrase \
the question according to the entity that is being asked about. \
Do not made up any information. The only information you can \
use to formulate the standalone question is the conversation and the follow up \
question.

Chat History:
###
{chat_history}
###

Follow Up Input: {question}
Standalone Question:"""

SYSTEM_ANSWER_QUESTION_TEMPLATE = """\
You are an expert in Molecular Biology, particularly in the area of microbial gene regulation, \
so you are familiar with the names of genes, promoters, regulatory proteins and their interactions.\
    
If you are asked for a list, give the complete list and not just a sample.

If there is nothing in the context relevant to the question at hand, just say "Hmm, \
I'm not sure.". Don't try to make up an answer. This is not a suggestion. This is a rule.

Anything between the following `context` is retrieved from a knowledge \
bank, not part of the conversation with the user.

<context>
    {context}
</context>

REMBEMBER: If there is no relevant information within the context, just say "Hmm, \
I'm not sure.". Don't try to make up an answer. This is not a suggestion. This is a rule. \
Anything between the preceding 'context' is retrieved from a knowledge bank, \
not part of the conversation with the user.

Take a deep breath and relax. You are an expert in Molecular Biology. You can do this.
Let's go!"""


def create_retriever_chain(
    llm: BaseLanguageModel[BaseMessageChunk],
    retriever: BaseRetriever,
    use_chat_history: bool,
):
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(CONDENSE_QUESTION_TEMPLATE)

    if not use_chat_history:
        initial_chain = (itemgetter("question")) | retriever
        return initial_chain
    else:
        condense_question_chain = (
            {
                "question": itemgetter("question"),
                "chat_history": itemgetter("chat_history"),
            }
            | CONDENSE_QUESTION_PROMPT
            | llm
            | StrOutputParser()
        )
        conversation_chain = condense_question_chain | retriever
        return conversation_chain


def get_k_or_less_documents(documents: list[Document], k: int):
    if len(documents) <= k:
        return documents
    else:
        return documents[:k]


def reorder_documents(documents: list[Document]):
    reorder = LongContextReorder()

    for i, doc in enumerate(documents):
        doc.metadata["original_index"] = i

    return reorder.transform_documents(documents)


def format_docs(docs: Sequence[Document]) -> str:
    formatted_docs: list[str] = []
    for i, doc in enumerate(docs):
        doc_string = f"<doc id='{doc.metadata.get('original_index', i)}'>{doc.page_content}</doc>"
        formatted_docs.append(doc_string)
    return "\n".join(formatted_docs)


def create_answer_chain(
    llm: BaseLanguageModel[BaseMessageChunk],
    retriever: BaseRetriever,
    use_chat_history: bool,
    k: int = 5,
) -> Runnable:
    retriever_chain = create_retriever_chain(llm, retriever, use_chat_history)

    _get_k_or_less_documents = partial(get_k_or_less_documents, k=k)

    context = RunnableMap(
        {
            "context": (
                retriever_chain
                | _get_k_or_less_documents
                | reorder_documents
                | format_docs
            ),
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history"),
        }
    )

    prompt = ChatPromptTemplate.from_messages(
        messages=[
            ("system", SYSTEM_ANSWER_QUESTION_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    response_synthesizer = prompt | llm
    response_chain = context | response_synthesizer

    return response_chain


st.title("Chat with RegulonDB Assistant")

st.subheader("It uses a combination of keyword and semantic search to find answers.")

# onAgent = st.toggle("Activate large responses")

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

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        # Create answer chain
        llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k", max_tokens=500)

        use_chat_history = len(st.session_state.messages) > 1

        chat_history = []
        if use_chat_history:
            for message in st.session_state.messages[:-1]:
                if message["role"] == "user":
                    chat_history.append(HumanMessage(content=message["content"]))
                elif message["role"] == "assistant":
                    chat_history.append(AIMessage(content=message["content"]))

        answer_chain = create_answer_chain(
            llm=llm,
            retriever=retriever,
            use_chat_history=use_chat_history,
            # k=6,
        )

        message_placeholder = st.empty()
        full_response = ""
        for token in answer_chain.stream(
            {
                "question": prompt,
                "chat_history": chat_history,
            }
        ):
            full_response += token.content
            message_placeholder.markdown(full_response + "▌")

        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
