import os
import uuid
import aiofiles
from fastapi import UploadFile, File, HTTPException
from app.config import get_settings

settings = get_settings()


class FileStorage:
    def __init__(self):
        os.makedirs(settings.upload_dir, exist_ok=True)

    async def save(self, file: UploadFile, subfolder: str = "") -> str:
        os.makedirs(os.path.join(settings.upload_dir, subfolder), exist_ok=True)

        ext = os.path.splitext(file.filename or "")[1].lower()
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.upload_dir, subfolder, f"{file_id}{ext}")

        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(status_code=400, detail=f"文件大小不能超过 {settings.max_file_size_mb}MB")
        await file.seek(0)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return file_path

    def delete(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False
