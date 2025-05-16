from os import sep
from platformdirs import user_config_dir


class Settings:
    def __init__(self, overleaf_host="www.overleaf.com", overleaf_protocol="https"):
        self._default_cookie_path = user_config_dir(
            appname="localleaf", appauthor=False, ensure_exists=True
        )
        self._overleaf_host = overleaf_host
        self._overleaf_url = f"{overleaf_protocol}://{overleaf_host}"

    def default_cookie_path(self):
        return f"{self._default_cookie_path}{sep}.olauth"

    def overleaf_host(self):
        return self._overleaf_host

    def base_url(self):
        return self._overleaf_url

    def base_websocket_url(self):
        return f"{self._overleaf_url}/socket.io/1"

    def project_websocket_url(self, socket_id, project_id):
        return f"wss://{self._overleaf_host}/socket.io/1/websocket/{socket_id}?projectId={project_id}"

    def login_url(self):
        return f"{self._overleaf_url}/login"

    def project_url(self):
        return f"{self._overleaf_url}/project"

    def project_id_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}"

    def download_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/download/zip"

    def upload_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/upload"

    def folder_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/folder"

    def delete_url(self, project_id, file_type_path, file_id):
        return f"{self._overleaf_url}/project/{project_id}/{file_type_path}/{file_id}"

    def compile_url(self, project_id):
        return f"{self._overleaf_url}/project/{project_id}/compile"
