import os
from typing import List, Tuple, Optional
from dataclasses import dataclass
import argparse

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import psycopg
except Exception:
    psycopg = None


@dataclass
class RetrievalResult:
    id: int
    url: str
    processo: Optional[str]
    text_plain: str
    similarity: float
    source: str
    sessao_date: Optional[str]
    descritores: List[str]
    decision: Optional[str]


@dataclass
class ChunkRetrievalResult:
    chunk_id: int
    doc_id: int
    chunk_index: int
    chunk_text: str
    similarity: float
    url: str
    processo: Optional[str]
    source: str
    sessao_date: Optional[str]


class DocumentRetriever:
    def __init__(
        self,
        db_dsn: str,
        model_name: str = "neuralmind/bert-base-portuguese-cased",
        embedding_dim: int = 768,
        chunk_size: int = 512,
    ):
        self.db_dsn = db_dsn
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.chunk_size = chunk_size
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        test_embedding = self.model.encode("test")
        actual_dim = len(test_embedding)
        if actual_dim != embedding_dim:
            print(f"Warning: Model produces {actual_dim}D embeddings, not {embedding_dim}D")
            self.embedding_dim = actual_dim
    
    def get_connection(self):
        if psycopg is None:
            raise RuntimeError("psycopg is not installed!")
        return psycopg.connect(self.db_dsn)
    
    def ensure_vector_schema(self):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'dgsi_documents' 
                            AND column_name = 'embedding'
                        ) THEN
                            ALTER TABLE dgsi_documents 
                            ADD COLUMN embedding vector({self.embedding_dim});
                        END IF;
                    END $$;
                """)
                
                #index for fast similarity search (using cosine distance)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS dgsi_documents_embedding_idx 
                    ON dgsi_documents 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                # chunks table for chunk retrieval
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS dgsi_document_chunks (
                        id SERIAL PRIMARY KEY,
                        doc_id INTEGER NOT NULL REFERENCES dgsi_documents(id) ON DELETE CASCADE,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        embedding vector({self.embedding_dim}),
                        UNIQUE(doc_id, chunk_index)
                    );
                """)
                
                # index for chunk embeddings
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS dgsi_chunks_embedding_idx 
                    ON dgsi_document_chunks 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                # index for doc_id lookups
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS dgsi_chunks_doc_id_idx 
                    ON dgsi_document_chunks(doc_id);
                """)
                
            conn.commit()
            print("Vector schema initialized successfully (including chunks table)")
        finally:
            conn.close()
    
    def _chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        # Simple chunking by sentences/paragraphs
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_len = len(word) + 1
            if current_length + word_len > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_len
            else:
                current_chunk.append(word)
                current_length += word_len
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks if chunks else [text[:max_length]]
    
    def generate_embedding(self, text: str, use_chunking: bool = True) -> np.ndarray:
        if not text or not text.strip():
            return np.zeros(self.embedding_dim)
        
        if use_chunking and len(text) > self.chunk_size * 2:
            # For very long documents, chunk and average, with max 5 chunks
            chunks = self._chunk_text(text, self.chunk_size)[:5]
            embeddings = self.model.encode(chunks, convert_to_numpy=True)
            return np.mean(embeddings, axis=0)
        else:
            return self.model.encode(text[:self.chunk_size * 3], convert_to_numpy=True)
    
    def index_document(self, doc_id: int, text: str) -> bool:
        embedding = self.generate_embedding(text)
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE dgsi_documents SET embedding = %s WHERE id = %s;",
                    (embedding.tolist(), doc_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error indexing document {doc_id}: {e}")
            return False
        finally:
            conn.close()
    
    def index_document_chunks(self, doc_id: int, text: str) -> bool:
        if not text or not text.strip():
            return False
        
        chunks = self._chunk_text(text, self.chunk_size)
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Delete existing chunks for this document
                cur.execute("DELETE FROM dgsi_document_chunks WHERE doc_id = %s;", (doc_id,))
                
                # Insert new chunks
                for i, chunk in enumerate(chunks):
                    embedding = self.model.encode(chunk, convert_to_numpy=True)
                    cur.execute(
                        """INSERT INTO dgsi_document_chunks 
                           (doc_id, chunk_index, chunk_text, embedding) 
                           VALUES (%s, %s, %s, %s);""",
                        (doc_id, i, chunk, embedding.tolist())
                    )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error indexing document chunks {doc_id}: {e}")
            return False
        finally:
            conn.close()
    
    def index_all_documents(self, batch_size: int = 100, limit: Optional[int] = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                query = "SELECT id, text_plain FROM dgsi_documents WHERE embedding IS NULL"
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                docs = cur.fetchall()
            
            total = len(docs)
            print(f"Found {total} documents to index")
        
            for i in range(0, total, batch_size):
                batch = docs[i:i + batch_size]
                print(f"Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")
                texts = [doc[1] for doc in batch]
                doc_ids = [doc[0] for doc in batch]
                embeddings = []
                for text in texts:
                    emb = self.generate_embedding(text)
                    embeddings.append(emb.tolist())
                
                with conn.cursor() as cur:
                    for doc_id, embedding in zip(doc_ids, embeddings):
                        cur.execute(
                            "UPDATE dgsi_documents SET embedding = %s WHERE id = %s;",
                            (embedding, doc_id)
                        )
                conn.commit()
                print(f"Indexed {min(i + batch_size, total)}/{total} documents")
                
        finally:
            conn.close()
    
    def index_all_documents_chunks(self, batch_size: int = 100, limit: Optional[int] = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                #documents that have no chunks indexed
                query = """
                    SELECT d.id, d.text_plain 
                    FROM dgsi_documents d
                    LEFT JOIN dgsi_document_chunks c ON d.id = c.doc_id
                    WHERE c.id IS NULL
                    GROUP BY d.id, d.text_plain
                """
                if limit:
                    query += f" LIMIT {limit}"
                cur.execute(query)
                docs = cur.fetchall()
            
            total = len(docs)
            print(f"Found {total} documents to index as chunks")
        
            for i in range(0, total, batch_size):
                batch = docs[i:i + batch_size]
                print(f"Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")
                
                for doc_id, text in batch:
                    self.index_document_chunks(doc_id, text)
                    
                print(f"Indexed {min(i + batch_size, total)}/{total} documents as chunks")
                
        finally:
            conn.close()
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_source: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[RetrievalResult]:
        query_embedding = self.generate_embedding(query)
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Use cosine similarity (1 - cosine_distance)
                # <=>  is cosine distance
                sql = """
                    SELECT 
                        id, url, processo, text_plain, source, 
                        sessao_date, descritores,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM dgsi_documents
                    WHERE embedding IS NOT NULL
                """
                params = [query_embedding.tolist()]
                if filter_source:
                    sql += " AND source = %s"
                    params.append(filter_source)
                
                sql += " ORDER BY embedding <=> %s::vector LIMIT %s;"
                params.extend([query_embedding.tolist(), top_k])
                cur.execute(sql, params)
                rows = cur.fetchall()

            results = []
            for row in rows:
                similarity = float(row[7])
                if similarity >= min_similarity:
                    results.append(RetrievalResult(
                        id=row[0],
                        url=row[1],
                        processo=row[2],
                        text_plain=row[3],
                        source=row[4],
                        sessao_date=row[5],
                        descritores=row[6] or [],
                        similarity=similarity
                    ))
            
            return results
            
        finally:
            conn.close()
    
    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 5,
        filter_source: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[ChunkRetrievalResult]:
        query_embedding = self.generate_embedding(query, use_chunking=False)
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # join with document metadata
                sql = """
                    SELECT 
                        c.id, c.doc_id, c.chunk_index, c.chunk_text,
                        d.url, d.processo, d.source, d.sessao_date,
                        1 - (c.embedding <=> %s::vector) AS similarity
                    FROM dgsi_document_chunks c
                    JOIN dgsi_documents d ON c.doc_id = d.id
                    WHERE c.embedding IS NOT NULL
                """
                params = [query_embedding.tolist()]
                if filter_source:
                    sql += " AND d.source = %s"
                    params.append(filter_source)
                
                sql += " ORDER BY c.embedding <=> %s::vector LIMIT %s;"
                params.extend([query_embedding.tolist(), top_k])
                cur.execute(sql, params)
                rows = cur.fetchall()

            results = []
            for row in rows:
                similarity = float(row[8])
                if similarity >= min_similarity:
                    results.append(ChunkRetrievalResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        chunk_index=row[2],
                        chunk_text=row[3],
                        url=row[4],
                        processo=row[5],
                        source=row[6],
                        sessao_date=row[7],
                        similarity=similarity
                    ))
            
            return results
            
        finally:
            conn.close()
    
    def get_document_stats(self) -> dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(embedding) as indexed,
                        COUNT(*) - COUNT(embedding) as not_indexed
                    FROM dgsi_documents;
                """)
                row = cur.fetchone()
                doc_stats = {
                    "total_documents": row[0],
                    "indexed_documents": row[1],
                    "not_indexed": row[2],
                    "index_percentage": (row[1] / row[0] * 100) if row[0] > 0 else 0
                }
                
                #chunk stats
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT doc_id) as docs_with_chunks,
                        COUNT(*) as total_chunks,
                        AVG(chunk_count) as avg_chunks_per_doc
                    FROM (
                        SELECT doc_id, COUNT(*) as chunk_count
                        FROM dgsi_document_chunks
                        GROUP BY doc_id
                    ) as chunk_counts;
                """)
                chunk_row = cur.fetchone()
                
                if chunk_row and chunk_row[0]:
                    doc_stats["docs_with_chunks"] = chunk_row[0]
                    doc_stats["total_chunks"] = chunk_row[1]
                    doc_stats["avg_chunks_per_doc"] = float(chunk_row[2]) if chunk_row[2] else 0
                else:
                    doc_stats["docs_with_chunks"] = 0
                    doc_stats["total_chunks"] = 0
                    doc_stats["avg_chunks_per_doc"] = 0
                
                return doc_stats
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="AI4Juris Document Retriever")
    parser.add_argument("--db-dsn", type=str, 
                       default=os.getenv("DGSISCRAPER_DB_DSN"),
                       help="PostgreSQL connection string")
    parser.add_argument("--action", type=str, required=True,
                       choices=["setup", "index", "index-chunks", "search", "search-chunks", "stats"],
                       help="Action to perform")
    parser.add_argument("--query", type=str, help="Search query (for search action)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--limit", type=int, help="Limit number of docs to index")
    parser.add_argument("--model", type=str, 
                       default="neuralmind/bert-base-portuguese-cased",
                       help="Embedding model name")
    
    args = parser.parse_args()
    
    if not args.db_dsn:
        print("Error: Database DSN not provided.")
        return
    
    retriever = DocumentRetriever(db_dsn=args.db_dsn, model_name=args.model)
    
    if args.action == "setup":
        print("Setting up vector schema...")
        retriever.ensure_vector_schema()
        print("Setup complete!")
        
    elif args.action == "index":
        print("Indexing documents...")
        retriever.index_all_documents(limit=args.limit)
        print("Indexing complete!")
        
    elif args.action == "index-chunks":
        print("Indexing documents as chunks...")
        retriever.index_all_documents_chunks(limit=args.limit)
        print("Chunk indexing complete!")
        
    elif args.action == "stats":
        stats = retriever.get_document_stats()
        print(f"\nDocument Statistics")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Indexed (full): {stats['indexed_documents']} ({stats['index_percentage']:.1f}%)")
        print(f"Not indexed: {stats['not_indexed']}")
        print(f"\nChunk Statistics")
        print(f"Documents with chunks: {stats['docs_with_chunks']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Average chunks per doc: {stats['avg_chunks_per_doc']:.1f}")
        
    elif args.action == "search":
        if not args.query:
            print("Error: --query required for search action")
            return
        
        print(f"\nSearching for: {args.query}")
        results = retriever.retrieve(args.query, top_k=args.top_k)
        
        print(f"\nTop {len(results)} Results\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [Similarity: {result.similarity:.3f}]")
            print(f"   Source: {result.source}")
            print(f"   Processo: {result.processo or 'N/A'}")
            print(f"   Date: {result.sessao_date or 'N/A'}")
            print(f"   URL: {result.url}")
            print(f"   Preview: {result.text_plain[:200]}...")
            print()
    
    elif args.action == "search-chunks":
        if not args.query:
            print("Error: --query required for search-chunks action")
            return
        
        print(f"\nSearching chunks for: {args.query}")
        results = retriever.retrieve_chunks(args.query, top_k=args.top_k)
        
        print(f"\nTop {len(results)} Chunk Results\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [Similarity: {result.similarity:.3f}] Chunk {result.chunk_index + 1} from Doc {result.doc_id}")
            print(f"   Source: {result.source}")
            print(f"   Processo: {result.processo or 'N/A'}")
            print(f"   Date: {result.sessao_date or 'N/A'}")
            print(f"   URL: {result.url}")
            print(f"   Chunk text: {result.chunk_text[:300]}...")
            print()


if __name__ == "__main__":
    main()
