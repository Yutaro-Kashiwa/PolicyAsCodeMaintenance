"""Data validation script to check which repositories have been processed."""

import logging
import sys
from pathlib import Path
from typing import List, Dict
import os
from p1_data_collect import AnalysisConfig, DataCollector
from modules.repository_manager import RepositoryManager
from modules.config import REPOS_DIR, DEFAULT_REPOS_CSV, OUTPUTS_DIR

import pandas as pd



def load_repository_list(csv_path: str) -> List[Dict[str, str]]:
    """Load repository list from CSV file using RepositoryManager.
    
    Args:
        csv_path: Path to the CSV file containing repository information
        
    Returns:
        List of dictionaries containing repository information
    """
    # Use RepositoryManager to load repositories
    repo_manager = RepositoryManager(REPOS_DIR)

    try:
        # Load all repositories (no specific repository_no)
        repositories = repo_manager.load_repositories(csv_path, repository_no=None)
        return repositories

    except Exception as e:
        logging.error(f"Failed to load repositories from {csv_path}: {e}")
        raise


def find_output_files(output_dir: str) -> Dict[str, Path]:
    """Find all output files in the outputs directory.
    
    Args:
        output_dir: Directory containing output files
        
    Returns:
        Dictionary mapping repository names to their output file paths
    """
    output_path = Path(output_dir)

    # If the path is not absolute, make it relative to the project root
    if not output_path.is_absolute():
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_path

    if not output_path.exists():
        logging.warning(f"Output directory does not exist: {output_path}")
        return {}

    # Find all JSON files recursively
    json_files = list(output_path.rglob("*.json"))

    # Create a mapping of repository names to file paths
    output_files = {}
    for json_file in json_files:
        # Skip aggregated results file
        if json_file.name == 'aggregated_results.json':
            continue

        # Get the repository name from the file path
        # Expected structure: outputs/owner_repo/repo.json or outputs/repo.json
        repo_name = json_file.stem  # filename without extension
        output_files[repo_name] = json_file

    logging.info(f"Found {len(output_files)} output files in {output_path}")
    return output_files


def main() -> int:
    """Main function to orchestrate the validation process."""
    try:
        # Load repository list from CSV
        logging.info("Loading repository list from CSV...")
        repositories = load_repository_list(DEFAULT_REPOS_CSV)
        missed_repositories = set()
        for r in repositories:
            missed_repositories.add(r['full_name'])
        number_of_studied_repositories = len(missed_repositories)
        print("# of all repos", number_of_studied_repositories)
        # Find output files
        logging.info("Scanning output directory for result files...")
        output_files = find_output_files(OUTPUTS_DIR)

        for f in output_files:
            path = output_files[f]
            if not str(path).endswith('.json'):
                continue
            parent_dir_name = os.path.basename(os.path.dirname(path))
            file_name = os.path.splitext(os.path.basename(path))[0]
            full_name = f"{parent_dir_name}/{file_name}"
            if full_name in missed_repositories:
                missed_repositories.remove(full_name)

        # print("-These projects might not have been collected yet.:------------------")
        # print("\n".join(sorted(missed_repositories)))
        print("-------------------")
        print("All repositories:", number_of_studied_repositories)
        number_of_completions = (number_of_studied_repositories - len(missed_repositories))
        print("Collected repositories:", number_of_completions,
              f"{number_of_completions / number_of_studied_repositories}%")
        number_of_misses = len(missed_repositories)
        print("Missed repositories:", number_of_misses, f"{number_of_misses / number_of_studied_repositories}%")

        for m in missed_repositories:
            i = 0
            for r in repositories:
                i += 1
                if r['full_name'] == m:
                    print(r['full_name'], i)
                    break
            if RETRIEVE_MISSED_REPOSITORIES:

                config = AnalysisConfig(
                    repository_no=i,
                    use_test_mode=False,
                    skip_clone=False,
                    verbose=False,
                    output_path=OUTPUTS_DIR
                )

                # Create and run data collector
                collector = DataCollector(config)
                collector.run()

        return 0

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1

RETRIEVE_MISSED_REPOSITORIES = True

if __name__ == "__main__":
    sys.exit(main())
