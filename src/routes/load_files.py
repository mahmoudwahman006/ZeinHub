from fastapi import FastAPI, APIRouter, Depends, File, UploadFile, status 
from fastapi.responses import JSONResponse
import os
import logging
import aiofiles

from helpers.config import get_settings, Settings
from controllers import LoadFilesController
from models import ResponseSignal


logger = logging.getLogger('uvicorn.error')
 
load_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@load_router.post("/upload/{project_id}")
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

    pass 