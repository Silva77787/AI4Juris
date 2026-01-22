import os
from dotenv import load_dotenv

from dgsi_scraper.retriever import DocumentRetriever
from agent.splitter import split
from agent.decision_table import db_connect, insert_decision, get_decision
from dgsi_scraper.scrape import search_documents

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")
retriever = DocumentRetriever(db_dsn=DB_DSN)

# def tool_retriever(file):
#     '''
#     Retrieve chunks relevant to file provided.
    
#     :param file: file given by user.
#     '''
#     retrieved = retriever.retrieve_chunks(file)

#     con = db_connect()

#     for i in range(len(retrieved)):
#         decision = get_decision(con, document_id=retrieved[i].doc_id)
#         if not decision:
#             full_text = search_documents(retrieved[i].url)
#             text_split = split(full_text)
#             insert_decision(con, document_id=retrieved[i].doc_id, chunk_text=text_split)
#         retrieved[i].decision = decision
#     con.close()
#     return retrieved

def tool_class_retriever(file, decision):

    retrieved = retriever.retrieve_by_class(decision=decision, query=file)

    return retrieved
