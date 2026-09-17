"""RAG LLM(kanana-1.5-8b-instruct) 가중치 다운로드.

팀원 RAG 서버가 사용하는 모델(backend/app/config.py rag_model_name)을
ceph 저장소에 내려받는다. 재실행 시 받다 만 파일부터 이어받는다.

사용법:
    conda activate projecth
    python scripts/preprocess/download_llm.py
    # 경로 변경: python scripts/preprocess/download_llm.py --local-dir /다른/경로
"""
import argparse
import sys

from huggingface_hub import snapshot_download

DEFAULT_REPO = "kakaocorp/kanana-1.5-8b-instruct-2505"
DEFAULT_LOCAL_DIR = "/ceph_data/wq1880/barrierfree/models/kanana-1.5-8b-instruct-2505"


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG LLM 가중치 다운로드")
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR)
    args = parser.parse_args()

    print(f"다운로드: {args.repo_id}\n  → {args.local_dir}")
    path = snapshot_download(repo_id=args.repo_id, local_dir=args.local_dir)
    print(f"[성공] 모델 저장 완료: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
