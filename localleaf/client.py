import json
import requests
import time

from bs4 import BeautifulSoup
from socketIO_client import SocketIO

from localleaf.settings import Settings


class OverleafClient:
    """
    Overleaf API Wrapper
    Supports login, querying all projects, querying a specific project, downloading a project and
    uploading a file to a project.
    """

    @staticmethod
    def filter_projects(json_content, more_attrs=None):
        more_attrs = more_attrs or {}
        for p in json_content["projects"]:
            if not p.get("archived") and not p.get("trashed"):
                if all(p.get(k) == v for k, v in more_attrs.items()):
                    yield p

    def __init__(self, cookie=None, csrf=None):
        self._cookie = cookie  # Store the cookie for authenticated requests
        self._csrf = csrf  # Store the CSRF token since it is needed for some requests
        self._settings = Settings()

    def login(self, username, password):
        """
        WARNING - DEPRECATED - Not working as Overleaf introduced captchas
        Login to the Overleaf Service with a username and a password
        Params: username, password
        Returns: Dict of cookie and CSRF
        """

        get_login = requests.get(self._settings.login_url())
        self._csrf = (
            BeautifulSoup(get_login.content, "html.parser")
            .find("input", {"name": "_csrf"})
            .get("value")
        )
        login_json = {"_csrf": self._csrf, "email": username, "password": password}
        post_login = requests.post(
            self._settings.login_url(), json=login_json, cookies=get_login.cookies
        )

        # On a successful authentication the Overleaf API returns a new authenticated cookie.
        # If the cookie is different than the cookie of the GET request the authentication was successful
        if (
            post_login.status_code == 200
            and get_login.cookies["overleaf_session2"]
            != post_login.cookies["overleaf_session2"]
        ):
            self._cookie = post_login.cookies

            # Enrich cookie with GCLB cookie from GET request above
            self._cookie["GCLB"] = get_login.cookies["GCLB"]

            # CSRF changes after making the login request, new CSRF token will be on the projects page
            projects_page = requests.get(
                self._settings.project_url(), cookies=self._cookie
            )
            self._csrf = (
                BeautifulSoup(projects_page.content, "html.parser")
                .find("meta", {"name": "ol-csrfToken"})
                .get("content")
            )

            return {"cookie": self._cookie, "csrf": self._csrf}

    def all_projects(self):
        """
        Get all of a user's active projects (= not archived and not trashed)
        Returns: List of project objects
        """
        projects_page = requests.get(self._settings.project_url(), cookies=self._cookie)
        json_content = json.loads(
            BeautifulSoup(projects_page.content, "html.parser")
            .find("meta", {"name": "ol-prefetchedProjectsBlob"})
            .get("content")
        )
        return list(OverleafClient.filter_projects(json_content))

    def get_project(self, project_name):
        """
        Get a specific project by project_name
        Params: project_name, the name of the project
        Returns: project object
        """

        projects_page = requests.get(self._settings.project_url(), cookies=self._cookie)
        json_content = json.loads(
            BeautifulSoup(projects_page.content, "html.parser")
            .find("meta", {"name": "ol-prefetchedProjectsBlob"})
            .get("content")
        )
        return next(
            OverleafClient.filter_projects(json_content, {"name": project_name}), None
        )

    def download_project(self, project_id):
        """
        Download project in zip format
        Params: project_id, the id of the project
        Returns: bytes string (zip file)
        """
        r = requests.get(
            self._settings.download_url(project_id), stream=True, cookies=self._cookie
        )
        return r.content

    def create_folder(self, project_id, parent_folder_id, folder_name):
        """
        Create a new folder in a project

        Params:
        project_id: the id of the project
        parent_folder_id: the id of the parent folder, root is the project_id
        folder_name: how the folder will be named

        Returns: folder id or None
        """

        params = {"parent_folder_id": parent_folder_id, "name": folder_name}
        headers = {"X-Csrf-Token": self._csrf}
        r = requests.post(
            self._settings.folder_url(project_id),
            cookies=self._cookie,
            headers=headers,
            json=params,
        )

        if r.ok:
            return json.loads(r.content)
        elif r.status_code == str(400):
            # Folder already exists
            return
        else:
            raise requests.HTTPError()

    def get_project_infos(self, project_id):
        """
        Get detailed project infos about the project

        Params:
        project_id: the id of the project

        Returns: project details
        """
        project_infos = None

        # Callback function for the joinProject emitter
        def set_project_infos(project_infos_dict):
            # Set project_infos variable in outer scope
            nonlocal project_infos
            project_infos = project_infos_dict["project"]

        # Convert cookie from CookieJar to string
        cookie = "GCLB={}; overleaf_session2={}".format(
            self._cookie["GCLB"], self._cookie["overleaf_session2"]
        )

        # Connect to Overleaf Socket.IO, send a time parameter and the cookies
        socket_io = SocketIO(
            self._settings.base_url(),
            params={"t": int(time.time()), "projectId": project_id},
            headers={"Cookie": cookie},
        )

        # Wait until we connect to the socket
        socket_io.on("connect", lambda: None)
        socket_io.wait_for_callbacks()

        # Send the joinProject event and receive the project infos
        socket_io.on("joinProjectResponse", set_project_infos)
        while not project_infos:
            socket_io.wait(1)

        # Disconnect from the socket if still connected
        if socket_io.connected:
            socket_io.disconnect()

        return project_infos

    def upload_file(self, project_id, project_infos, file_name, file):
        """
        Upload a file to the project

        Params:
        project_id: the id of the project
        file_name: how the file will be named
        file: the file itself

        Returns: True on success, False on fail
        """

        # Set the folder_id to the id of the root folder
        folder_id = project_infos["rootFolder"][0]["_id"]

        # The file name contains path separators, check folders
        if "/" in file_name:
            local_folders = file_name.split("/")[
                :-1
            ]  # Remove last item since this is the file name
            current_overleaf_folder = project_infos["rootFolder"][0][
                "folders"
            ]  # Set the current remote folder

            for local_folder in local_folders:
                exists_on_remote = False
                for remote_folder in current_overleaf_folder:
                    # Check if the folder exists on remote, continue with the new folder structure
                    if local_folder.lower() == remote_folder["name"].lower():
                        exists_on_remote = True
                        folder_id = remote_folder["_id"]
                        current_overleaf_folder = remote_folder["folders"]
                        break
                # Create the folder if it doesn't exist
                if not exists_on_remote:
                    new_folder = self.create_folder(project_id, folder_id, local_folder)
                    current_overleaf_folder.append(new_folder)
                    folder_id = new_folder["_id"]
                    current_overleaf_folder = new_folder["folders"]

        headers = {"X-CSRF-TOKEN": self._csrf}
        params = {"folder_id": folder_id}
        data = {"name": file_name.split("/")[-1]}
        files = {"qqfile": file.read()}

        # Upload the file to the predefined folder
        r = requests.post(
            self._settings.upload_url(project_id),
            cookies=self._cookie,
            headers=headers,
            data=data,
            params=params,
            files=files,
        )

        return r.status_code == str(200) and json.loads(r.content)["success"]

    def delete_file(self, project_id, project_infos, file_name):
        """
        Deletes a project's file

        Params:
        project_id: the id of the project
        file_name: how the file will be named

        Returns: True on success, False on fail
        """

        file = None

        # The file name contains path separators, check folders
        if "/" in file_name:
            local_folders = file_name.split("/")[
                :-1
            ]  # Remove last item since this is the file name
            current_overleaf_folder = project_infos["rootFolder"][0][
                "folders"
            ]  # Set the current remote folder

            for local_folder in local_folders:
                for remote_folder in current_overleaf_folder:
                    if local_folder.lower() == remote_folder["name"].lower():
                        file = next(
                            (
                                v
                                for v in remote_folder["docs"]
                                if v["name"] == file_name.split("/")[-1]
                            ),
                            None,
                        )
                        current_overleaf_folder = remote_folder["folders"]
                        break
        # File is in root folder
        else:
            file = next(
                (
                    v
                    for v in project_infos["rootFolder"][0]["docs"]
                    if v["name"] == file_name
                ),
                None,
            )

        # File not found!
        if file is None:
            return False

        headers = {"X-Csrf-Token": self._csrf}

        r = requests.delete(
            self._settings.delete_url(project_id, file["_id"]),
            cookies=self._cookie,
            headers=headers,
            json={},
        )

        return r.status_code == str(204)

    def download_pdf(self, project_id):
        """
        Compiles and returns a project's PDF

        Params:
        project_id: the id of the project

        Returns: PDF file name and content on success
        """
        headers = {"X-Csrf-Token": self._csrf}

        params = {"enable_pdf_caching": True}

        body = {
            "check": "silent",
            "draft": False,
            "incrementalCompilesEnabled": True,
            "rootDoc_id": "",
            "stopOnFirstError": False,
        }

        r = requests.post(
            self._settings.compile_url(project_id),
            cookies=self._cookie,
            headers=headers,
            params=params,
            json=body,
        )

        if not r.ok:
            raise requests.HTTPError()

        compile_result = json.loads(r.content)

        if compile_result["status"] != "success":
            raise requests.HTTPError()

        pdf_file = next(v for v in compile_result["outputFiles"] if v["type"] == "pdf")

        download_req = requests.get(
            self._settings.base_url() + pdf_file["url"],
            cookies=self._cookie,
            headers=headers,
        )

        if download_req.ok:
            return pdf_file["path"], download_req.content

        return None
