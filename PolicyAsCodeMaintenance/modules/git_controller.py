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
    単一のリポジトリをクローンする

    Args:
        repo_name (str): リポジトリ名（例: 'microsoft/vscode'）
        cloned_path (str): クローン先のディレクトリパス

    Returns:
        bool: クローンが成功した場合True、失敗した場合False
    """
    try:
        # クローン先ディレクトリを作成（存在しない場合）
        Path(cloned_path).mkdir(parents=True, exist_ok=True)

        # GitHubのURLを構築
        github_url = f"https://github.com/{repo_name}.git"

        # リポジトリ名からローカルディレクトリ名を取得
        local_repo_name = repo_name.split('/')[-1]
        local_path = os.path.join(cloned_path, local_repo_name)

        # 既にクローン済みかチェック
        if os.path.exists(local_path):
            print(f"Repository '{repo_name}' already exists at {local_path}, skipping...")
            return True

        print(f"Cloning {repo_name} to {local_path}...")

        # pygit2を使ってクローン
        repo = pygit2.clone_repository(github_url, local_path)

        print(f"Successfully cloned {repo_name}")
        return True

    except pygit2.GitError as e:
        print(f"Failed to clone {repo_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error cloning {repo_name}: {str(e)}")
        return False


