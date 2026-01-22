import os
from dotenv import load_dotenv

from dgsi_scraper.retriever import DocumentRetriever
from agent.splitter import split
from agent.decision_table import db_connect, insert_decision, get_decision
from dgsi_scraper.scrape import search_documents

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
  
def tool_class_retriever(file, decision):

    retrieved = retriever.retrieve_by_class(decision=decision, query=file)
    
    return retrieved
