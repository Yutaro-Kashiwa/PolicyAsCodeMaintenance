import pygit2

from pathlib import Path
import os

def get_commit_changes(repo_path):
    repo = pygit2.Repository(repo_path)
    commit_changes = {}

    for commit in repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL):
        commit_id = str(commit.id)
        changed_files = []

        if commit.parents:
            parent = commit.parents[0]
            diff = repo.diff(parent, commit)
            for patch in diff:
                changed_files.append(patch.delta.new_file.path)
        else:
            # Initial commit (no parents)
            tree = commit.tree
            for entry in tree:
                changed_files.append(entry.name)

        commit_changes[commit_id] = changed_files

    return commit_changes


def clone_repository(repo_name, cloned_path):
    """
    Clone a single repository

    Args:
        repo_name (str): Repository name (e.g., 'microsoft/vscode')
        cloned_path (str): Path to the directory where the repository will be cloned

    Returns:
        bool: True if cloning succeeds, False if it fails
    """
    try:
        # Create clone destination directory (if it doesn't exist)
        Path(cloned_path).mkdir(parents=True, exist_ok=True)

        # Build GitHub URL
        github_url = f"https://github.com/{repo_name}.git"

        # Get local directory name from repository name
        local_repo_name = repo_name.split('/')[-1]
        local_path = os.path.join(cloned_path, local_repo_name)

        # Check if already cloned
        if os.path.exists(local_path):
            print(f"Repository '{repo_name}' already exists at {local_path}, skipping...")
            return True

        print(f"Cloning {repo_name} to {local_path}...")

        # Clone using pygit2
        repo = pygit2.clone_repository(github_url, local_path)

        print(f"Successfully cloned {repo_name}")
        return True

    except pygit2.GitError as e:
        print(f"Failed to clone {repo_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error cloning {repo_name}: {str(e)}")
        return False