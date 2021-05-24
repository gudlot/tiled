from pathlib import Path

import typer
from typing import Optional


cli_app = typer.Typer()
serve_app = typer.Typer()
profile_app = typer.Typer()
cli_app.add_typer(serve_app, name="serve")
cli_app.add_typer(profile_app, name="profile")


@cli_app.command("download")
def download(
    catalog_uri: str,
    path: str,
    available_bytes: Optional[int] = None,
):
    """
    Download content from a Catalog to an on-disk cache.
    """
    from ..client.cache import download
    from ..client.catalog import Catalog

    catalog = Catalog.from_uri(catalog_uri)
    download(catalog, path=path, available_bytes=available_bytes)


@profile_app.command("paths")
def profile_paths():
    "List the locations that the client will search for profiles (client-side configuration)."
    from ..profiles import paths

    print("\n".join(paths))


@profile_app.command("list")
def profile_list():
    "List the profiles (client-side configuration) found and the files they were read from."
    from ..profiles import load_profiles

    profiles = load_profiles()
    if not profiles:
        typer.echo("No profiles found.")
        return
    max_len = max(len(name) for name in profiles)
    PADDING = 4

    print(
        "\n".join(
            f"{name:<{max_len + PADDING}}{filepath}"
            for name, (filepath, _) in profiles.items()
        )
    )


@profile_app.command("show")
def profile_show(profile_name: str):
    "Show the content of a profile."
    import yaml
    import sys

    from ..profiles import load_profiles

    profiles = load_profiles()
    try:
        filepath, content = profiles[profile_name]
    except KeyError:
        typer.echo(
            f"The profile {profile_name!r} could not be found. "
            "Use tiled profile list to see profile names."
        )
        raise typer.Abort()
    print(f"Source: {filepath}", file=sys.stderr)
    print("--", file=sys.stderr)
    print(yaml.dump(content), file=sys.stdout)


@serve_app.command("directory")
def serve_directory(
    directory: str,
    public: bool = typer.Option(False, "--public"),
):
    "Serve a Catalog instance from a directory of files."
    from ..catalogs.files import Catalog
    from ..server.app import serve_catalog, print_admin_api_key_if_generated

    catalog = Catalog.from_directory(directory)
    web_app = serve_catalog(catalog, allow_anonymous_access=public)
    print_admin_api_key_if_generated(web_app)

    import uvicorn

    uvicorn.run(web_app)


@serve_app.command("pyobject")
def serve_pyobject(
    object_path: str,  # e.g. "package_name.module_name:object_name"
    public: bool = typer.Option(False, "--public"),
):
    "Serve a Catalog instance from a Python module."
    from ..server.app import serve_catalog, print_admin_api_key_if_generated
    from ..utils import import_object

    catalog = import_object(object_path)

    web_app = serve_catalog(catalog, allow_anonymous_access=public)
    print_admin_api_key_if_generated(web_app)

    import uvicorn

    uvicorn.run(web_app)


@serve_app.command("config")
def serve_config(
    config_path: Path,
):
    "Serve a Catalog as specified in configuration file(s)."
    from ..config import construct_serve_catalog_kwargs, parse_configs

    try:
        parsed_config = parse_configs(config_path)
    except Exception as err:
        (msg,) = err.args
        typer.echo(msg)
        raise typer.Abort()

    # Delay this import, which is fairly expensive, so that
    # we can fail faster if config-parsing fails above.

    from ..server.app import serve_catalog, print_admin_api_key_if_generated

    kwargs = construct_serve_catalog_kwargs(parsed_config)
    web_app = serve_catalog(**kwargs)
    print_admin_api_key_if_generated(web_app)

    # Likewise, delay this import.

    import uvicorn

    uvicorn.run(web_app)


main = cli_app

if __name__ == "__main__":
    main()

# This object is used by the auto-generated documentation.
typer_click_object = typer.main.get_command(cli_app)
