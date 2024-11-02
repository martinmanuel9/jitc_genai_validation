# /app/src/app/utils/data_loader.py

from haystack.utils import convert_files_to_docs
from haystack.document_stores import MilvusDocumentStore
from haystack.nodes import DensePassageRetriever

def index_documents():
    document_store = MilvusDocumentStore(
        host="milvus",
        port="19530",
        index="document_index",
        consistency_level="Session",
    )
    docs = convert_files_to_docs(dir_path="../../data/documents")
    document_store.write_documents(docs)
    retriever = DensePassageRetriever(document_store=document_store)
    document_store.update_embeddings(retriever)
