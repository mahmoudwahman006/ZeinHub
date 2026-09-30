from .BaseController import BaseController
from .LoadFilesController import LoadFilesController
from models import ResponseSignal
import os 
import json
import aiofiles
from helpers.normalize import (  # e.g. from app.ingestion.normalize import ...
    clean_text,
    detect_language_safe,
    normalize_arabic,
)
 
from pypdf import PdfReader




def read_txt_pages(file_path: str) -> list[dict]:
    """A TXT file is one 'page'. utf-8-sig also strips a Windows BOM.
    Raises UnicodeDecodeError if the file is not UTF-8 (caller handles it)."""
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return [{"page": None, "text": f.read()}]


def read_pdf_pages(file_path: str) -> list[dict]:
    """One entry per PDF page, 1-based page numbers kept for citations.
    A scanned (image-only) PDF yields empty text for every page."""
    reader = PdfReader(file_path)
    return [
        {"page": number, "text": page.extract_text() or ""}
        for number, page in enumerate(reader.pages, start=1)
    ]


def build_records(pages: list[dict], source_name: str) -> list[dict]:
    """Clean + language-tag + normalize each page; skip pages with no text.

    `text`            -> cleaned, human-readable (show this to users / the LLM)
    `text_normalized` -> Arabic search-normalized (use this for matching only)
    """
    records = []
    for page in pages:
        text = clean_text(page["text"])
        if not text:
            continue
        language = detect_language_safe(text)
        text_normalized = normalize_arabic(text) if language == "ar" else text
        records.append(
            {
                "source": source_name,
                "page": page["page"],
                "language": language,
                "text": text,
                "text_normalized": text_normalized,
            }
        )
    return records


class ProcessFilesController(BaseController):
    
    def __init__(self):
        super().__init__()
        self.size_scale = (1048576 * 10) # convert MB to bytes = 10 MB
        self.chunk_size = self.app_settings.FILE_DEFAULT_CHUNK_SIZE  ################

    

    def get_file_content(self, project_id: str, file_id: str):
        project_path = LoadFilesController.get_project_path(self, project_id=project_id)
        file_path = os.path.join(project_path, file_id)
 
        if not os.path.exists(file_path):
            return False, ResponseSignal.FILE_NOT_FOUND.value
 
        extension = os.path.splitext(file_id)[1].lower()
        try:
            if extension == ".txt":
                pages = read_txt_pages(file_path)
            elif extension == ".pdf":
                pages = read_pdf_pages(file_path)
            else:
                return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        except Exception:
            return False, ResponseSignal.FILE_PROCESSING_FAILED.value
 
        return True, {"pages": pages}
 
    def process_file(self, project_id: str, file_id: str, source_name: str | None = None):
        """source_name: the ORIGINAL file name for citations (the stored name
        is random). Falls back to file_id when not given."""
        ok, result = self.get_file_content(project_id=project_id, file_id=file_id)
        if not ok:
            return False, result
 
        records = build_records(result["pages"], source_name or file_id)
        if not records:
            # empty file, or a scanned PDF with no text layer
            return False, ResponseSignal.FILE_NO_TEXT.value
        try:
            self.save_records(project_id, file_id, records)
        except OSError:
            return False, ResponseSignal.FILE_PROCESSING_FAILED.value
 
        return True, {"records": records, "count": len(records)} 


     # ---- corpus storage: one JSON file per uploaded file (DVC-friendly) ----
 
    corpus_dir = "assets/corpus"  # kept apart from the raw uploads in assets/
 
    def get_corpus_file_path(self, project_id: str, file_id: str) -> str:
        return os.path.join(self.corpus_dir, project_id, f"{file_id}.json")
 
    def save_records(self, project_id: str, file_id: str, records: list[dict]) -> str:
        path = self.get_corpus_file_path(project_id, file_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            # ensure_ascii=False keeps Arabic readable instead of \u0645\u0631...
            json.dump(records, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)  # atomic: never leaves a half-written file
        return path
 
    async def load_records(self, project_id: str, file_id: str):
        path = self.get_corpus_file_path(project_id, file_id)
        if not os.path.exists(path):
            return False, ResponseSignal.FILE_RECORDS_NOT_FOUND.value
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
                return True, {"records": json.loads(content)}
        except (OSError, json.JSONDecodeError):
            return False, ResponseSignal.FILE_PROCESSING_FAILED.value
 