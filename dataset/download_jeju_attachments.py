"""Download attachment files from Jeju Data Hub data pages."""

import argparse
import json
import time
import re
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://www.jejudatahub.net/data/view/data/{}"
VIEW_API_URL = "https://www.jejudatahub.net/api/data/view"
DOWNLOAD_API_URL = "https://www.jejudatahub.net/api/file/test-download"
DEFAULT_START_ID = 742
DEFAULT_END_ID = 622
SCRIPT_DIR = Path(__file__).resolve().parent


def safe_filename(name: str) -> str:
    bad_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.strip() or "download.zip"


def safe_extract_zip(zip_path: Path, output_dir: Path) -> None:
    target_dir = output_dir / zip_path.stem
    target_dir.mkdir(parents=True, exist_ok=True)
    target_root = target_dir.resolve()

    try:
        zf = zipfile.ZipFile(zip_path, "r", metadata_encoding="cp949")
    except TypeError:
        zf = zipfile.ZipFile(zip_path, "r")

    with zf:
        for member in zf.infolist():
            member_path = (target_dir / member.filename).resolve()
            if target_root not in [member_path, *member_path.parents]:
                raise RuntimeError(f"Unsafe path in zip: {member.filename}")
        zf.extractall(target_dir)

    print(f"Extracted: {target_dir}")


DEFAULT_EXTENSIONS = ["csv", "zip", "xlsx", "xls", "json", "xml"]


def extension_pattern(extensions):
    cleaned = [re.escape(ext.lower().lstrip(".")) for ext in extensions]
    return re.compile(r"\.({})$".format("|".join(cleaned)), re.IGNORECASE)


def open_json(url: str, timeout_sec: float):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_metadata(data_id: int, timeout_sec: float):
    params = urlencode({"id": data_id, "userId": "", "viewCount": "viewCount"})
    return open_json(f"{VIEW_API_URL}?{params}", timeout_sec)


def attachment_names(metadata, extensions):
    pattern = extension_pattern(extensions)
    seen = set()
    names = []
    for key in ["dataFile", "file"]:
        group = metadata.get(key) or {}
        for file_info in group.get("fileInfos") or []:
            filename = (file_info.get("fileName") or "").strip()
            file_key = (file_info.get("id"), file_info.get("fileId"), filename)
            if filename and pattern.search(filename) and file_key not in seen:
                names.append(file_info)
                seen.add(file_key)
    return names


def download_attachment(file_info, save_path: Path, timeout_sec: float, referer: str) -> bool:
    params = {
        "id": file_info["id"],
        "fileId": file_info["fileId"],
        "fileName": file_info["fileName"],
        "fileSize": file_info["fileSize"],
        "contentType": file_info["contentType"],
        "saveFileName": file_info["saveFileName"],
        "downloadCount": file_info.get("downloadCount", 0),
        "createAt": file_info["createAt"],
        "createBy": file_info["createBy"],
    }
    url = f"{DOWNLOAD_API_URL}?{urlencode(params)}"
    expected_size = int(file_info.get("fileSize") or 0)
    tmp_path = save_path.with_name(f"{save_path.name}.part")

    if expected_size and save_path.exists() and save_path.stat().st_size < expected_size:
        save_path.replace(tmp_path)

    offset = tmp_path.stat().st_size if tmp_path.exists() else 0
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer,
    }
    if offset:
        headers["Range"] = f"bytes={offset}-"

    request = Request(
        url,
        headers=headers,
    )
    with urlopen(request, timeout=timeout_sec) as response:
        status = getattr(response, "status", None)
        if offset and status != 206:
            tmp_path.unlink(missing_ok=True)
            offset = 0
        mode = "ab" if offset else "wb"
        with tmp_path.open(mode) as out_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out_file.write(chunk)
    actual_size = tmp_path.stat().st_size
    if expected_size and actual_size != expected_size:
        raise RuntimeError(f"incomplete download: expected {expected_size} bytes, got {actual_size} bytes")
    tmp_path.replace(save_path)
    return True


def run(args):
    file_dir = args.output_root / "jeju_files"
    extract_dir = args.output_root / "jeju_extracted"
    file_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    downloaded = []

    for data_id in range(args.start_id, args.end_id - 1, -1):
        page_url = BASE_URL.format(data_id)
        print(f"\n[{data_id}] Read metadata: {page_url}")

        try:
            metadata = fetch_metadata(data_id, args.request_timeout_sec)
            attachments = attachment_names(metadata, args.extensions)
            if not attachments:
                print(f"No matching attachments: {data_id}")
                failed.append(
                    {
                        "data_id": data_id,
                        "error": "matching attachment not found",
                        "extensions": args.extensions,
                    }
                )
                continue

            for attachment in attachments:
                filename = safe_filename(attachment["fileName"])
                save_path = file_dir / f"{data_id}_{filename}"

                expected_size = int(attachment.get("fileSize") or 0)
                complete_existing = (
                    save_path.exists()
                    and (not expected_size or save_path.stat().st_size == expected_size)
                )
                if complete_existing and not args.overwrite:
                    print(f"Already exists: {save_path}")
                    downloaded.append(str(save_path))
                else:
                    if save_path.exists() and not complete_existing:
                        print(
                            "Redownload incomplete file: "
                            f"{save_path} ({save_path.stat().st_size}/{expected_size})"
                        )
                    print(f"Download: {filename}")
                    last_error = None
                    for attempt in range(1, args.retries + 1):
                        try:
                            download_attachment(
                                attachment,
                                save_path,
                                args.download_timeout_ms / 1000,
                                page_url,
                            )
                            last_error = None
                            break
                        except Exception as error:
                            last_error = error
                            print(f"Retry {attempt}/{args.retries} failed: {error}")
                    if last_error is not None:
                        raise last_error
                    print(f"Saved: {save_path}")
                    downloaded.append(str(save_path))

                if save_path.suffix.lower() == ".zip" and not args.no_extract:
                    try:
                        safe_extract_zip(save_path, extract_dir)
                    except Exception as extract_error:
                        print(f"Extract failed: {save_path} / {extract_error}")
                        failed.append(
                            {
                                "data_id": data_id,
                                "error": f"extract failed: {extract_error}",
                            }
                        )

            time.sleep(args.sleep_sec)

        except Exception as error:
            print(f"Failed: {data_id} / {error}")
            failed.append({"data_id": data_id, "error": str(error)})

    summary = {
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "downloaded": downloaded,
        "failed": failed,
    }
    summary_path = args.output_root / "jeju_download_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\nDone")
    print(f"Downloaded count: {len(downloaded)}")
    print(f"Failed count: {len(failed)}")
    print(f"Summary: {summary_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Download Jeju Data Hub attachments.")
    parser.add_argument("--start-id", type=int, default=DEFAULT_START_ID)
    parser.add_argument("--end-id", type=int, default=DEFAULT_END_ID)
    parser.add_argument("--output-root", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--request-timeout-sec", type=float, default=30)
    parser.add_argument("--page-timeout-ms", type=int, default=30000)
    parser.add_argument("--download-timeout-ms", type=int, default=120000)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--headed", action="store_true", help="Show browser window.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-extract", action="store_true")
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=DEFAULT_EXTENSIONS,
        help="Attachment extensions to download. Example: --extensions csv zip hwp",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
