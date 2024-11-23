from os import sep
from platformdirs import user_config_dir


class Settings:
    def __init__(self, overleaf_url="https://www.overleaf.com"):
        self._default_cookie_path = user_config_dir(
            appname="localleaf", appauthor=False, ensure_exists=True
        )
        self._overleaf_url = overleaf_url

    def default_cookie_path(self):
        return f"{self._default_cookie_path}{sep}.olauth"

    def base_url(self):
        return self._overleaf_url

    def login_url(self):
        return f"{self._overleaf_url}/login"

    def project_url(self):
        return f"{self._overleaf_url}/project"

    def download_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/download/zip"

    def upload_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/upload"

    def folder_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/folder"

    def delete_url(self, project_id, file_id):
        return f"{self._overleaf_url}/project/{project_id}/doc/{file_id}"

    def compile_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/compile"
