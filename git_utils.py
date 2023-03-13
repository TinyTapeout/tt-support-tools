import base64
from urllib.parse import urlparse
import logging
import requests
import os
import zipfile, io


def unique(duplist):
    unique_list = []
    # traverse for all elements
    for x in duplist:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    return unique_list


def fetch_file(url, filename):
    logging.info("trying to download {}".format(url))
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning("couldn't download {}".format(url))
        exit(1)

    with open(filename, 'wb') as fh:
        logging.info("written to {}".format(filename))
        fh.write(r.content)


def check_status(r):
    if r.status_code == 401:
        logging.error("unauthorised, check INFO.md for information about GitHub API keys")
        exit(1)


def fetch_file_from_git(git_url, path):
    # get the basics
    user_name, repo = split_git_url(git_url)

    # authenticate for rate limiting
    auth_string = os.environ['GH_USERNAME'] + ':' + os.environ['GH_TOKEN']
    encoded = base64.b64encode(auth_string.encode('ascii'))
    headers = {
        "authorization" : 'Basic ' + encoded.decode('ascii'),
        "Accept"        : "application/vnd.github+json",
        }
    encoded = base64.b64encode(auth_string.encode('ascii'))

    api_url = 'https://api.github.com/repos/%s/%s/contents/%s' % (user_name, repo, path)

    logging.debug(api_url)
    r = requests.get(api_url, headers=headers)
    check_status(r)
    requests_remaining = int(r.headers['X-RateLimit-Remaining'])
    if requests_remaining == 0:
        logging.error("no API requests remaining")
        exit(1)

    logging.debug("API requests remaining %d" % requests_remaining)

    data = r.json()
    if 'content' not in data:
        return None

    file_content = data['content']

    file_content_encoding = data.get('encoding')
    if file_content_encoding == 'base64':
        file_content = base64.b64decode(file_content)

    return file_content


# the latest artifact isn't necessarily the one related to the latest commit, as github
# could have taken longer to process an older commit than a newer one.
# so iterate through commits and return the artifact that matches
def get_most_recent_action_url(commits, artifacts):
    release_sha_to_download_url = {artifact['workflow_run']['head_sha']: artifact['archive_download_url'] for artifact in artifacts}
    for commit in commits:
        if commit['sha'] in release_sha_to_download_url:
            return release_sha_to_download_url[commit['sha']]


def get_most_recent_action_page(commits, runs):
    release_sha_to_page_url = {run['head_sha']: run['html_url'] for run in runs if run['name'] == 'gds'}
    for commit in commits:
        if commit['sha'] in release_sha_to_page_url:
            return release_sha_to_page_url[commit['sha']]


def split_git_url(url):
    res = urlparse(url)
    try:
        _, user_name, repo = res.path.split('/')
    except ValueError:
        logging.error(f"couldn't split repo from {url}")
        exit(1)
    repo = repo.replace('.git', '')
    return user_name, repo


# download the artifact for each project to get the gds & lef
def install_artifacts(url, directory):
    logging.debug(url)
    user_name, repo = split_git_url(url)

    # authenticate for rate limiting
    auth_string = os.environ['GH_USERNAME'] + ':' + os.environ['GH_TOKEN']
    encoded = base64.b64encode(auth_string.encode('ascii'))
    headers = {
        "authorization" : 'Basic ' + encoded.decode('ascii'),
        "Accept"        : "application/vnd.github+json",
        }

    # first fetch the git commit history
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/commits'
    r = requests.get(api_url, headers=headers)
    check_status(r)
    requests_remaining = int(r.headers['X-RateLimit-Remaining'])
    if requests_remaining == 0:
        logging.error("no API requests remaining")
        exit(1)

    commits = r.json()

    # now get the artifacts
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/actions/artifacts'
    r = requests.get(api_url, headers=headers, params={'per_page': 100})
    check_status(r)
    data = r.json()

    # check there are some artifacts
    if 'artifacts' not in data:
        logging.error(f"no artifact found for {url}")
        exit(1)
    else:
        # only get artifacts called GDS
        artifacts = [a for a in data['artifacts'] if a['name'] == 'GDS']
        logging.debug(f"found {len(artifacts)} artifacts")

    if len(artifacts) == 0:
        logging.error("no artifacts for this project")
        exit(1)

    download_url = get_most_recent_action_url(commits, artifacts)

    # need actions access on the token to get the artifact
    # won't work on a pull request because they won't have the token
    attempts = 1
    max_attempts = 3
    while attempts < max_attempts:
        try:
            logging.debug(f"download url {download_url} attempt {attempts}")
            r = requests.get(download_url, headers=headers)
            check_status(r)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(directory)
            break
        except zipfile.BadZipFile:
            attempts += 1
            logging.warning(f"problem with zipfile, retry {attempts}")

    if attempts == max_attempts:
        logging.error("gave up downloading zipfile")
        exit(1)


def get_latest_action_url(url, directory):
    logging.debug(url)
    user_name, repo = split_git_url(url)

    # authenticate for rate limiting
    auth_string = os.environ['GH_USERNAME'] + ':' + os.environ['GH_TOKEN']
    encoded = base64.b64encode(auth_string.encode('ascii'))
    headers = {
        "authorization" : 'Basic ' + encoded.decode('ascii'),
        "Accept"        : "application/vnd.github+json",
        }

    # first fetch the git commit history
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/commits'
    r = requests.get(api_url, headers=headers)
    check_status(r)
    requests_remaining = int(r.headers['X-RateLimit-Remaining'])
    if requests_remaining == 0:
        logging.error("no API requests remaining")
        exit(1)

    commits = r.json()

    # get runs
    api_url = f'https://api.github.com/repos/{user_name}/{repo}/actions/runs'
    r = requests.get(api_url, headers=headers, params={'per_page': 100})
    check_status(r)
    runs = r.json()
    page_url = get_most_recent_action_page(commits, runs['workflow_runs'])

    return page_url
