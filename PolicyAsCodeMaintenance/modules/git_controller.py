import pygit2

from pathlib import Path
import os

def get_commit_changes(repo_path):
    repo = pygit2.Repository(repo_path)
    commit_changes = {}

    for commit in repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL):
        commit_id = str(commit.id)
        commit_info = {
            'files': [],
            'author': commit.author.name,
            'author_email': commit.author.email,
            'message': commit.message,
            'date': commit.commit_time,
            'changes': []  # List of file changes with additions/deletions
        }

        if commit.parents:
            parent = commit.parents[0]
            diff = repo.diff(parent.tree, commit.tree)
            
            # Enable line-by-line diff statistics
            diff.find_similar()
            
            for patch in diff:
                file_path = patch.delta.new_file.path
                commit_info['files'].append(file_path)
                
                # Get line statistics for this file
                additions = patch.line_stats[1]  # Number of additions
                deletions = patch.line_stats[2]  # Number of deletions
                
                commit_info['changes'].append({
                    'file': file_path,
                    'additions': additions,
                    'deletions': deletions,
                    'total_changes': additions + deletions
                })
        else:
            # Initial commit (no parents)
            tree = commit.tree
            # For initial commit, we'll need to walk the tree recursively
            def walk_tree(tree_obj, prefix=''):
                for entry in tree_obj:
                    if entry.type == 'tree':
                        subtree = repo[entry.id]
                        walk_tree(subtree, prefix + entry.name + '/')
                    else:
                        full_path = prefix + entry.name
                        commit_info['files'].append(full_path)
                        # For initial commit, all lines are additions
                        try:
                            blob = repo[entry.id]
                            if hasattr(blob, 'is_binary') and blob.is_binary:
                                lines = 0
                            elif hasattr(blob, 'data'):
                                lines = blob.data.decode('utf-8', errors='ignore').count('\n')
                            else:
                                lines = 0
                        except (UnicodeDecodeError, AttributeError):
                            lines = 0
                        
                        commit_info['changes'].append({
                            'file': full_path,
                            'additions': lines,
                            'deletions': 0,
                            'total_changes': lines
                        })
            
            walk_tree(tree)

        commit_changes[commit_id] = commit_info

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
            try:
                print(f"Repository '{repo_name}' already exists at {local_path}, updating...")
                # Open existing repository
                repo = pygit2.Repository(local_path)
                # Get remote origin
                remote = repo.remotes["origin"]
                # Fetch latest changes
                remote.fetch()
                
                # Get the default branch (usually main or master)
                # Try to get the remote's default branch first
                try:
                    # Try main branch first
                    main_ref = remote.get_refspec(0).dst
                    if "main" in main_ref:
                        default_branch_ref = repo.references["refs/remotes/origin/main"].target
                    else:
                        default_branch_ref = repo.references["refs/remotes/origin/master"].target
                except (KeyError, IndexError):
                    # Fallback to local branches
                    try:
                        default_branch_ref = repo.references["refs/heads/main"].target
                    except KeyError:
                        try:
                            default_branch_ref = repo.references["refs/heads/master"].target
                        except KeyError:
                            # Use current HEAD as last resort
                            default_branch_ref = repo.head.target
                
                # Reset to the latest commit (hard reset)
                repo.reset(default_branch_ref, pygit2.GIT_RESET_HARD)
                
                print(f"Successfully updated {repo_name}")
                return True
                
            except Exception as e:
                print(f"Failed to update {repo_name}: {str(e)}, will try to re-clone...")
                # If update fails, fall through to re-clone
                import shutil
                shutil.rmtree(local_path)

        print(f"Cloning {repo_name} to {local_path}...")

        # Clone using pygit2
        pygit2.clone_repository(github_url, local_path)

        print(f"Successfully cloned {repo_name}")
        return True

    except pygit2.GitError as e:
        print(f"Failed to clone {repo_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error cloning {repo_name}: {str(e)}")
        return False