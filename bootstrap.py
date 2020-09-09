from os import getenv
from typing import Dict

import boto3

response: Dict = boto3.client('codebuild').start_build(
    projectName='orchestrator',
    secondarySourcesOverride=[
        {
            "type": "GITHUB",
            "location": f"https://github.com/{getenv('GITHUB_REPOSITORY')}",
            "sourceIdentifier": "git_project"
        }
    ],
    secondarySourcesVersionOverride=[
        {"sourceIdentifier": "git_project", "sourceVersion": getenv("GITHUB_SHA")}
    ],
    environmentVariablesOverride=[
        {"name": "GIT_REF", "value": getenv("GITHUB_REF"), "type": "PLAINTEXT"},
        {"name": "RUN_NUMBER", "value": getenv("GITHUB_RUN_NUMBER"), "type": "PLAINTEXT"},
        {"name": "GIT_ACTOR", "value": getenv("GITHUB_ACTOR"), "type": "PLAINTEXT"},
        {"name": "GIT_REPOSITORY", "value": getenv("GITHUB_REPOSITORY"), "type": "PLAINTEXT"},
        {"name": "GIT_COMMIT_SHA", "value": getenv("GITHUB_SHA"), "type": "PLAINTEXT"},
        {"name": "RUN_ENV", "value": getenv("RUN_ENV"), "type": "PLAINTEXT"}
    ]
)

build_id = response['build']['id']

account_id = boto3.client('sts').get_caller_identity()['Account']

print(f"::set-env name=CODEBUILD_LINK::https://console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/orchestrator/build/{build_id}/?region=us-east-1")
