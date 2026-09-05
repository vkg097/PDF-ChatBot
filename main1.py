import os
import tempfile
import streamlit as st
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

st.set_page_config(page_title="PDF Q&A Engine", layout="wide")
st.title("📄 1000-Page PDF Query System")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Configuration")
    
    provider = st.radio("Select Processing Stack", ["Cloud (Groq)", "Local (Ollama)"])
    
    if provider == "Cloud (Groq)":
        groq_api_key = st.text_input("Groq API Key", type="password", help="Enter your gsk_... key")
        hf_token = st.text_input("Hugging Face Token (Optional)", type="password", help="Optional API key for Cloud Embeddings")
        model_name = st.selectbox("Select Model", ["openai/gpt-oss-20b"])
    else:
        model_name = st.text_input("Ollama Model", value="qwen2.5:3b")

# --- Helper: Dynamic Embeddings Selector ---
def get_embeddings(provider, hf_token=None):
    if provider == "Cloud (Groq)":
        # Cloud setup: Fast lightweight cloud embeddings model
        kwargs = {"token": hf_token} if hf_token else {}
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs=kwargs
        )
    else:
        # Local setup: Ollama local embeddings model
        return OllamaEmbeddings(model="nomic-embed-text")

# --- Helper: PDF Processor & Vector Store ---
@st.cache_resource(show_spinner="Chunking and indexing document...")
def process_pdf(file_bytes, provider_type, token=None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    loader = PyPDFLoader(tmp_path)
    documents = loader.load()

    # Split into 1000-character chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)

    # Instantiate selected embeddings
    embeddings = get_embeddings(provider_type, token)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    os.remove(tmp_path)
    return vectorstore

# --- Main App Interface ---
uploaded_file = st.file_uploader("Upload PDF (up to 1000+ pages)", type=["pdf"])

if uploaded_file:
    # Build vectorstore mapped to selected provider
    vectorstore = process_pdf(
        uploaded_file.getvalue(), 
        provider, 
        hf_token if provider == "Cloud (Groq)" else None
    )
    st.success(f"Document processed successfully using {provider} mode!")

    user_query = st.text_input("Ask a question about your document:")

    if user_query:
        # Guardrails for Cloud execution
        if provider == "Cloud (Groq)" and not groq_api_key:
            st.error("Please enter your Groq API key in the sidebar.")
            st.stop()

        # Initialize LLM based on mode
        if provider == "Cloud (Groq)":
            os.environ["GROQ_API_KEY"] = groq_api_key
            llm = ChatGroq(model=model_name, api_key=groq_api_key)
        else:
            llm = ChatOllama(model=model_name)

        # Retrieve top 4 chunks
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

        prompt = PromptTemplate.from_template(
            """Context:
{context}

Question:
{question}

Answer directly and concisely using only the context provided:"""
        )

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        with st.chat_message("assistant"):
            st.write_stream(rag_chain.stream(user_query))