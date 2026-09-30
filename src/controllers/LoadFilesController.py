from .BaseController import BaseController
from models import ResponseSignal

from fastapi import UploadFile
import re
import os
import random
import string

class LoadFilesController(BaseController):
    
    def __init__(self):
        super().__init__()
        self.size_scale = (1048576 * 10) # convert MB to bytes = 10 MB
        self.chunk_size = self.app_settings.FILE_DEFAULT_CHUNK_SIZE  ################



    def validate_uploaded_file(self, file: UploadFile):

        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value

    def get_project_path(self, project_id: str):
        project_dir = os.path.join(
            self.files_dir,
            project_id
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    def generate_unique_filepath(self, orig_file_name: str, project_id: str):

        random_key = self.generate_random_string()
        project_path = self.get_project_path(project_id=project_id)

        cleaned_file_name = self.get_clean_file_name(
            orig_file_name=orig_file_name
        )

        new_file_path = os.path.join(
            project_path,
            random_key + "_" + cleaned_file_name
        )

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path,
                random_key + "_" + cleaned_file_name
            )

        return new_file_path, random_key + "_" + cleaned_file_name

    def get_clean_file_name(self, orig_file_name: str):

        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name

    def generate_random_string(self, length: int=12):
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


