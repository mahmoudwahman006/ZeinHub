from fastapi import FastAPI, APIRouter, Depends, File, UploadFile, status , Form
from fastapi.responses import JSONResponse
import os
import logging
import aiofiles

from helpers.config import get_settings, Settings
from controllers import LoadFilesController, ProcessFilesController
from models import ResponseSignal


logger = logging.getLogger('uvicorn.error')
 
files_router = APIRouter(
    prefix="/api/v1/files",
    tags=["api_v1", "files"],
)

@files_router.post("/upload/{project_id}")
async def upload_file(project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):

    load_files_controller = LoadFilesController()

    is_valid, result_signal = load_files_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": result_signal
            }
        )

    project_dir_path = load_files_controller.get_project_path(project_id=project_id)
    file_path, file_id = load_files_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=project_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:

        logger.error(f"Error while uploading file: {e}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
            }
        )

    return JSONResponse(
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id": file_id
            }
        )



@files_router.post("/process/{project_id}")

async def process_file(project_id: str, file_id: str, app_settings: Settings = Depends(get_settings)):

    process_files_controller = ProcessFilesController()

    try:
        ok, result = process_files_controller.process_file(
            project_id=project_id,
            file_id=file_id
        )
    except Exception:
        logger.exception("process_file crashed: project=%s file=%s", project_id, file_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.FILE_PROCESSING_FAILED.value},
        )
 
    if not ok:
        return JSONResponse(
            status_code= status.HTTP_400_BAD_REQUEST,
            content={"signal": result},
        )
 
    records = result["records"]
    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_PROCESS_SUCCESS.value,
            "records_count": result["count"],
            "languages": sorted({r["language"] for r in records}),
        }
    )


 
@files_router.get("/records/{project_id}")
async def get_records(
    project_id: str,
    file_id: str,
    limit: int = 20,
    offset: int = 0,
    app_settings: Settings = Depends(get_settings),
):
    process_files_controller = ProcessFilesController()
    ok, result = await process_files_controller.load_records(project_id=project_id,file_id=file_id)
    
    if not ok:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result},
        )
 
    records = result["records"]
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return JSONResponse(
        content={
            "total": len(records),
            "offset": offset,
            "limit": limit,
            "records": records[offset : offset + limit],
        }
    )