import re
import sys
import base64
import shlex
import json
import os
import requests

from github import Github, GithubException


START_COMMENT = "<!--START_SECTION:stack-->"
END_COMMENT = "<!--END_SECTION:stack-->"

REPOSITORY = os.getenv("INPUT_REPOSITORY")
GH_TOKEN = os.getenv("INPUT_GH_TOKEN")
GH_API_URL = os.getenv("INPUT_GH_API_URL")
COMMIT_MESSAGE = os.getenv("INPUT_COMMIT_MESSAGE")

BADGES = os.getenv("INPUT_BADGES")
if BADGES is None or BADGES == "None":
    raise Exception("Failed to get badges!")

BADGE_SIZE = os.getenv("INPUT_BADGE_SIZE", '110')

LIST_REGEX = f"{START_COMMENT}[\\s\\S]+{END_COMMENT}"


def readReadme(file: str) -> str:
    with open(file, mode="r", encoding="utf-8") as file:
        return file.read()


def saveJson(filename: str="badges.json", content: str="") -> None:
    with open(filename, mode="w", encoding="utf-8") as file:
        return file.write(json.dumps(content))


def processTable(table: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for index, line in enumerate(table[1:-1].split('\n')):
        data: dict[str, str] = {}
        if index == 0:
            header = [t.strip() for t in line.split('|')[1:-1]]
        if index > 1:
            values = [t.strip() for t in line.split('|')[1:-1]]
            for col, value in zip(header, values):
                data[col] = value
            if data:
                result.append(data)
    return result

def getAllBadges(file_content: str, save=False) -> list[dict[str, str]]:
    lines: list[str] = file_content.split("\n")
    wanted_lines: list[dict[str, str]] = []
    header: str = ""
    table: list[str] = ""
    tables: list[dict[str, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("###"):
            if i != 0:
                tables.append({header: "\n".join(table)})
                table = []
            header = "".join([char for char in line.strip("### ") if ord(char) in range(1, 125)]).strip()
        elif header != "":
            table.append(line)
    for data in tables:
        for key, value in data.items():
            processed_table: dict[str, str] = processTable(value)
            if processed_table != {}:
                wanted_lines.extend(processed_table)
    if save:
        saveJson(content=wanted_lines)
    return wanted_lines


def getWantedBadgesMarkdown(all_badges: list[dict[str, str]], badges_list: list[str]) -> list[str]:
    markdowns: list[str] = []
    for badge in badges_list:
        for item in all_badges:
            if badge.lower() == item["Name"].lower():
                markdowns.append(item["Badge"])
    return markdowns


class GithubRepo:
    def __init__(self):
        self.COMMIT_MESSAGE=COMMIT_MESSAGE

        # Automatic GitHub API detection.
        g = Github(base_url=GH_API_URL, login_or_token=GH_TOKEN)

        try:
            self.repo = g.get_repo(REPOSITORY)
        except GithubException:
            print(
                "Authentication Error. Try saving a GitHub Token in your Repo Secrets or Use the GitHub Actions Token, which is automatically used by the action."
            )
            sys.exit(1)
        try:
            self.contents_repo = self.repo.get_readme()
        except Exception:
            print(
                "The readme cannot be obtained!"
            )
            sys.exit(1)

    def save_readme(self, new_readme):
        self.repo.update_file(
            path=self.contents_repo.path, message=self.COMMIT_MESSAGE, content=new_readme, sha=self.contents_repo.sha
        )
    
    def get_readme(self):
        return str(base64.b64decode(self.contents_repo.content), "utf-8")


def parseArguments(env_args: str) -> list[str]:
    return shlex.split(env_args)


def generate_new_readme(md_badges, readme):
    """Generate a new Readme.md"""
    if not md_badges:
        return readme
    badges_in_readme = f"{START_COMMENT}\n{md_badges}\n{END_COMMENT}"

    return re.sub(LIST_REGEX, badges_in_readme, readme)


if __name__ == "__main__":
    # print("\n".join(getWantedBadgesMarkdown(getAllBadges(requests.get("https://raw.githubusercontent.com/kamuridesu/markdown-badges/master/README.md").text), parseArguments("Python Java JavaScript 'Shell Script' 'GitHub Actions' 'GitLab CI' Django Flask Node.js Spring AWS Azure 'Google Cloud' 'IntelliJ IDEA' Neovim 'Sublime Text' 'Visual Studio Code' Arch Windows Ansible Docker Jira Kubernetes Terraform Vagrant Jenkins Git Gitea GitHub GitLab"))))
    git = GithubRepo()
    readme = git.get_readme()
    all_badges = getAllBadges(requests.get("https://raw.githubusercontent.com/kamuridesu/markdown-badges/master/README.md").text)
    wanted_badges = getWantedBadgesMarkdown(all_badges, parseArguments(BADGES))
    new_readme = generate_new_readme("\n".join(wanted_badges), readme)
    if new_readme != readme:
        git.save_readme(new_readme)
