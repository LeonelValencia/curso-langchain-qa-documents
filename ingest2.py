import os
from dotenv import load_dotenv
# import pysqlite3
# import sys
# sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders.csv_loader import CSVLoader

load_dotenv()
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

def load_data():
    """
    Load data from a CSV file and return it as a list of dictionaries.
    """

    loader = CSVLoader(file_path='tablePromoters.tsv',csv_args={
        'delimiter': '\t',
        # "fieldnames": ["ID of promoter", "name of promoter", "synonyms", "operon's strand", "transcription start site (TSS)", 
        #                "firstGene's distance to promoter", "first gene's name", "promoter's sequence", 
        #                "nucleotide", "relative position box -10", "relative position box -35", 
        #                "right end position of box -10", "left end position of box -10", 
        #                "right end position of box -35", "left end position of box -35", 
        #                "sequence of box -10", "sequence of box -35", "name of bind Sigma Factor", "name of transcription unit (TU)", 
        #                "promotor's note", "evidence with pmid", "pmid", "name of citations's evidence", 
        #                "promoter's genes", "regulator's name","sequence of regulatory site"],
        "fieldnames": ["promoter id", "promoter name", "strand", "position of Transcription Start Site (TSS)", "sigma factor", 
                       "promoter sequence", "first gene", "distance to first gene", 
                       "evidence", "Additive Evidence", "confidence level (C: Confirmed, S: Strong, W: Weak)", 
                       "pmids associated to object"]
    })
    data = loader.load()
    return data

def process_data(data):
    """
    Process the data by splitting it into chunks and creating a Chroma vector store.
    """
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    docs = text_splitter.split_documents(data)
    print(len(docs))

    openai_lc_client = Chroma.from_documents(
        docs, embeddings, persist_directory="data/chroma/regulondb", collection_name="promotores"
    )        
    return openai_lc_client

def main():
    """
    Main function to load data and process it.
    """
    data = load_data()
    openai_lc_client = process_data(data)

if __name__ == "__main__":
    main()