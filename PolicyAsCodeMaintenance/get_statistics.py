# Usage example: Specify the repository path
from modules.file_controller import load_repository_list, list_directories
from modules.git_controller import get_commit_changes, clone_repository
import os
import pandas as pd


# Directory and file path constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
REPOS_DIR = os.path.join(ROOT_DIR, 'repos')
INPUTS_DIR = os.path.join(ROOT_DIR, 'inputs')
# repos-full-test.csv contains only 1 repository for testing purposes
# Comment this line and uncomment the line below to use the full dataset
REPOS_CSV_PATH = os.path.join(INPUTS_DIR, 'repos-full.csv')
#REPOS_CSV_PATH = os.path.join(INPUTS_DIR, 'repos-full.csv')
FILES_CSV_PATH = os.path.join(INPUTS_DIR, 'pac_files.csv')


def is_pac(repo_id, file):
    df = pd.read_csv(FILES_CSV_PATH)
    match = df[(df['repo_id'] == repo_id) & (df['path'] == file)]
    return not match.empty


def count_commits_changing_pac(repo_id, changes):
    i = 0
    # Display results
    for commit_id, files in changes.items():
        print(f"Commit {commit_id}:")
        for file in files:
            if is_pac(repo_id, file):
                print(f"Commit {commit_id}: {file}")
                i+=1
            else:
                pass

    return i


def clone_repositories_from_list(repo_list):
    """
    Clone all repositories from repository list

    Args:
        repo_list (list): List of repository information dictionaries

    Returns:
        dict: Statistical information of cloning results
    """
    if not repo_list:
        print("No repositories to clone")
        return {'success': 0, 'failed': 0, 'skipped': 0}
        raise

    success_count = 0
    failed_count = 0

    for repo_info in repo_list:
        repo_name = repo_info['full_name']
        if clone_repository(repo_name, REPOS_DIR):
            # TODO: Check out the repositories
            success_count += 1
        else:
            failed_count += 1
    print(f"\nCloning completed: {success_count} successful, {failed_count} failed")
    return {'success': success_count, 'failed': failed_count}


def analyze(repo_list, cloned_path):
    repos = list_directories(cloned_path)
    print("Directory list:")
    for repo_name in repos:
        repo_path = f"{cloned_path}/{repo_name}"

        # set id to the id in the dictionary of repo_list where repo_name is a suffix of full_name
        repo_id = None
        for repo_info in repo_list:
            if repo_info['full_name'].endswith(repo_name):
                repo_id = repo_info['id']
                break
        if repo_id is None:
            raise Exception(f"Could not find repo id for repo_name: {repo_name}")

        changes = get_commit_changes(repo_path)
        num_pac_changes = count_commits_changing_pac(repo_id, changes)
        print(repo_name, num_pac_changes, len(changes), num_pac_changes/len(changes))



# To debug (analyze one repository), use the argument "--repository_no=10"
if __name__ == "__main__":
    import argparse
    # Receive cluster number (if none, run all.)
    parser = argparse.ArgumentParser(description='to collect maintenance activities from repositories that have policy as code')
    parser.add_argument('--repository_no', type=int, help='') # starts from 1
    args = parser.parse_args()
    repo_list = load_repository_list(REPOS_CSV_PATH, args.repository_no)
    print(f"Repository list: {repo_list}")
    clone_repositories_from_list(repo_list)
    analyze(repo_list, REPOS_DIR)