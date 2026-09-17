from fastapi import APIRouter

from app.schemas.rag import RagAskRequest, RagAskResponse, RagRequest, RagResponse
from app.services import rag_client

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/recommend", response_model=RagResponse)
def recommend(payload: RagRequest) -> RagResponse:
    """RAG 팀원 서버로의 gateway. 미연결 시 mock 설명을 반환한다."""
    return rag_client.get_recommendation(payload)


@router.post("/ask", response_model=RagAskResponse)
def ask(payload: RagAskRequest) -> RagAskResponse:
    """로컬 FAISS 벡터DB에서 관련 문서를 검색한다. LLM 답변 생성은 별도 RAG 서버 담당."""
    from app.services.retriever import retrieve_documents

    documents = retrieve_documents(
        query=payload.question,
        place_name=payload.place_name,
        category=payload.category,
        top_k=payload.top_k,
    )
    return RagAskResponse(question=payload.question, retrieved_documents=documents)
