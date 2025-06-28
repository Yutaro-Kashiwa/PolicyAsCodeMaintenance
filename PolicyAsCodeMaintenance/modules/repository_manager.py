"""Repository management functionality for cloning and analyzing repositories."""
import os
import logging
from typing import List, Dict, Optional
import pygit2

from .config import REPOSITORIES_THAT_SHOULD_USE_HEAD
from .file_controller import load_repository_list, list_directories
from .git_controller import get_commit_changes, clone_repository

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manages repository operations including cloning and analysis."""
    
    def __init__(self, repos_dir: str):
        """Initialize the repository manager.
        
        Args:
            repos_dir: Directory where repositories will be cloned
        """
        self.repos_dir = repos_dir
        self._ensure_repos_dir_exists()
    
    def _ensure_repos_dir_exists(self) -> None:
        """Ensure the repositories directory exists."""
        if not os.path.exists(self.repos_dir):
            os.makedirs(self.repos_dir)
            logger.info(f"Created repositories directory: {self.repos_dir}")
    
    def load_repositories(self, csv_path: str, repository_no: Optional[int] = None) -> List[Dict]:
        """Load repository list from CSV file.
        
        Args:
            csv_path: Path to CSV file containing repository information
            repository_no: Optional specific repository number to load (1-based index)
            
        Returns:
            List of repository information dictionaries
        """
        try:
            repo_list = load_repository_list(csv_path, repository_no)
            logger.info(f"Loaded {len(repo_list)} repositories from {csv_path}")
            return repo_list
        except Exception as e:
            logger.error(f"Failed to load repositories from {csv_path}: {e}")
            raise
    
    def clone_repositories(self, repo_list: List[Dict]) -> Dict[str, int]:
        """Clone all repositories from the repository list.
        
        Args:
            repo_list: List of repository information dictionaries
            
        Returns:
            Dictionary with cloning statistics (success, failed, skipped counts)
        """

        total = len(repo_list)
        for i, repo_info in enumerate(repo_list, 1):
            repo_name = repo_info['full_name']
            logger.info(f"Cloning repository {i}/{total}: {repo_name}")
            
            result = clone_repository(repo_name, self.repos_dir)

            logger.info(
                f"Cloning completed: {repo_name} successful, "
            )


    def get_repository_id(self, repo_list: List[Dict], repo_name: str) -> Optional[int]:
        """Find repository ID by matching repository name.
        
        Args:
            repo_list: List of repository information dictionaries
            repo_name: Repository name to match (can be partial name)
            
        Returns:
            Repository ID if found, None otherwise
        """
        for repo_info in repo_list:
            if repo_info['full_name'].endswith(repo_name):
                return repo_info['id']
        
        logger.warning(f"Could not find repository ID for: {repo_name}")
        return None
    
    def get_repository_info(self, repo_list: List[Dict], repo_name: str) -> Optional[Dict]:
        """Find repository information by matching repository name.
        
        Args:
            repo_list: List of repository information dictionaries
            repo_name: Repository name to match (can be partial name)
            
        Returns:
            Repository info dict with 'id' and 'full_name' if found, None otherwise
        """
        for repo_info in repo_list:
            if repo_info['full_name'].endswith(repo_name):
                return {'id': repo_info['id'], 'full_name': repo_info['full_name']}

        return None
    
    def get_cloned_repositories(self) -> List[str]:
        """Get list of cloned repository directories.
        
        Returns:
            List of repository directory names
        """
        return list_directories(self.repos_dir)
    
    def get_repository_changes(self, repo_name: str) -> Dict[str, List[str]]:
        """Get commit changes for a repository.
        
        Args:
            repo_name: Name of the repository directory
            
        Returns:
            Dictionary mapping commit IDs to lists of changed files
        """
        repo_path = os.path.join(self.repos_dir, repo_name)
        try:
            changes = get_commit_changes(repo_path)
            logger.info(f"Retrieved {len(changes)} commits for {repo_name}")
            return changes
        except Exception as e:
            logger.error(f"Failed to get changes for {repo_name}: {e}")
            raise RuntimeError("Exception: Failed to get changes for {repo_name}: {e}")

    def checkout(self, repo_list: List[Dict]) -> Dict[str, int]:
        """Checkout specific commits in cloned repositories.
        
        Args:
            repo_list: List of repository information dictionaries containing 'full_name' and 'sha'
            
        Returns:
            Dictionary with checkout statistics (success, failed, skipped counts)
        """
        if not repo_list:
            logger.warning("No repositories to checkout")
            raise RuntimeError("No repositories to checkout")
        

        total = len(repo_list)
        
        for i, repo_info in enumerate(repo_list, 1):
            repo_name = repo_info['full_name']
            sha = repo_info.get('sha')
            
            if not sha:
                logger.warning(f"No SHA provided for {repo_name}, skipping checkout")
                raise RuntimeError(f"No SHA provided for {repo_name}, skipping checkout")
            
            # Get local directory name from repository name
            # local_repo_name = repo_name.split('/')[-1]
            repo_path = os.path.join(self.repos_dir, repo_name)
            
            # Check if repository exists
            if not os.path.exists(repo_path):
                logger.error(f"Repository {repo_name} not found at {repo_path}, skipping checkout")
                raise RuntimeError(f"Repository {repo_name} not found at {repo_path}")

            
            logger.info(f"Checking out {repo_name} at commit {sha} ({i}/{total})")
            
            try:
                repo = pygit2.Repository(repo_path)
                
                # Get the commit object from SHA
                commit = repo.get(sha)
                if not commit:
                    logger.error(f"Commit {sha} not found in {repo_name}")
                    commit = repo.revparse_single('HEAD')

                # The specified sha in the dataset no longer exist so we will use HEAD
                if repo_name in REPOSITORIES_THAT_SHOULD_USE_HEAD:
                    logger.info(f"Skipping checkout for {repo_name}")
                    print(f"Skipping checkout for {repo_name}")
                    commit = repo.revparse_single('HEAD')

                # Checkout the commit
                repo.checkout_tree(commit)
                
                # Update HEAD to point to the commit
                repo.set_head(commit.id)
                
                logger.info(f"Successfully checked out {repo_name} at {sha}")


            except pygit2.GitError as e:
                logger.error(f"Git error during checkout of {repo_name}: {e}")
                raise RuntimeError(f"Git error during checkout of {repo_name}: {e}")
            except Exception as e:
                logger.error(f"Failed to checkout {repo_name} at {sha}: {e}")
                raise RuntimeError(f"Anonymous Error: Failed to checkout {repo_name} at {sha}: {e}")
        
            logger.info(
                f"Checkout completed: {repo_name} successful, "
            )