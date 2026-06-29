import os
import json
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from core.rag.embedder import embed_texts, embed_query
from core.logger import logger

_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(_THIS_FILE)))
DOCUMENTS_DIR = os.path.join(
    os.path.dirname(_THIS_FILE), "documents")
CHROMA_DIR = os.path.join(_PROJECT_ROOT, "data", "chroma")
COLLECTION_NAME = "feedbackiq_knowledge"
RELEVANCE_THRESHOLD = 0.45

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    os.makedirs(CHROMA_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    return _collection


def load_documents_from_files() -> List[Dict]:
    all_docs = []
    for filename in os.listdir(DOCUMENTS_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                docs = json.load(f)
            all_docs.extend(docs)
        except Exception as e:
            logger.error(
                f"Failed to load {filename}: {e}")
    return all_docs


def build_document_text(doc: Dict) -> str:
    return (
        f"Industry: {doc.get('industry', 'General')}\n"
        f"Problem: {doc.get('problem', '')}\n"
        f"Solution: {doc.get('solution', '')}\n"
        f"Tags: {', '.join(doc.get('tags', []))}"
    )


def initialise_knowledge_base(
        force_rebuild: bool = False) -> int:
    collection = _get_collection()
    existing_count = collection.count()

    if existing_count > 0 and not force_rebuild:
        logger.info(
            f"Knowledge base ready: {existing_count} docs")
        return existing_count

    if force_rebuild and existing_count > 0:
        _client.delete_collection(COLLECTION_NAME)
        _get_collection()

    docs = load_documents_from_files()
    if not docs:
        logger.warning("No documents found")
        return 0

    texts = [build_document_text(doc) for doc in docs]
    embeddings = embed_texts(texts)

    collection = _get_collection()
    collection.add(
        ids=[doc["id"] for doc in docs],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "industry": doc.get("industry", "General"),
            "issue_type": doc.get("issue_type", ""),
            "effort": doc.get("effort", "medium"),
            "timeframe": doc.get("timeframe", "short_term"),
            "impact": doc.get("impact", ""),
            "solution": doc.get("solution", ""),
            "problem": doc.get("problem", ""),
            "tags": ",".join(doc.get("tags", []))
        } for doc in docs]
    )

    logger.info(f"Knowledge base built: {len(docs)} docs")
    return len(docs)


def retrieve_relevant_solutions(
    query: str,
    industry: str,
    n_results: int = 5
) -> List[Dict]:
    collection = _get_collection()

    if collection.count() == 0:
        initialise_knowledge_base()

    query_embedding = embed_query(query)

    where_filter = None
    if industry and industry != "Other":
        where_filter = {
            "$or": [
                {"industry": {"$eq": industry}},
                {"industry": {"$eq": "General"}}
            ]
        }

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where_filter,
            include=["metadatas", "distances"]
        )
    except Exception:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["metadatas", "distances"]
        )

    if not results["metadatas"] or \
            not results["metadatas"][0]:
        return []

    retrieved = []
    for i, metadata in enumerate(results["metadatas"][0]):
        retrieved.append({
            "problem": metadata.get("problem", ""),
            "solution": metadata.get("solution", ""),
            "impact": metadata.get("impact", ""),
            "effort": metadata.get("effort", "medium"),
            "timeframe": metadata.get(
                "timeframe", "short_term"),
            "industry": metadata.get("industry", ""),
            "relevance_score": round(
                1 - results["distances"][0][i], 3)
        })

    return [doc for doc in retrieved
            if doc["relevance_score"] >= RELEVANCE_THRESHOLD]


def build_retrieval_query(
    top_issues: List[Dict],
    industry: str,
    dominant_emotion: str
) -> str:
    issue_parts = []
    for issue in top_issues[:3]:
        category = issue.get("category", "")
        example = issue.get("example", "")
        critical = issue.get("critical_count", 0)
        urgency = "critical" if critical > 0 else "medium"
        issue_parts.append(
            f"{category} {urgency} urgency: {example}"
        )

    return (
        f"Industry: {industry}\n"
        f"Customer emotion: {dominant_emotion}\n"
        f"Issues:\n" + "\n".join(issue_parts)
    )


def retrieve_per_issue(
    top_issues: List[Dict],
    industry: str,
    n_per_issue: int = 2
) -> Dict[str, List[Dict]]:
    """
    Retrieve relevant documents separately for each issue.
    Returns a dict mapping category name to its retrieved docs.
    This ensures each recommendation gets docs specific to
    its own problem not a mix of all problems combined.
    """
    results = {}
    for issue in top_issues[:5]:
        category = issue.get("category", "")
        example = issue.get("example", "")
        critical = issue.get("critical_count", 0)
        urgency = "critical" if critical > 0 else "medium"

        query = (
            f"Industry: {industry}\n"
            f"Problem: {category} - {example}\n"
            f"Tags: {category.lower()}"
        )

        try:
            raw_docs = retrieve_relevant_solutions(
                query, industry, n_results=n_per_issue)
            docs = [d for d in raw_docs
                    if d["relevance_score"] >= RELEVANCE_THRESHOLD]
            if not docs:
                logger.info(
                    f"{category}: no doc above threshold, "
                    f"LLM will use data only")
            results[category] = docs
        except Exception as e:
            logger.warning(
                f"RAG retrieval failed for {category}: {e}")
            results[category] = []

    return results
