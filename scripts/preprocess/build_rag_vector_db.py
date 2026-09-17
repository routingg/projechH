"""Build text-only RAG documents and a FAISS vector store for WheelTrip Jeju."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 무장애여행정보 개별 관광지(제주데이터허브) — 데이터 경로 정리 후 위치
DEFAULT_RAW_DIR = (
    PROJECT_ROOT / "backend" / "data" / "raw"
    / "barrier_free_tourism" / "jejudatahub_attractions"
)
FALLBACK_RAW_DIR = PROJECT_ROOT / "dataset" / "jeju_files"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "backend" / "data" / "processed"
DEFAULT_VECTOR_DIR = PROJECT_ROOT / "vector_store"
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SOURCE_NAME = "제주데이터허브 무장애여행정보"
CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).replace("\ufeff", "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def first_non_empty(row: pd.Series, candidates: list[str]) -> str:
    lower_map = {str(col).strip().lower(): col for col in row.index}
    for candidate in candidates:
        col = lower_map.get(candidate.lower())
        if col is not None:
            value = clean_text(row.get(col))
            if value:
                return value
    return ""


def normalize_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def infer_data_id(file_path: Path) -> str | None:
    match = re.match(r"^(\d+)", file_path.stem)
    return match.group(1) if match else None


def infer_place_name(file_path: Path) -> str:
    name = file_path.stem
    name = re.sub(r"^\d+[_\-\s]*", "", name)
    prefixes = [
        "제주특별자치도_무장애여행정보_",
        "제주특별자치도 무장애여행정보 ",
        "무장애여행정보_",
        "무장애여행정보 ",
    ]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix) :]
    return name.strip(" _-")


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def scan_files(raw_dir: Path, processed_dir: Path) -> pd.DataFrame:
    files = sorted(
        path
        for path in raw_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".hwp"}
    )
    rows = []
    for path in files:
        rows.append(
            {
                "file_path": relative_or_absolute(path),
                "file_name": path.name,
                "extension": path.suffix.lower().lstrip("."),
                "parent_dir": relative_or_absolute(path.parent),
                "inferred_data_id": infer_data_id(path),
                "inferred_place_name": infer_place_name(path),
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(processed_dir / "file_manifest.csv", index=False, encoding="utf-8-sig")
    return manifest


def read_csv_with_fallback(path: Path) -> tuple[pd.DataFrame | None, str | None, str | None]:
    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(path, encoding=encoding, dtype=str)
            return frame, encoding, None
        except Exception as error:
            last_error = str(error)
    return None, None, last_error


def merge_csv_files(csv_paths: list[Path], processed_dir: Path) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    frames = []
    failures = []
    for path in csv_paths:
        frame, encoding, error = read_csv_with_fallback(path)
        if frame is None:
            failures.append({"file": relative_or_absolute(path), "error": error or "unknown error"})
            continue
        frame["source_file"] = relative_or_absolute(path)
        frame["source_file_name"] = path.name
        frame["source_encoding"] = encoding
        frame["inferred_data_id"] = infer_data_id(path)
        frame["inferred_place_name"] = infer_place_name(path)
        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    merged.to_csv(
        processed_dir / "accessibility_points_raw.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return merged, failures


def build_description(row: pd.Series) -> str:
    point_name = first_non_empty(row, ["장소명칭", "title", "Title", "장소", "시설명"])
    parts = []
    if point_name:
        parts.append(f"포인트: {point_name}")
    for candidates in [
        ["장소상세정보", "Description", "description", "설명", "내용"],
        ["무장애관광정보", "접근성정보", "accessibility"],
        ["etc", "비고"],
        ["info"],
    ]:
        value = first_non_empty(row, candidates)
        if value and value not in parts:
            parts.append(value)
    return ". ".join(parts)


def classify_category(description: str) -> str:
    rules = [
        ("parking", ["장애인 전용주차", "주차장", "주차"]),
        ("toilet", ["장애인 화장실", "화장실"]),
        ("slope", ["경사로", "경사", "오르막", "내리막"]),
        ("risk", ["배수구", "바퀴 끼임", "미끄러움", "위험", "주의", "턱"]),
        ("entrance", ["출입구", "입구", "매표소", "진입로"]),
        ("elevator", ["엘리베이터", "승강기", "리프트"]),
        ("route", ["관람로", "이동로", "통로", "산책로"]),
        ("rental", ["휠체어 대여", "대여소"]),
        ("rest", ["휴게", "쉼터", "카페", "휴식"]),
    ]
    for category, keywords in rules:
        if any(keyword in description for keyword in keywords):
            return category
    return "general"


def classify_risk_level(description: str) -> str:
    high_keywords = [
        "위험",
        "주의",
        "바퀴 끼임",
        "미끄러움",
        "급경사",
        "이용 불가",
        "진입 불가",
        "없음",
        "잠김",
        "턱",
        "계단",
    ]
    medium_keywords = ["경사", "오르막", "내리막", "배수구", "좁음"]
    if any(keyword in description for keyword in high_keywords):
        return "high"
    if any(keyword in description for keyword in medium_keywords):
        return "medium"
    return "low"


def extract_slope_degree(description: str) -> float | None:
    patterns = [
        r"(?:경사도?|오르막|내리막)[^\d]{0,8}(\d+(?:\.\d+)?)\s*도",
        r"(\d+(?:\.\d+)?)\s*도",
    ]
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return float(match.group(1))
    return None


def extract_length_m(description: str) -> float | None:
    patterns = [
        r"길이\s*(?:약\s*)?(\d+(?:\.\d+)?)\s*(cm|m)",
        r"(\d+(?:\.\d+)?)\s*(cm|m)\s*(?:구간|길이)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if not match:
            continue
        value = float(match.group(1))
        unit = match.group(2).lower()
        return value / 100 if unit == "cm" else value
    return None


def standardize_csv(raw: pd.DataFrame, processed_dir: Path) -> pd.DataFrame:
    if raw.empty:
        standardized = pd.DataFrame()
        standardized.to_csv(processed_dir / "accessibility_points.csv", index=False, encoding="utf-8-sig")
        return standardized

    rows = []
    for index, row in raw.iterrows():
        place_id = clean_text(row.get("inferred_data_id")) or first_non_empty(row, ["place_id"])
        place_name = clean_text(row.get("inferred_place_name")) or first_non_empty(
            row, ["관광지명", "시설명", "place_name"]
        )
        point_id = first_non_empty(row, ["Point", "point", "ID", "id", "아이디"]) or str(index + 1)
        lat = normalize_float(first_non_empty(row, ["위도", "lat", "latitude"]))
        lng = normalize_float(first_non_empty(row, ["경도", "lng", "lon", "longitude"]))
        altitude = normalize_float(first_non_empty(row, ["고도", "해발고도", "altitude"]))
        image_file = first_non_empty(row, ["이미지파일명", "이미지", "사진", "Image", "image"])
        description = build_description(row)
        category = classify_category(description)
        risk_level = classify_risk_level(description)

        record = row.to_dict()
        record.update(
            {
                "place_id": place_id or None,
                "place_name": place_name or None,
                "point_id": point_id or None,
                "lat": lat,
                "lng": lng,
                "altitude": altitude,
                "description": description,
                "image_file": image_file or None,
                "source_file": clean_text(row.get("source_file")),
                "source_file_name": clean_text(row.get("source_file_name")),
                "category": category,
                "risk_level": risk_level,
                "extracted_slope_degree": extract_slope_degree(description),
                "extracted_length_m": extract_length_m(description),
            }
        )
        rows.append(record)

    standardized = pd.DataFrame(rows)
    standardized.to_csv(
        processed_dir / "accessibility_points.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return standardized


def run_hwp5txt(path: Path) -> tuple[str, str | None]:
    command = shutil.which("hwp5txt")
    if command:
        result = subprocess.run(
            [command, str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout, None
        return "", result.stderr.strip() or result.stdout.strip()

    result = subprocess.run(
        ["python", "-m", "hwp5.hwp5txt", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        return result.stdout, None
    return "", result.stderr.strip() or result.stdout.strip()


def extract_hwp_texts(hwp_paths: list[Path], processed_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    txt_dir = ensure_dir(processed_dir / "hwp_txt")
    successes = []
    failures = []
    for path in hwp_paths:
        out_path = txt_dir / f"{path.stem}.txt"
        try:
            text, error = run_hwp5txt(path)
            text = text.replace("\r\n", "\n").strip()
            if error:
                failures.append({"file": relative_or_absolute(path), "error": error})
                continue
            if len(re.sub(r"\s+", "", text)) < 50:
                failures.append({"file": relative_or_absolute(path), "error": "extracted text shorter than 50 chars"})
                out_path.write_text(text, encoding="utf-8")
                continue
            out_path.write_text(text, encoding="utf-8")
            successes.append(
                {
                    "source_file": relative_or_absolute(path),
                    "txt_file": relative_or_absolute(out_path),
                    "place_name": infer_place_name(path),
                    "data_id": infer_data_id(path),
                    "text_length": len(text),
                }
            )
        except Exception as error:
            failures.append({"file": relative_or_absolute(path), "error": str(error)})
    return successes, failures


def csv_doc_text(place_name: str, category: str, description: str) -> str:
    templates = {
        "parking": "{place_name}의 주차 관련 무장애 접근성 정보: {description}",
        "toilet": "{place_name}의 화장실 관련 무장애 접근성 정보: {description}",
        "slope": "{place_name}의 경사로 및 경사 구간 정보: {description}",
        "risk": "{place_name}에서 주의가 필요한 접근성 정보: {description}",
        "entrance": "{place_name}의 입구 및 진입로 접근성 정보: {description}",
        "route": "{place_name}의 관람로 및 이동로 접근성 정보: {description}",
    }
    template = templates.get(category, "{place_name} 내부 접근성 포인트 정보: {description}")
    return template.format(place_name=place_name or "제주 관광지", description=description)


def safe_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, np.floating):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            clean_record = {key: safe_json_value(value) for key, value in record.items()}
            file.write(json.dumps(clean_record, ensure_ascii=False) + "\n")


def build_csv_rag_documents(points: pd.DataFrame, processed_dir: Path) -> list[dict[str, Any]]:
    docs = []
    if not points.empty:
        for _, row in points.iterrows():
            description = clean_text(row.get("description"))
            if not description:
                continue
            place_name = clean_text(row.get("place_name")) or "제주 관광지"
            category = clean_text(row.get("category")) or "general"
            doc = {
                "doc_id": f"csv_point_{len(docs) + 1:06d}",
                "place_id": clean_text(row.get("place_id")) or None,
                "place_name": place_name,
                "category": category,
                "risk_level": clean_text(row.get("risk_level")) or None,
                "text": csv_doc_text(place_name, category, description),
                "lat": safe_json_value(row.get("lat")),
                "lng": safe_json_value(row.get("lng")),
                "altitude": safe_json_value(row.get("altitude")),
                "image_file": clean_text(row.get("image_file")) or None,
                "source_type": "csv",
                "source_file": clean_text(row.get("source_file")),
                "source": SOURCE_NAME,
            }
            docs.append(doc)
    write_jsonl(processed_dir / "rag_documents_csv.jsonl", docs)
    return docs


def classify_hwp_category(text: str) -> str:
    rules = [
        ("usage", ["이용안내", "관람시간", "관람료"]),
        ("facility", ["편의시설", "부대시설", "화장실", "승강기", "엘리베이터"]),
        ("parking", ["주차장", "주차"]),
        ("address", ["주소"]),
        ("contact", ["문의", "전화"]),
        ("guide", ["관광지 소개", "정보", "설명"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "general"


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    sentences = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"[ \t]+", " ", paragraph)
        pieces = re.split(r"(?<=[.!?。])\s+", paragraph)
        for piece in pieces:
            piece = piece.strip()
            if piece:
                sentences.append(piece)
    return sentences


def chunk_text(text: str, chunk_size: int = 750, overlap: int = 100, min_size: int = 80) -> list[str]:
    sentences = split_sentences(text)
    chunks = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > chunk_size:
            if len(current) >= min_size:
                chunks.append(current.strip())
            current = current[-overlap:].strip() if overlap > 0 else ""
        current = f"{current} {sentence}".strip() if current else sentence
    if len(current) >= min_size:
        chunks.append(current.strip())
    return chunks


def build_hwp_rag_documents(processed_dir: Path) -> list[dict[str, Any]]:
    txt_dir = processed_dir / "hwp_txt"
    docs = []
    for txt_path in sorted(txt_dir.glob("*.txt")):
        text = txt_path.read_text(encoding="utf-8").strip()
        if len(re.sub(r"\s+", "", text)) < 50:
            continue
        place_name = infer_place_name(txt_path)
        data_id = infer_data_id(txt_path)
        for chunk in chunk_text(text):
            docs.append(
                {
                    "doc_id": f"hwp_doc_{len(docs) + 1:06d}",
                    "place_id": data_id,
                    "place_name": place_name,
                    "category": classify_hwp_category(chunk),
                    "risk_level": None,
                    "text": chunk,
                    "lat": None,
                    "lng": None,
                    "altitude": None,
                    "image_file": None,
                    "source_type": "hwp",
                    "source_file": relative_or_absolute(txt_path),
                    "source": SOURCE_NAME,
                }
            )
    write_jsonl(processed_dir / "rag_documents_hwp.jsonl", docs)
    return docs


def combine_rag_documents(csv_docs: list[dict[str, Any]], hwp_docs: list[dict[str, Any]], processed_dir: Path) -> list[dict[str, Any]]:
    combined = []
    seen_text = set()
    for doc in [*csv_docs, *hwp_docs]:
        text = clean_text(doc.get("text"))
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        new_doc = dict(doc)
        prefix = "csv_point" if new_doc.get("source_type") == "csv" else "hwp_doc"
        new_doc["doc_id"] = f"{prefix}_{len(combined) + 1:06d}"
        for key in ["source_type", "source_file", "source"]:
            if key not in new_doc:
                new_doc[key] = SOURCE_NAME if key == "source" else None
        combined.append(new_doc)
    write_jsonl(processed_dir / "rag_documents.jsonl", combined)
    return combined


def build_faiss_index(docs: list[dict[str, Any]], vector_dir: Path, model_name: str, batch_size: int) -> None:
    if not docs:
        raise RuntimeError("No RAG documents to embed.")
    index_dir = ensure_dir(vector_dir / "faiss_index")
    metadata_path = vector_dir / "metadata.jsonl"
    texts = [doc["text"] for doc in docs]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(index_dir / "index.faiss"))
    (index_dir / "config.json").write_text(
        json.dumps(
            {
                "model_name": model_name,
                "dimension": int(embeddings.shape[1]),
                "index_type": "IndexFlatIP",
                "metric": "cosine_similarity",
                "document_count": len(docs),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_jsonl(metadata_path, docs)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def search(query: str, vector_dir: Path, model_name: str, top_k: int) -> list[dict[str, Any]]:
    index_path = vector_dir / "faiss_index" / "index.faiss"
    metadata_path = vector_dir / "metadata.jsonl"
    index = faiss.read_index(str(index_path))
    docs = load_jsonl(metadata_path)
    model = SentenceTransformer(model_name)
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    scores, indices = index.search(query_embedding, top_k)
    results = []
    for score, doc_index in zip(scores[0], indices[0]):
        if doc_index < 0 or doc_index >= len(docs):
            continue
        doc = docs[int(doc_index)]
        results.append({"score": float(score), **doc})
    return results


def render_search_results(results: list[dict[str, Any]]) -> None:
    print("\nSearch results")
    print("=" * 80)
    for rank, result in enumerate(results, start=1):
        snippet = clean_text(result.get("text"))[:220]
        print(f"[{rank}] score={result['score']:.4f}")
        print(f"place_name: {result.get('place_name')}")
        print(f"category: {result.get('category')}")
        print(f"risk_level: {result.get('risk_level')}")
        print(f"source_type: {result.get('source_type')}")
        print(f"source_file: {result.get('source_file')}")
        print(f"text: {snippet}")
        print("-" * 80)


def missing_counts(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    result = {}
    for column in columns:
        if column not in frame.columns:
            result[column] = 0
            continue
        result[column] = int(frame[column].isna().sum() + (frame[column].astype(str).str.strip() == "").sum())
    return result


def markdown_count_table(title: str, counter: Counter) -> str:
    lines = [f"## {title}", "", "| value | count |", "| --- | ---: |"]
    for key, count in counter.most_common():
        lines.append(f"| {key or 'null'} | {count} |")
    lines.append("")
    return "\n".join(lines)


def write_quality_report(
    processed_dir: Path,
    csv_file_count: int,
    csv_failures: list[dict[str, str]],
    points_raw: pd.DataFrame,
    points: pd.DataFrame,
    hwp_file_count: int,
    hwp_successes: list[dict[str, Any]],
    hwp_failures: list[dict[str, str]],
    csv_docs: list[dict[str, Any]],
    hwp_docs: list[dict[str, Any]],
    combined_docs: list[dict[str, Any]],
) -> None:
    description_count = int(points["description"].astype(str).str.strip().ne("").sum()) if "description" in points else 0
    category_counter = Counter(points["category"].fillna("null").astype(str)) if "category" in points else Counter()
    risk_counter = Counter(points["risk_level"].fillna("null").astype(str)) if "risk_level" in points else Counter()
    place_counter = Counter(points["place_name"].fillna("null").astype(str)) if "place_name" in points else Counter()
    missing = missing_counts(
        points,
        ["place_id", "place_name", "point_id", "lat", "lng", "altitude", "description", "image_file"],
    )

    lines = [
        "# Data Quality Report",
        "",
        f"- 전체 CSV 파일 수: {csv_file_count}",
        f"- CSV 병합 성공 수: {csv_file_count - len(csv_failures)}",
        f"- CSV 병합 실패 수: {len(csv_failures)}",
        f"- 전체 CSV 행 수: {len(points_raw)}",
        f"- description이 있는 행 수: {description_count}",
        f"- HWP 파일 수: {hwp_file_count}",
        f"- HWP 텍스트 추출 성공 수: {len(hwp_successes)}",
        f"- HWP 텍스트 추출 실패 수: {len(hwp_failures)}",
        f"- CSV 기반 RAG 문서 수: {len(csv_docs)}",
        f"- HWP 기반 RAG 문서 수: {len(hwp_docs)}",
        f"- 최종 RAG 문서 수: {len(combined_docs)}",
        "",
        markdown_count_table("category 분포", category_counter),
        markdown_count_table("risk_level 분포", risk_counter),
        markdown_count_table("장소명 상위 20개", Counter(dict(place_counter.most_common(20)))),
        "## 결측치 현황",
        "",
        "| column | missing_count |",
        "| --- | ---: |",
    ]
    for column, count in missing.items():
        lines.append(f"| {column} | {count} |")
    lines.extend(["", "## 실패 파일 목록", ""])
    if not csv_failures and not hwp_failures:
        lines.append("- 없음")
    for failure in csv_failures:
        lines.append(f"- CSV: {failure['file']} - {failure['error']}")
    for failure in hwp_failures:
        lines.append(f"- HWP: {failure['file']} - {failure['error']}")
    lines.append("")
    (processed_dir / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def resolve_raw_dir(raw_dir: Path) -> Path:
    if raw_dir.exists():
        return raw_dir
    if raw_dir == DEFAULT_RAW_DIR and FALLBACK_RAW_DIR.exists():
        print(f"raw_dir not found, using fallback: {relative_or_absolute(FALLBACK_RAW_DIR)}")
        return FALLBACK_RAW_DIR
    raise FileNotFoundError(f"raw_dir not found: {raw_dir}")


def build(args: argparse.Namespace) -> list[dict[str, Any]]:
    raw_dir = resolve_raw_dir(args.raw_dir)
    processed_dir = ensure_dir(args.processed_dir)
    vector_dir = ensure_dir(args.vector_dir)

    manifest = scan_files(raw_dir, processed_dir)
    csv_paths = sorted(path for path in raw_dir.rglob("*.csv") if path.is_file())
    hwp_paths = sorted(path for path in raw_dir.rglob("*.hwp") if path.is_file())

    points_raw, csv_failures = merge_csv_files(csv_paths, processed_dir)
    points = standardize_csv(points_raw, processed_dir)
    hwp_successes, hwp_failures = extract_hwp_texts(hwp_paths, processed_dir)
    csv_docs = build_csv_rag_documents(points, processed_dir)
    hwp_docs = build_hwp_rag_documents(processed_dir)
    combined_docs = combine_rag_documents(csv_docs, hwp_docs, processed_dir)
    build_faiss_index(combined_docs, vector_dir, args.embedding_model, args.batch_size)
    write_quality_report(
        processed_dir=processed_dir,
        csv_file_count=int((manifest["extension"] == "csv").sum()) if not manifest.empty else 0,
        csv_failures=csv_failures,
        points_raw=points_raw,
        points=points,
        hwp_file_count=int((manifest["extension"] == "hwp").sum()) if not manifest.empty else 0,
        hwp_successes=hwp_successes,
        hwp_failures=hwp_failures,
        csv_docs=csv_docs,
        hwp_docs=hwp_docs,
        combined_docs=combined_docs,
    )
    print("\nBuild complete")
    print(f"raw_dir: {raw_dir}")
    print(f"processed_dir: {processed_dir}")
    print(f"vector_dir: {vector_dir}")
    print(f"csv_docs: {len(csv_docs)}")
    print(f"hwp_docs: {len(hwp_docs)}")
    print(f"combined_docs: {len(combined_docs)}")
    return combined_docs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WheelTrip Jeju RAG documents and FAISS vector DB.")
    parser.add_argument("--raw_dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--processed_dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--vector_dir", type=Path, default=DEFAULT_VECTOR_DIR)
    parser.add_argument("--embedding_model", default=DEFAULT_MODEL)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--query", default="")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--search_only", action="store_true", help="Skip rebuild and search the existing FAISS index.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.raw_dir = args.raw_dir if args.raw_dir.is_absolute() else PROJECT_ROOT / args.raw_dir
    args.processed_dir = args.processed_dir if args.processed_dir.is_absolute() else PROJECT_ROOT / args.processed_dir
    args.vector_dir = args.vector_dir if args.vector_dir.is_absolute() else PROJECT_ROOT / args.vector_dir

    if not args.search_only:
        build(args)
    elif not (args.vector_dir / "faiss_index" / "index.faiss").exists():
        raise FileNotFoundError(f"FAISS index not found: {args.vector_dir / 'faiss_index' / 'index.faiss'}")
    if args.query:
        results = search(args.query, args.vector_dir, args.embedding_model, args.top_k)
        render_search_results(results)


if __name__ == "__main__":
    main()
