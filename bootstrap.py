from glob import glob
from os import getenv
from pathlib import Path
from typing import Dict, List

import boto3

ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
PARELLELIZE = getenv("PARALLELIZE", None)
DEBUG = getenv("DEBUG", None)


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
                "value": getenv("GITHUB_SHA"),
                "type": "PLAINTEXT",
            },
            {"name": "RUN_ENV", "value": getenv("RUN_ENV"), "type": "PLAINTEXT"},
            {
                "name": "SLACK_WEBHOOK",
                "value": getenv("SLACK_WEBHOOK"),
                "type": "PLAINTEXT",
            },
            {
                "name": "PROJECT_PATH_LIST",
                "value": ",".join(project_path_list),
                "type": "PLAINTEXT",
            },
        ],
    }

    if DEBUG:
        payload["debugSessionEnabled"] = True
        payload["environmentVariablesOverride"].append(
            {"name": "DEBUG", "value": DEBUG, "type": "PLAINTEXT"}
        )

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

project_list: List[Path] = [
    Path(entry) for entry in glob(PROJECT_SEARCH_PATH, recursive=True)
]

standardized_path_list: List[str] = [
    f"{GIT_REPO_PATH}/{project_path.parent.name}"
    f"{str(project_path).rsplit(project_path.parent.name)[1]}"
    for project_path in project_list
]

if PARELLELIZE:
    print("\n[*] Executing parallized project build!")
    for project_path in standardized_path_list:
        print(f"Passing in project path: {project_path}")
        start_build([project_path])
else:
    print("\n[*] Executing standard (non-parallelized) project build!")
    start_build(standardized_path_list)
