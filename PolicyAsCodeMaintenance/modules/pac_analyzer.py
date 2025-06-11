"""Policy as Code (PAC) file analysis functionality."""
import pandas as pd
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class PacAnalyzer:
    """Analyzes Policy as Code files and their changes in repositories."""
    
    def __init__(self, pac_files_csv_path: str):
        """Initialize the PAC analyzer with a CSV file containing PAC file definitions.
        
        Args:
            pac_files_csv_path: Path to CSV file containing repo_id and file paths
        """
        self.pac_files_csv_path = pac_files_csv_path
        self._pac_files_df = None
        self._load_pac_files()
    
    def _load_pac_files(self) -> None:
        """Load PAC files from CSV into a DataFrame."""
        try:
            self._pac_files_df = pd.read_csv(self.pac_files_csv_path)
            logger.info(f"Loaded {len(self._pac_files_df)} PAC file entries")
        except Exception as e:
            logger.error(f"Failed to load PAC files from {self.pac_files_csv_path}: {e}")
            raise
    
    def is_pac_file(self, repo_id: int, file_path: str) -> bool:
        """Check if a file is a Policy as Code file for a given repository.
        
        Args:
            repo_id: Repository ID
            file_path: Path to the file within the repository
            
        Returns:
            True if the file is a PAC file, False otherwise
        """
        if self._pac_files_df is None:
            return False
            
        match = self._pac_files_df[
            (self._pac_files_df['repo_id'] == repo_id) & 
            (self._pac_files_df['path'] == file_path)
        ]
        return not match.empty
    
    def parse_commits(self, commit_changes: Dict[str, Dict]) -> List['Commit']:
        """Parse raw commit data into Commit objects.
        
        Args:
            commit_changes: Dictionary mapping commit IDs to commit info dictionaries
            
        Returns:
            List of Commit objects
        """
        commits = []
        for commit_id, commit_info in commit_changes.items():
            if isinstance(commit_info, dict):
                commit = Commit()
                commit.commit_id = commit_id
                commit.author = commit_info.get('author', '')
                commit.author_email = commit_info.get('author_email', '')
                commit.message = commit_info.get('message', '')
                commit.date = commit_info.get('date', None)
                commit.files = commit_info.get('files', [])
                commit.changes = commit_info.get('changes', [])
                commits.append(commit)
        
        return commits
    
    def count_pac_changes_from_commits(self, repo_id: int, commits: List['Commit']) -> Tuple[int, Dict[str, List[Dict]]]:
        """Count commits that change PAC files and identify which files were changed.
        
        Args:
            repo_id: Repository ID
            commits: List of Commit objects
            
        Returns:
            Tuple of (count of PAC changes, dictionary of commits with PAC file changes including line stats)
        """
        pac_changes_count = 0
        pac_commits = {}
        
        for commit in commits:
            pac_files_in_commit = []
            
            # Create a map of file to change stats
            change_map = {change['file']: change for change in commit.changes} if commit.changes else {}
            
            for file_path in commit.files:
                if self.is_pac_file(repo_id, file_path):
                    # Include line statistics if available
                    file_info = {
                        'file': file_path,
                        'additions': 0,
                        'deletions': 0,
                        'total_changes': 0
                    }
                    if file_path in change_map:
                        file_info.update(change_map[file_path])
                    pac_files_in_commit.append(file_info)
            
            # Identify other (non-PAC) changes
            other_changes = []
            for file_path in commit.files:
                if not self.is_pac_file(repo_id, file_path):
                    file_info = {
                        'file': file_path,
                        'additions': 0,
                        'deletions': 0,
                        'total_changes': 0
                    }
                    if file_path in change_map:
                        file_info.update(change_map[file_path])
                    other_changes.append(file_info)
            
            # Store changes in the commit object
            commit.pac_changes = pac_files_in_commit
            commit.other_changes = other_changes
            
            if pac_files_in_commit:
                pac_changes_count += len(pac_files_in_commit)
                pac_commits[commit.commit_id] = pac_files_in_commit
                logger.debug(f"Commit {commit.commit_id}: {len(pac_files_in_commit)} PAC file(s) changed")
        
        return pac_changes_count, pac_commits
    
    def analyze_repository(self, repo_id: int, repo_name: str, commit_changes: Dict[str, Dict], project_name: str = None) -> Dict:
        """Analyze PAC changes in a repository using Commit objects.
        
        Args:
            repo_id: Repository ID
            repo_name: Repository name (e.g., 'aws-cdk')
            commit_changes: Dictionary mapping commit IDs to commit info dictionaries
            project_name: Full project name including owner (e.g., 'aws/aws-cdk')
            
        Returns:
            Dictionary with analysis results
        """
        total_commits = len(commit_changes)
        
        # Parse raw commit data into Commit objects
        commits = self.parse_commits(commit_changes)
        
        # Count PAC changes using Commit objects
        pac_changes_count, pac_commits = self.count_pac_changes_from_commits(repo_id, commits)
        
        # Calculate statistics
        total_added_lines = sum(sum(change.get('additions', 0) for change in commit.changes) for commit in commits)
        total_deleted_lines = sum(sum(change.get('deletions', 0) for change in commit.changes) for commit in commits)
        
        # PAC-specific statistics
        pac_added_lines = 0
        pac_deleted_lines = 0
        for commit_id, pac_files in pac_commits.items():
            for pac_file in pac_files:
                pac_added_lines += pac_file.get('additions', 0)
                pac_deleted_lines += pac_file.get('deletions', 0)
        
        results = {
            'repository_id': repo_id,
            'repository_name': repo_name,
            'project_name': project_name,  # Use project_name if provided, else fall back to repo_name
            'total_commits': total_commits,
            'pac_changes_count': pac_changes_count,
            'pac_commits_count': len(pac_commits),
            'pac_change_ratio': pac_changes_count / total_commits if total_commits > 0 else 0,
            'commits': commits,  # Return Commit objects instead of raw changes
            'statistics': {
                'total_added_lines': total_added_lines,
                'total_deleted_lines': total_deleted_lines,
                'total_modified_lines': total_added_lines + total_deleted_lines,
                'pac_added_lines': pac_added_lines,
                'pac_deleted_lines': pac_deleted_lines,
                'pac_modified_lines': pac_added_lines + pac_deleted_lines
            }
        }
        
        display_name = project_name if project_name else repo_name
        logger.info(
            f"{display_name}: {pac_changes_count} PAC changes in {len(pac_commits)} commits "
            f"out of {total_commits} total commits ({results['pac_change_ratio']:.2%})"
        )
        
        return results


class Commit:
    def __init__(self):
        self.commit_id = None
        self.author = None
        self.author_email = None
        self.message = None
        self.date = None
        self.files = []
        self.changes = []  # List of file changes with additions/deletions
        self.pac_changes = []
        self.other_changes = []
    
    def has_pac_changes(self) -> bool:
        """Check if this commit contains PAC changes."""
        return len(self.pac_changes) > 0
    
    def get_pac_added_lines(self) -> int:
        """Get total number of lines added in PAC files."""
        return sum(change.get('additions', 0) for change in self.pac_changes)
    
    def get_pac_deleted_lines(self) -> int:
        """Get total number of lines deleted in PAC files."""
        return sum(change.get('deletions', 0) for change in self.pac_changes)
    
    def get_total_added_lines(self) -> int:
        """Get total number of lines added in all files."""
        return sum(change.get('additions', 0) for change in self.changes)
    
    def get_total_deleted_lines(self) -> int:
        """Get total number of lines deleted in all files."""
        return sum(change.get('deletions', 0) for change in self.changes)
    
    def __str__(self):
        return f"Commit({self.commit_id[:8]}, author={self.author}, files={len(self.files)}, pac_changes={len(self.pac_changes)})"
