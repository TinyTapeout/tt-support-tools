import base64
import errno
import logging
import os
import sys
import typing
from urllib.parse import urlparse

import requests
from git.repo import Repo


def fetch_file(url: str, filename: str):
    logging.info("trying to download {}".format(url))
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning("couldn't download {}".format(url))
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)

    with open(filename, "wb") as fh:
        logging.info("written to {}".format(filename))
        fh.write(r.content)


def check_status(r: requests.Response):
    if r.status_code == 401:
        logging.error(
            "unauthorised, check INFO.md for information about GitHub API keys"
        )
        exit(1)


def headers_try_to_add_authorization_from_environment(
    headers: typing.Dict[str, str]
) -> bool:
    gh_token = os.getenv("GH_TOKEN", "")  # override like gh CLI
    if not gh_token:
        gh_token = os.getenv("GITHUB_TOKEN", "")  # GHA inherited

    if len(gh_token) > 0:
        # As per https://docs.github.com/en/rest/overview/authenticating-to-the-rest-api
        headers["authorization"] = "Bearer " + gh_token
        return True

    # Use a token instead which is designed to limit exposure of passwords
    # I can't find any GH docs explaining use cases for Basic auth and confirming a token
    # can be used instead of PASSWORD in the password field of authorization header.
    gh_username = os.getenv("GH_USERNAME", "")  # override like gh CLI
    if not gh_username:
        gh_username = os.getenv("GITHUB_ACTOR", "")  # GHA inherited

    gh_password = os.getenv("GH_PASSWORD", "")

    if len(gh_username) > 0 and len(gh_password) > 0:
        auth_string = gh_username + ":" + gh_password
        encoded = base64.b64encode(auth_string.encode("ascii"))
        headers["authorization"] = "Basic " + encoded.decode("ascii")
        return True

    print(
        "WARNING: No github token found from environment, trying public API requests without, see docs/INFO.md#instructions-to-build-gds",
        file=sys.stderr,
    )
    return False


def get_most_recent_action_page(
    commits: typing.List[typing.Dict[str, str]],
    runs: typing.List[typing.Dict[str, str]],
) -> typing.Optional[str]:
    release_sha_to_page_url = {
        run["head_sha"]: run["html_url"] for run in runs if run["name"] == "gds"
    }
    for commit in commits:
        if commit["sha"] in release_sha_to_page_url:
            return release_sha_to_page_url[commit["sha"]]
    return None


def split_git_url(url: str):
    res = urlparse(url)
    try:
        _, user_name, repo = res.path.split("/")
    except ValueError:
        logging.error(f"couldn't split repo from {url}")
        exit(1)
    repo = repo.replace(".git", "")
    return user_name, repo


def get_latest_action_url(url: str):
    logging.debug(url)
    user_name, repo = split_git_url(url)

    headers = {
        "Accept": "application/vnd.github+json",
    }
    # authenticate for rate limiting
    headers_try_to_add_authorization_from_environment(headers)

    # first fetch the git commit history
    api_url = f"https://api.github.com/repos/{user_name}/{repo}/commits"
    r = requests.get(api_url, headers=headers)
    check_status(r)
    requests_remaining = int(r.headers["X-RateLimit-Remaining"])
    if requests_remaining == 0:
        logging.error("no API requests remaining")
        exit(1)

    commits = r.json()

    # get runs
    api_url = f"https://api.github.com/repos/{user_name}/{repo}/actions/runs"
    r = requests.get(api_url, headers=headers, params={"per_page": 100})
    check_status(r)
    runs = r.json()
    page_url = get_most_recent_action_page(commits, runs["workflow_runs"])

    return page_url


def get_first_remote(repo: Repo) -> str:
    return list(repo.remotes[0].urls)[0]
