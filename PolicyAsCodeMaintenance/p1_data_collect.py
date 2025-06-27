"""Main script for analyzing Policy as Code maintenance activities in repositories."""
import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
import time

from pathlib import Path
from typing import List, Dict, Optional

from modules.config import (
    REPOS_DIR,
    PAC_FILE_NAMES_CSV_PATH,
    DEFAULT_REPOS_CSV,
    REPOS_TEST_CSV_PATH,
    USE_TEST_MODE
)
from modules.pac_analyzer import PacAnalyzer
from modules.repository_manager import RepositoryManager


@dataclass
class AnalysisConfig:
    """Configuration for repository analysis."""
    repository_no: Optional[int] = None
    use_test_mode: bool = False
    skip_clone: bool = False
    verbose: bool = False
    output_path: str = 'outputs/results.json'
    
    @property
    def csv_path(self) -> str:
        """Get the appropriate CSV file path based on configuration."""
        return REPOS_TEST_CSV_PATH if (self.use_test_mode or USE_TEST_MODE) else DEFAULT_REPOS_CSV





class DataCollector:
    """Main class for collecting and analyzing repository data."""
    
    def __init__(self, config: AnalysisConfig):
        """Initialize the data collector with configuration.
        
        Args:
            config: Analysis configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.repo_manager = RepositoryManager(REPOS_DIR)
        self.pac_analyzer = PacAnalyzer(PAC_FILE_NAMES_CSV_PATH)
    
    def setup_logging(self) -> None:
        """Configure logging for the application."""
        level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def load_repositories(self) -> List[Dict]:
        """Load repository list from CSV file.
        
        Returns:
            List of repository information dictionaries
            
        Raises:
            RuntimeError: If no repositories are loaded
        """
        self.logger.info(f"Using repository list from: {self.config.csv_path}")
        
        repo_list = self.repo_manager.load_repositories(
            self.config.csv_path, 
            self.config.repository_no
        )
        
        if not repo_list:
            raise RuntimeError("No repositories loaded")
        
        self.logger.info(f"Loaded {len(repo_list)} repositories")
        return repo_list
    
    def clone_and_checkout_repositories(self, repo_list: List[Dict]) -> None:
        """Clone and checkout repositories if needed.
        
        Args:
            repo_list: List of repository information
            
        Raises:
            RuntimeError: If cloning or checkout fails completely
        """
        if self.config.skip_clone:
            self.logger.info("Skipping repository cloning as requested")
            return
        
        # Clone repositories
        self.logger.info("Starting repository cloning...")
        self.repo_manager.clone_repositories(repo_list)
        

        
        # Checkout specific commits
        self.logger.info("Starting repository checkout...")
        self.repo_manager.checkout(repo_list)
        
        self.logger.info(
            f"Repository preparation complete. "
        )
    
    def analyze_repositories(self, repo_list: List[Dict]) -> List[Dict]:
        """Analyze PAC changes in all cloned repositories.
        
        Args:
            repo_list: List of repository information
            
        Returns:
            List of analysis results for each repository
        """
        results = []
        cloned_repos = self.repo_manager.get_cloned_repositories()
        
        if not cloned_repos:
            self.logger.warning("No cloned repositories found to analyze")
            raise RuntimeError("No cloned repositories found to analyze")
        
        self.logger.info(f"Analyzing {len(cloned_repos)} repositories...")
        
        for repo_info in repo_list:
            # print(repo)
            # Find repository info

            
            repo_id = repo_info['id']
            full_name = repo_info['full_name']
            
            self.logger.info(f"Analyzing repository: {full_name}")
            
            # Get commit changes
            changes = self.repo_manager.get_repository_changes(full_name)
            if not changes:
                self.logger.warning(f"No commits found for {full_name}")
                raise RuntimeError(f"No commits found for {full_name}")
            
            # Analyze PAC changes
            try:
                analysis_result = self.pac_analyzer.analyze_repository(repo_id, full_name, changes, full_name)
                results.append(analysis_result)
                self.logger.debug(f"Successfully analyzed {full_name}")
            except Exception as e:
                self.logger.error(f"Failed to analyze {full_name}: {e}")
                raise RuntimeError(f"Failed to analyze {full_name}: {e}")
        
        self.logger.info(f"Analysis completed for {len(results)} repositories")
        return results
    
    def serialize_commit_for_json(self, commit) -> Dict:
        """Convert a single Commit object to JSON-serializable format.
        
        Args:
            commit: Commit object to serialize
            
        Returns:
            Dictionary representation of the commit
        """
        if hasattr(commit, '__dict__'):
            return {
                'commit_id': commit.commit_id,
                'author': commit.author,
                'author_email': commit.author_email,
                'message': commit.message,
                'date': commit.date,
                'files': commit.files,
                'pac_changes': commit.pac_changes,
                'other_changes': commit.other_changes,
                'has_pac_changes': commit.has_pac_changes(),
                'pac_added_lines': commit.get_pac_added_lines(),
                'pac_deleted_lines': commit.get_pac_deleted_lines(),
                'total_added_lines': commit.get_total_added_lines(),
                'total_deleted_lines': commit.get_total_deleted_lines()
            }
        else:
            return commit
    
    def serialize_results_for_json(self, results: List[Dict], start_time) -> Dict:
        """Convert results to JSON-serializable format.
        
        Args:
            results: List of analysis results from repositories
            
        Returns:
            Dictionary ready for JSON serialization
        """
        serialized_results = []
        
        for result in results:
            # Create a copy to avoid modifying the original
            serialized_result = result.copy()
            
            # Remove statistics field if present
            if 'statistics' in serialized_result:
                del serialized_result['statistics']
            
            # Convert Commit objects to dictionaries if present
            if 'commits' in serialized_result:
                commits_data = [
                    self.serialize_commit_for_json(commit) 
                    for commit in serialized_result['commits']
                ]
                serialized_result['commits'] = commits_data
            
            serialized_results.append(serialized_result)
        end_time = time.time()
        execution_time = end_time - start_time
        # Create metadata
        metadata = {
            'analysis_start': start_time,
            'analysis_endtime': end_time,
            'analysis_duration': execution_time,
            'configuration': {
                'repository_no': self.config.repository_no,
                'use_test_mode': self.config.use_test_mode,
                'csv_path': self.config.csv_path,
                'pac_file_names_csv': PAC_FILE_NAMES_CSV_PATH
            }
        }
        
        return {
            'metadata': metadata,
            'repositories': serialized_results
        }

    def get_output_filename(self, owner_name, repository_name):
        if owner_name and repository_name:
            # Replace problematic characters for valid filename
            safe_owner = owner_name.replace('/', '_').replace('\\', '_')
            safe_owner = ''.join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in safe_owner)
            safe_repo = repository_name.replace('/', '_').replace('\\', '_')
            safe_repo = ''.join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in safe_repo)

            # Ensure the output directory exists
            output_dir = Path("outputs") / safe_owner
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            return f"outputs/{safe_owner}/{safe_repo}.json"
        else:
            raise ValueError("Owner name and repository name are required")

    def get_output_filename_from_results(self, results: List[Dict]) -> str:
        """Determine the output filename based on configuration and results.
        
        Args:
            results: List of analysis results
            
        Returns:
            Output filename
        """
        # If repository_no is specified and we have exactly one result, use repository name
        if self.config.repository_no is not None and len(results) == 1:
            # Prefer project_name (e.g., 'aws/aws-cdk') over repository_name (e.g., 'aws-cdk')
            owner_name = results[0].get('owner_name')
            repository_name = results[0].get('repository_name', '')
            
            return self.get_output_filename(owner_name, repository_name)

        
        # Otherwise, use the configured output path
        return self.config.output_path
    
    def save_results_to_json(self, results: List[Dict], start_time) -> str:
        """Save analysis results to JSON file.
        
        Args:
            results: List of analysis results from repositories
            
        Returns:
            Absolute path to the saved file
            
        Raises:
            RuntimeError: If saving fails
        """
        try:
            # Determine output filename
            output_filename = self.get_output_filename_from_results(results)
            
            # Log if we're using repository name
            if output_filename != self.config.output_path:
                self.logger.info(f"Using repository name for output: {output_filename}")
            
            # Resolve output path
            output_path = Path(output_filename)
            if not output_path.is_absolute():
                # If relative path, make it relative to the project root
                project_root = Path(__file__).parent.parent
                output_path = project_root / output_path
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert results to JSON-serializable format
            json_data = self.serialize_results_for_json(results, start_time)
            
            # Write to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            absolute_path = str(output_path.resolve())
            self.logger.info(f"Results saved to {absolute_path}")
            return absolute_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to save results to JSON: {e}") from e
    
    def print_summary(self, results: List[Dict], output_path: str) -> None:
        """Print analysis summary to console.
        
        Args:
            results: Analysis results
            output_path: Path where results were saved
        """
        total_repos = len(results)
        total_commits = sum(r.get('total_commits', 0) for r in results)
        total_pac_changes = sum(r.get('pac_changes_count', 0) for r in results)
        total_pac_commits = sum(r.get('pac_commits_count', 0) for r in results)
        
        print(f"\n{'='*70}")
        print("POLICY AS CODE ANALYSIS SUMMARY")
        print(f"{'='*70}")
        print(f"Repositories analyzed:     {total_repos}")
        print(f"Total commits:             {total_commits}")
        print(f"Total PAC changes:         {total_pac_changes}")
        print(f"PAC commits:               {total_pac_commits}")
        
        if total_commits > 0:
            print(f"PAC change ratio:          {total_pac_changes/total_commits:.2%}")
            print(f"PAC commit ratio:          {total_pac_commits/total_commits:.2%}")
        
        print(f"\nResults saved to: {output_path}")
        print(f"{'='*70}")

    def run(self) -> int:
        """Run the complete analysis workflow.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            start_time = time.time()
            # Setup logging
            self.setup_logging()
            
            # Load repositories
            repo_list = self.load_repositories()
            # Skip if we have already made an output for this project
            if self.is_exist_outputfiles(repo_list):
                self.logger.info("Skipping analysis - output file already exists")
                return 0
            # Clone and checkout repositories
            self.clone_and_checkout_repositories(repo_list)
            
            # Analyze repositories
            results = self.analyze_repositories(repo_list)


            if not results:
                self.logger.warning("No analysis results generated")
                return 1
            
            # Save results to JSON
            output_path = self.save_results_to_json(results, start_time)
            
            # Print summary
            self.print_summary(results, output_path)
            
            self.logger.info("Analysis completed successfully")
            return 0
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            return 1

    def is_exist_outputfiles(self, repo_list: List[Dict]) -> bool:
        """Check if output files already exist for the repositories.
        
        Args:
            repo_list: List of repository information
            
        Returns:
            True if output files exist for all repositories, False otherwise
        """
        # For single repository analysis, check if output file exists
        if self.config.repository_no is not None and len(repo_list) == 1:
            repo = repo_list[0]
            full_name = repo.get('full_name', '')
            
            if full_name and '/' in full_name:
                owner_name, repository_name = full_name.split('/', 1)
                try:
                    output_filename = self.get_output_filename(owner_name, repository_name)
                    output_path = Path(output_filename)
                    
                    # Make absolute path if needed
                    if not output_path.is_absolute():
                        project_root = Path(__file__).parent.parent
                        output_path = project_root / output_path
                    
                    if output_path.exists():
                        self.logger.info(f"Output file already exists: {output_path}")
                        return True
                except Exception as e:
                    self.logger.debug(f"Error checking output file: {e}")
                    return False
        
        # For multiple repositories, we proceed with analysis
        # (could be extended to check all output files if needed)
        return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Collect maintenance activities from repositories that have Policy as Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Analyze all repositories → outputs/results.json
  %(prog)s --test                   # Use test dataset → outputs/results.json
  %(prog)s --repository_no 5        # Analyze repository #5 → outputs/owner_repo.json
  %(prog)s --no-clone --verbose     # Skip cloning, verbose output → outputs/results.json
  %(prog)s --output analysis.json   # Custom output file → analysis.json
  
Note: When using --repository_no, the output file is automatically named
      after the repository and placed in outputs/ (e.g., outputs/microsoft_vscode.json)
        """
    )
    
    parser.add_argument(
        '--repository_no', 
        type=int, 
        metavar='N',
        help='Analyze specific repository by number (1-based index). '
             'Output will be named after the repository (e.g., owner_repo.json)'
    )
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Use test dataset with single repository'
    )
    parser.add_argument(
        '--no-clone',
        action='store_true',
        help='Skip cloning and only analyze existing repositories'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='outputs/results.json',
        metavar='FILE',
        help='Output JSON file path (default: %(default)s). '
             'Ignored when --repository_no is used (output will be named after the repository)'
    )
    
    return parser


def main() -> int:
    """Main function to orchestrate the repository analysis process.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create configuration
    config = AnalysisConfig(
        repository_no=args.repository_no,
        use_test_mode=args.test,
        skip_clone=args.no_clone,
        verbose=args.verbose,
        output_path=args.output
    )
    
    # Create and run data collector
    collector = DataCollector(config)
    return collector.run()


if __name__ == "__main__":
    sys.exit(main())