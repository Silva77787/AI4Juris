import os
from dotenv import load_dotenv
from typing import List

from dgsi_scraper.retriever import DocumentRetriever, ChunkRetrievalResult
from agent.splitter import split
from agent.decision_table import db_connect, insert_decision, get_decision
from dgsi_scraper.scrape import search_documents

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")
retriever = DocumentRetriever(db_dsn=DB_DSN)

def tool_retriever(text: str) -> List[ChunkRetrievalResult]:
    '''
    Retrieve chunks relevant to text provided.
    Chunks have their decision associated to them.
    Use this function to help identify the text provided.
    
    :param text: text given by user.
    :return: list of chunk retrieval results
    '''
    return retriever.retrieve(query=text)
  
def tool_class_retriever(file: str, decision: str) -> List[ChunkRetrievalResult]:
    '''
    Retrieve chunks relevant to text provided and filtered by decision.
    
    :param file: text given by user.
    :param decision: decision to filter chunks by.
    :return: list of chunk retrieval results
    '''
    retrieved = retriever.retrieve_by_class(decision=decision, query=file)
    return retrieved
