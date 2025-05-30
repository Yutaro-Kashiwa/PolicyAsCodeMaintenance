# Usage example: Specify the repository path
from modules.file_controller import load_repository_list, list_directories
from modules.git_controller import get_commit_changes, clone_repository
import os


def is_pac(file):
    #TODO: Based on ROpdebee's code we need to identify PaC changes
    # https://github.com/ROpdebee/PaC-dataset/blob/main/scripts/filter_files.py
    pass


def count_commits_changing_pac(changes):
    i = 0
    # Display results
    for commit_id, files in changes.items():
        print(f"Commit {commit_id}:")
        for file in files:
            if is_pac(file):
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
        repo_name = repo_info['repo_name']
        # sha = repo_info['sha']
        if clone_repository(repo_name, cloned_path):
            # TODO: Check out the repositories
            success_count += 1
        else:
            failed_count += 1
        if (debug_mode):
            break

    print(f"\nCloning completed: {success_count} successful, {failed_count} failed")
    return {'success': success_count, 'failed': failed_count}





def analyze(cloned_path):
    # Usage example (change to any path you want)
    repos = list_directories(cloned_path)
    print("Directory list:")
    for repo_name in repos:
        repo_path = f"{cloned_path}/{repo_name}"

        changes = get_commit_changes(repo_path)
        num_pac_changes = count_commits_changing_pac(changes)
        print(repo_name, num_pac_changes, len(changes), num_pac_changes/len(changes))
        if (debug_mode):
            break
debug_mode = False
if __name__ == "__main__":
    cloned_path = '../repos/'
    repo_list = load_repository_list('../inputs/repos.csv')
    clone_repositories_from_list(repo_list)
    analyze(cloned_path)