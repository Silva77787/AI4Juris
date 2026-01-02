import os
from dotenv import load_dotenv

from dgsi_scraper.retriever import DocumentRetriever

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")
retriever = DocumentRetriever(db_dsn=DB_DSN)

def tool_retriever(file):
    '''
    Retrieve chunks relevant to file provided.
    
    :param file: file given by user.
    '''
    return retriever.retrieve(file)