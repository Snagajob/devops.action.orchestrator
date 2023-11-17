from glob import glob
from os import getenv
from pathlib import Path
from typing import Dict, List
import requests

import boto3

ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
PARALLELIZE = getenv("PARALLELIZE", None)
DEBUG = getenv("DEBUG", None)
GEMFURY_TOKEN = getenv("GEMFURY_TOKEN", None)
RUN_ENV = getenv("RUN_ENV", None)
ARGO_SKIP_ENVS = getenv("ARGO_SKIP_ENVS", None)
ARGO_NOTIFICATION_WEBHOOK = getenv("ARGO_NOTIFICATION_WEBHOOK", None)
SLACK_WEBHOOK = getenv("SLACK_WEBHOOK", None)
GITHUB_REPOSITORY = getenv("GITHUB_REPOSITORY", None)
GITHUB_SHA = getenv("GITHUB_SHA", None)
RELEASE_CHANNEL = getenv("RELEASE_CHANNEL")

if RELEASE_CHANNEL == "":
    RELEASE_CHANNEL = "master"


def start_build(project_path_list: List[str]):
    payload = {
        "projectName": "orchestrator",
        "secondarySourcesOverride": [
            {
                "type": "GITHUB",
                "location": f"https://github.com/{getenv('GITHUB_REPOSITORY')}",
                "sourceIdentifier": "git_project",
            }
        ],
        "secondarySourcesVersionOverride": [
            {"sourceIdentifier": "git_project", "sourceVersion": getenv("GITHUB_SHA")}
        ],
        "environmentVariablesOverride": [
            {"name": "GIT_REF", "value": getenv("GITHUB_REF"), "type": "PLAINTEXT"},
            {
                "name": "RUN_NUMBER",
                "value": getenv("GITHUB_RUN_NUMBER"),
                "type": "PLAINTEXT",
            },
            {"name": "GIT_ACTOR", "value": getenv("GITHUB_ACTOR"), "type": "PLAINTEXT"},
            {
                "name": "GIT_REPOSITORY",
                "value": getenv("GITHUB_REPOSITORY"),
                "type": "PLAINTEXT",
            },
            {
                "name": "GIT_COMMIT_SHA",
                "value": GITHUB_SHA,
                "type": "PLAINTEXT",
            },
            {"name": "RUN_ENV", "value": RUN_ENV, "type": "PLAINTEXT"},
            {
                "name": "SLACK_WEBHOOK",
                "value": SLACK_WEBHOOK,
                "type": "PLAINTEXT",
            },
            {
                "name": "PROJECT_PATH_LIST",
                "value": ",".join(project_path_list),
                "type": "PLAINTEXT",
            },
            {   "name": "RELEASE_CHANNEL", 
                "value": RELEASE_CHANNEL, 
                "type": "PLAINTEXT"
            },
        ],
    }

    if DEBUG:
        payload["debugSessionEnabled"] = True
        payload["environmentVariablesOverride"].append(
            {"name": "DEBUG", "value": DEBUG, "type": "PLAINTEXT"}
        )

    if GEMFURY_TOKEN:
        payload["environmentVariablesOverride"].append(
            {"name": "GEMFURY_TOKEN", "value": GEMFURY_TOKEN, "type": "PLAINTEXT"}
        )

    if ARGO_SKIP_ENVS:
        payload["environmentVariablesOverride"].append(
            {"name": "ARGO_SKIP_ENVS", "value": ARGO_SKIP_ENVS, "type": "PLAINTEXT"}
        )
        print(f"Adding ARGO_SKIP_ENVS: {ARGO_SKIP_ENVS}")

    if ARGO_NOTIFICATION_WEBHOOK:
        payload["environmentVariablesOverride"].append(
            {
                "name": "ARGO_NOTIFICATION_WEBHOOK",
                "value": ARGO_NOTIFICATION_WEBHOOK,
                "type": "PLAINTEXT",
            }
        )
        print(f"Adding ARGO_NOTIFICATION_WEBHOOK: {ARGO_NOTIFICATION_WEBHOOK}")

    response: Dict = boto3.client("codebuild").start_build(**payload)

    build_id = response["build"]["id"]

    if len(project_path_list) == 1:
        print(f"Project: {project_path}\n")
    else:
        print("Deploying full project as one build")

    print(
        f"Build: https://console.aws.amazon.com/codesuite/codebuild/{ACCOUNT_ID}"
        f"/projects/orchestrator/build/{build_id}/?region=us-east-1\n"
    )


GIT_REPO_PATH = getenv("GITHUB_REPOSITORY").split("/")[1]
PROJECT_SEARCH_PATH = f"/home/runner/work/{GIT_REPO_PATH}/**/config.json"

print(f"Looking in {PROJECT_SEARCH_PATH} for config.json files")

print(f"Release channel: {RELEASE_CHANNEL}")

project_list: List[Path] = [
    Path(entry) for entry in glob(PROJECT_SEARCH_PATH, recursive=True)
]

standardized_path_list: List[str] = [
    f"{GIT_REPO_PATH}/{project_path.parent.name}"
    f"{str(project_path).rsplit(project_path.parent.name)[1]}"
    for project_path in project_list
]

if RUN_ENV not in ["dev", "qa", "uat", "prod"]:
    print("\n[X] Skipping build since RUN_ENV is not valid.")
    exit(0)

if PARALLELIZE:
    print("\n[*] Executing parallized project build!")
    for project_path in standardized_path_list:
        print(f"Passing in project path: {project_path}")
        start_build([project_path])
else:
    print("\n[*] Executing standard (non-parallelized) project build!")
    start_build(standardized_path_list)

slack_commit_url = (
    f"<https://github.com/{GITHUB_REPOSITORY}/commit/{GITHUB_SHA}|{GITHUB_SHA[:7]}>"
)

requests.post(
    SLACK_WEBHOOK,
    json={
        "text": f"New build detected for repository: *{GITHUB_REPOSITORY}* :: Commit *{slack_commit_url}* :: Run Env *{RUN_ENV}*"
    },
)
