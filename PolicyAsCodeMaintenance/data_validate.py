"""Data validation script to check which repositories have been processed."""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import os
from data_collect import AnalysisConfig
from modules.repository_manager import RepositoryManager
from modules.config import REPOS_DIR, DEFAULT_REPOS_CSV, OUTPUTS_DIR


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_repository_list(csv_path:str) -> List[Dict[str, str]]:
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


def validate_output_file(file_path: Path) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """Validate a single output file.

    Args:
        file_path: Path to the JSON output file

    Returns:
        Tuple of (is_valid, error_message, metadata)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if it has the expected structure
        if 'metadata' not in data:
            return False, "Missing 'metadata' field", None

        if 'repositories' not in data:
            return False, "Missing 'repositories' field", None

        # Check if it contains repository data
        repos = data.get('repositories', [])
        if not repos:
            return False, "No repository data found", None

        # Extract relevant metadata
        metadata = {
            'timestamp': data['metadata'].get('analysis_timestamp', 'Unknown'),
            'repository_count': len(repos),
            'total_commits': sum(r.get('total_commits', 0) for r in repos),
            'pac_changes': sum(r.get('pac_changes_count', 0) for r in repos)
        }

        return True, None, metadata

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", None
    except Exception as e:
        return False, f"Error reading file: {e}", None


def check_repository_outputs(repositories: List[Dict[str, str]], output_files: Dict[str, Path]) -> Dict[str, Dict]:
    """Check which repositories have output files and validate them.

    Args:
        repositories: List of repository information from CSV
        output_files: Dictionary mapping repository names to output file paths

    Returns:
        Dictionary with validation results for each repository
    """
    results = {}

    for repo in repositories:
        repo_id = repo.get('id', 'Unknown')
        full_name = repo.get('full_name', 'Unknown')
        
        # Extract repository name from full_name (e.g., 'aws/aws-cdk' -> 'aws-cdk')
        if full_name and '/' in full_name:
            repo_name = full_name.split('/')[-1]
        else:
            repo_name = full_name

        # Try to find output file by repository name
        output_file = output_files.get(repo_name)

        if output_file:
            # Validate the output file
            is_valid, error_msg, metadata = validate_output_file(output_file)

            results[repo_id] = {
                'id': repo_id,
                'name': repo_name,
                'full_name': full_name,
                'has_output': True,
                'output_file': str(output_file),
                'is_valid': is_valid,
                'error': error_msg,
                'metadata': metadata
            }
        else:
            results[repo_id] = {
                'id': repo_id,
                'name': repo_name,
                'full_name': full_name,
                'has_output': False,
                'output_file': None,
                'is_valid': False,
                'error': 'Output file not found',
                'metadata': None
            }

    return results


def generate_validation_report(results: Dict[str, Dict], output_path: str) -> str:
    """Generate a validation report and save it to a file.
    
    Args:
        results: Validation results for all repositories
        output_path: Path where to save the report
        
    Returns:
        Absolute path to the saved report
    """
    output_file = Path(output_path)
    
    # If the path is not absolute, make it relative to the project root
    if not output_file.is_absolute():
        project_root = Path(__file__).parent.parent
        output_file = project_root / output_file
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare report data
    total_repos = len(results)
    processed_repos = sum(1 for r in results.values() if r['has_output'])
    valid_repos = sum(1 for r in results.values() if r['is_valid'])
    
    report = {
        'validation_timestamp': datetime.now().isoformat(),
        'summary': {
            'total_repositories': total_repos,
            'processed_repositories': processed_repos,
            'valid_outputs': valid_repos,
            'missing_outputs': total_repos - processed_repos,
            'invalid_outputs': processed_repos - valid_repos,
            'processing_rate': processed_repos / total_repos if total_repos > 0 else 0,
            'validation_rate': valid_repos / processed_repos if processed_repos > 0 else 0
        },
        'repositories': results
    }
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    absolute_path = str(output_file.resolve())
    logging.info(f"Validation report saved to {absolute_path}")
    return absolute_path


def print_summary(results: Dict[str, Dict], report_path: str) -> None:
    """Print validation summary to console."""
    total_repos = len(results)
    processed_repos = sum(1 for r in results.values() if r['has_output'])
    valid_repos = sum(1 for r in results.values() if r['is_valid'])
    missing_repos = total_repos - processed_repos
    invalid_repos = processed_repos - valid_repos
    
    print(f"\n{'='*70}")
    print("DATA VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total repositories:        {total_repos}")
    print(f"Processed repositories:    {processed_repos} ({processed_repos/total_repos*100:.1f}%)")
    print(f"Valid outputs:             {valid_repos} ({valid_repos/total_repos*100:.1f}%)")
    print(f"Missing outputs:           {missing_repos} ({missing_repos/total_repos*100:.1f}%)")
    print(f"Invalid outputs:           {invalid_repos} ({invalid_repos/total_repos*100:.1f}%)")
    
    # Show some examples of missing repositories
    if missing_repos > 0:
        print(f"\nExamples of missing repositories (showing up to 10):")
        missing_count = 0
        for repo_id, repo_data in results.items():
            if not repo_data['has_output']:
                print(f"  - {repo_data['full_name']} (ID: {repo_id})")
                missing_count += 1
                if missing_count >= 10:
                    break
        if missing_repos > 10:
            print(f"  ... and {missing_repos - 10} more")
    
    # Show invalid outputs
    if invalid_repos > 0:
        print(f"\nInvalid output files:")
        for repo_id, repo_data in results.items():
            if repo_data['has_output'] and not repo_data['is_valid']:
                print(f"  - {repo_data['full_name']}: {repo_data['error']}")
    
    print(f"\nDetailed validation report saved to: {report_path}")
    print(f"{'='*70}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Validate Policy as Code analysis outputs against repository list',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Validate using repos-full.csv
  %(prog)s --csv inputs/repos.csv           # Use different CSV file
  %(prog)s --output-dir results/            # Check different output directory
  %(prog)s --report validation.json         # Save report to custom file
  %(prog)s --verbose                        # Enable verbose logging
        """
    )

    parser.add_argument(
        '--report',
        type=str,
        default='outputs/validation_report.json',
        metavar='FILE',
        help='Output file path for validation report (default: %(default)s)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    return parser


def main() -> int:
    """Main function to orchestrate the validation process."""
    try:
        # Parse command line arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Setup logging
        setup_logging(args.verbose)

        
        # Load repository list from CSV
        logging.info("Loading repository list from CSV...")
        repositories = load_repository_list(DEFAULT_REPOS_CSV)

        
        # Find output files
        logging.info("Scanning output directory for result files...")
        output_files = find_output_files(OUTPUTS_DIR)


        #TODO: inputfileとoutputファイルの確認作業を入れる
        for f in output_files:
            path = output_files[f]
            # 直前のディレクトリ名とファイル名に分ける
            dir_name = os.path.dirname(path)  # ディレクトリ部分
            file_name = os.path.basename(path)  # ファイル名部分

            # さらに直前のディレクトリ名だけを取得したい場合
            parent_dir_name = os.path.basename(dir_name)

            print(f"フルパス: {path}")
            print(f"ディレクトリパス: {dir_name}")
            print(f"ファイル名: {file_name}")
            print(f"直前のディレクトリ名: {parent_dir_name}")
            print("-" * 30)
        print(output_files)
        exit(1)
        # Validate outputs
        logging.info("Validating repository outputs...")
        results = check_repository_outputs(repositories, output_files)
        
        # Generate report
        report_path = generate_validation_report(results, args.report)
        
        # Print summary
        print_summary(results, report_path)
        
        logging.info("Validation completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())