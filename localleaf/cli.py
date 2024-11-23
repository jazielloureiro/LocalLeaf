import click
import os
import pickle
import zipfile
import io
import dateutil.parser
import glob
import fnmatch
import traceback
from pathlib import Path

from localleaf.client import OverleafClient
from localleaf.browser import OverleafBrowser


@click.group()
@click.option(
    "--cookie-path",
    "cookie_path",
    default=".olauth",
    type=click.Path(exists=False),
    help="Relative path to load the persisted Overleaf cookie.",
)
@click.option(
    "-v", "--verbose", "verbose", is_flag=True, help="Enable extended error logging."
)
@click.pass_context
def cli(ctx, cookie_path, verbose):
    ctx.ensure_object(dict)

    ctx.obj["cookie_path"] = cookie_path
    ctx.obj["verbose"] = verbose


@cli.command(name="login")
@click.pass_context
def login(ctx):
    if os.path.isfile(ctx.obj["cookie_path"]) and not click.confirm(
        "Persisted Overleaf cookie already exist. Do you want to override it?"
    ):
        return

    execute_action(
        lambda: login_handler(ctx.obj["cookie_path"]),
        "Login successful. Cookie persisted as `"
        + click.format_filename(ctx.obj["cookie_path"])
        + "`. You may now sync your project.",
        "Login failed. Please try again.",
        ctx.obj["verbose"],
    )


@cli.command(name="list")
@click.pass_context
def list_projects(ctx):
    def query_projects():
        for i in sorted(
            overleaf_client.all_projects(),
            key=lambda x: x["lastUpdated"],
            reverse=True,
        ):
            click.echo(
                f"{dateutil.parser.isoparse(i['lastUpdated']).strftime('%m/%d/%Y, %H:%M:%S')} - {i['name']}"
            )
        return True

    if not os.path.isfile(ctx.obj["cookie_path"]):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path."
        )

    with open(ctx.obj["cookie_path"], "rb") as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    execute_action(
        query_projects,
        "Querying all projects successful.",
        "Querying all projects failed. Please try again.",
        ctx.obj["verbose"],
    )


@cli.command(name="download")
@click.option(
    "-n",
    "--name",
    "project_name",
    default="",
    help="Specify the Overleaf project name instead of the default name of the sync directory.",
)
@click.option(
    "--download-path", "download_path", default=".", type=click.Path(exists=True)
)
@click.pass_context
def download_pdf(ctx, project_name, download_path):
    def download_project_pdf():
        nonlocal project_name
        project_name = project_name or os.path.basename(os.getcwd())
        project = execute_action(
            lambda: overleaf_client.get_project(project_name),
            "Project queried successfully.",
            "Project could not be queried.",
            ctx.obj["verbose"],
        )

        file_name, content = overleaf_client.download_pdf(project["id"])

        if file_name and content:
            # Change the current directory to the specified sync path
            os.chdir(download_path)
            open(file_name, "wb").write(content)

        return True

    if not os.path.isfile(ctx.obj["cookie_path"]):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path."
        )

    with open(ctx.obj["cookie_path"], "rb") as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    execute_action(
        download_project_pdf,
        "Downloading project's PDF successful.",
        "Downloading project's PDF failed. Please try again.",
        ctx.obj["verbose"],
    )


@cli.command(name="pull")
@click.option(
    "-n",
    "--name",
    "project_name",
    default="",
    help="Specify the Overleaf project name instead of the default name of the sync directory.",
)
@click.option(
    "-p",
    "--path",
    "sync_path",
    default=".",
    type=click.Path(exists=True),
    help="Path of the project to sync.",
)
@click.option(
    "-i",
    "--olignore",
    "olignore_path",
    default=".olignore",
    type=click.Path(exists=False),
    help="Path to the .olignore file relative to sync path (ignored if syncing from remote to local). See "
    "fnmatch / unix filename pattern matching for information on how to use it.",
)
@click.pass_context
def pull_changes(ctx, project_name, sync_path, olignore_path):
    if not os.path.isfile(ctx.obj["cookie_path"]):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path."
        )

    with open(ctx.obj["cookie_path"], "rb") as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    # Change the current directory to the specified sync path
    os.chdir(sync_path)

    project_name = project_name or os.path.basename(os.getcwd())
    project = execute_action(
        lambda: overleaf_client.get_project(project_name),
        "Project queried successfully.",
        "Project could not be queried.",
        ctx.obj["verbose"],
    )

    project_infos = execute_action(
        lambda: overleaf_client.get_project_infos(project["id"]),
        "Project details queried successfully.",
        "Project details could not be queried.",
        ctx.obj["verbose"],
    )

    zip_file = execute_action(
        lambda: zipfile.ZipFile(
            io.BytesIO(overleaf_client.download_project(project["id"]))
        ),
        "Project downloaded successfully.",
        "Project could not be downloaded.",
        ctx.obj["verbose"],
    )

    sync_func(
        files_from=zip_file.namelist(),
        deleted_files=[
            f for f in olignore_keep_list(olignore_path) if f not in zip_file.namelist()
        ],
        create_file_at_to=lambda name: write_file(name, zip_file.read(name)),
        delete_file_at_to=lambda name: delete_file(name),
        create_file_at_from=lambda name: overleaf_client.upload_file(
            project["id"], project_infos, name, open(name, "rb")
        ),
        from_exists_in_to=lambda name: os.path.isfile(name),
        from_equal_to_to=lambda name: open(name, "rb").read() == zip_file.read(name),
        from_newer_than_to=lambda name: dateutil.parser.isoparse(
            project["lastUpdated"]
        ).timestamp()
        > os.path.getmtime(name),
        from_name="remote",
        to_name="local",
        verbose=ctx.obj["verbose"],
    )


@cli.command(name="push")
@click.option(
    "-n",
    "--name",
    "project_name",
    default="",
    help="Specify the Overleaf project name instead of the default name of the sync directory.",
)
@click.option(
    "-p",
    "--path",
    "sync_path",
    default=".",
    type=click.Path(exists=True),
    help="Path of the project to sync.",
)
@click.option(
    "-i",
    "--olignore",
    "olignore_path",
    default=".olignore",
    type=click.Path(exists=False),
    help="Path to the .olignore file relative to sync path (ignored if syncing from remote to local). See "
    "fnmatch / unix filename pattern matching for information on how to use it.",
)
@click.pass_context
def push_changes(ctx, project_name, sync_path, olignore_path):
    if not os.path.isfile(ctx.obj["cookie_path"]):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path."
        )

    with open(ctx.obj["cookie_path"], "rb") as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    # Change the current directory to the specified sync path
    os.chdir(sync_path)

    project_name = project_name or os.path.basename(os.getcwd())
    project = execute_action(
        lambda: overleaf_client.get_project(project_name),
        "Project queried successfully.",
        "Project could not be queried.",
        ctx.obj["verbose"],
    )

    project_infos = execute_action(
        lambda: overleaf_client.get_project_infos(project["id"]),
        "Project details queried successfully.",
        "Project details could not be queried.",
        ctx.obj["verbose"],
    )

    zip_file = execute_action(
        lambda: zipfile.ZipFile(
            io.BytesIO(overleaf_client.download_project(project["id"]))
        ),
        "Project downloaded successfully.",
        "Project could not be downloaded.",
        ctx.obj["verbose"],
    )

    keep_list = olignore_keep_list(olignore_path)

    sync_func(
        files_from=keep_list,
        deleted_files=[f for f in zip_file.namelist() if f not in keep_list],
        create_file_at_to=lambda name: overleaf_client.upload_file(
            project["id"], project_infos, name, open(name, "rb")
        ),
        delete_file_at_to=lambda name: overleaf_client.delete_file(
            project["id"], project_infos, name
        ),
        create_file_at_from=lambda name: write_file(name, zip_file.read(name)),
        from_exists_in_to=lambda name: name in zip_file.namelist(),
        from_equal_to_to=lambda name: open(name, "rb").read() == zip_file.read(name),
        from_newer_than_to=lambda name: os.path.getmtime(name)
        > dateutil.parser.isoparse(project["lastUpdated"]).timestamp(),
        from_name="local",
        to_name="remote",
        verbose=ctx.obj["verbose"],
    )


def login_handler(path):
    store = OverleafBrowser().login()
    if store is None:
        return False
    with open(path, "wb+") as f:
        pickle.dump(store, f)
    return True


def delete_file(path):
    _dir = os.path.dirname(path)
    if _dir == path:
        return

    if _dir != "" and not os.path.exists(_dir):
        return
    else:
        os.remove(path)


def write_file(path, content):
    _dir = os.path.dirname(path)
    if _dir == path:
        return

    # path is a file
    if _dir != "" and not os.path.exists(_dir):
        os.makedirs(_dir)

    with open(path, "wb+") as f:
        f.write(content)


def sync_func(
    files_from,
    deleted_files,
    create_file_at_to,
    delete_file_at_to,
    create_file_at_from,
    from_exists_in_to,
    from_equal_to_to,
    from_newer_than_to,
    from_name,
    to_name,
    verbose=False,
):
    click.echo("Syncing files from [%s] to [%s]" % (from_name, to_name))

    newly_add_list = []
    update_list = []
    delete_list = []
    restore_list = []
    not_restored_list = []
    not_sync_list = []
    synced_list = []

    for name in files_from:
        if from_exists_in_to(name):
            if not from_equal_to_to(name):
                if not from_newer_than_to(name) and not click.confirm(
                    "\n-> Warning: last-edit time stamp of file <%s> from [%s] is older than [%s].\nContinue to "
                    "overwrite with an older version?" % (name, from_name, to_name)
                ):
                    not_sync_list.append(name)
                    continue

                update_list.append(name)
            else:
                synced_list.append(name)
        else:
            newly_add_list.append(name)

    for name in deleted_files:
        delete_choice = click.prompt(
            "\n-> Warning: file <%s> does not exist on [%s] anymore (but it still exists on [%s])."
            "\nShould the file be [d]eleted, [r]estored or [i]gnored?"
            % (name, from_name, to_name),
            default="i",
            type=click.Choice(["d", "r", "i"]),
        )
        if delete_choice == "d":
            delete_list.append(name)
        elif delete_choice == "r":
            restore_list.append(name)
        elif delete_choice == "i":
            not_restored_list.append(name)

    if len(newly_add_list):
        click.echo("[NEW] Following new file(s) created on [%s]" % to_name)

    for name in newly_add_list:
        click.echo("\t%s" % name)
        try:
            create_file_at_to(name)
        except:
            if verbose:
                print(traceback.format_exc())
            raise click.ClickException(
                "\n[ERROR] An error occurred while creating new file(s) on [%s]"
                % to_name
            )

    if len(restore_list):
        click.echo("[NEW] Following new file(s) created on [%s]" % from_name)

    for name in restore_list:
        click.echo("\t%s" % name)
        try:
            create_file_at_from(name)
        except:
            if verbose:
                print(traceback.format_exc())
            raise click.ClickException(
                "\n[ERROR] An error occurred while creating new file(s) on [%s]"
                % from_name
            )

    if len(update_list):
        click.echo("[UPDATE] Following file(s) updated on [%s]" % to_name)

    for name in update_list:
        click.echo("\t%s" % name)
        try:
            create_file_at_to(name)
        except:
            if verbose:
                print(traceback.format_exc())
            raise click.ClickException(
                "\n[ERROR] An error occurred while updating file(s) on [%s]" % to_name
            )

    if len(delete_list):
        click.echo("[DELETE] Following file(s) deleted on [%s]" % to_name)

    for name in delete_list:
        click.echo("\t%s" % name)
        try:
            delete_file_at_to(name)
        except:
            if verbose:
                print(traceback.format_exc())
            raise click.ClickException(
                "\n[ERROR] An error occurred while creating new file(s) on [%s]"
                % to_name
            )

    if len(synced_list):
        click.echo("[SYNC] Following file(s) are up to date")

    for name in synced_list:
        click.echo("\t%s" % name)

    if len(not_sync_list):
        click.echo(
            "[SKIP] Following file(s) on [%s] have not been synced to [%s]"
            % (from_name, to_name)
        )

    for name in not_sync_list:
        click.echo("\t%s" % name)

    if len(not_restored_list):
        click.echo(
            "[SKIP] Following file(s) on [%s] have not been synced to [%s]"
            % (to_name, from_name)
        )

    for name in not_restored_list:
        click.echo("\t%s" % name)


def execute_action(action, success_message, fail_message, verbose_error_logging=False):
    try:
        success = action()
    except:
        if verbose_error_logging:
            print(traceback.format_exc())
        success = False

    if success:
        click.echo(success_message)
    else:
        raise click.ClickException(fail_message)

    return success


def olignore_keep_list(olignore_path):
    """
    The list of files to keep synced, with support for sub-folders.
    Should only be called when syncing from local to remote.
    """
    # get list of files recursively (ignore .* files)
    files = glob.glob("**", recursive=True)

    if not os.path.isfile(olignore_path):
        click.echo("Notice: .olignore file does not exist, will sync all items.")
        keep_list = files
    else:
        click.echo(".olignore: using %s to filter items" % olignore_path)
        with open(olignore_path, "r") as f:
            ignore_pattern = f.read().splitlines()

        keep_list = [
            f
            for f in files
            if not any(fnmatch.fnmatch(f, ignore) for ignore in ignore_pattern)
        ]

    keep_list = [Path(item).as_posix() for item in keep_list if not os.path.isdir(item)]
    return keep_list
