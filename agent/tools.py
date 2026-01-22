import os
from dotenv import load_dotenv

from dgsi_scraper.retriever import DocumentRetriever

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")
retriever = DocumentRetriever(db_dsn=DB_DSN)

def tool_retriever(text):
    '''
    Retrieve chunks relevant to text provided.
    Chunks have their decision associated to them.
    Use this function to help identify the text provided.
    
    :param file: text given by user.
    :return: list of chunk retrieval results
    '''
    return retriever.retrieve(query=text)
