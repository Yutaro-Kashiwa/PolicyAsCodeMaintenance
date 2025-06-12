
"""Data aggregation script for Policy as Code analysis results."""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def find_result_files(input_dir: str) -> List[Path]:
    """Find all JSON result files in the specified directory.
    
    Args:
        input_dir: Directory to search for JSON files
        
    Returns:
        List of Path objects for JSON files
    """
    input_path = Path(input_dir)
    
    # If the path is not absolute, make it relative to the project root
    if not input_path.is_absolute():
        project_root = Path(__file__).parent.parent
        input_path = project_root / input_path
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_path}")
    
    # Find all JSON files recursively
    json_files = list(input_path.rglob("*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in: {input_path}")
    
    logging.info(f"Found {len(json_files)} JSON files to aggregate")
    return json_files


def load_result_file(file_path: Path) -> Dict[str, Any]:
    """Load and validate a single result file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the loaded data
        
    Raises:
        Exception: If file cannot be loaded or is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Basic validation - check if it looks like our result format
        if 'metadata' not in data or 'repositories' not in data:
            logging.warning(f"File {file_path} doesn't appear to be a valid result file - skipping")
            return None
            
        logging.debug(f"Loaded {file_path}: {len(data.get('repositories', []))} repositories")
        return data
        
    except Exception as e:
        logging.error(f"Failed to load {file_path}: {e}")
        return None


def aggregate_results(result_files: List[Path]) -> Dict[str, Any]:
    """Aggregate multiple result files into a single dataset.
    
    Args:
        result_files: List of JSON file paths to aggregate
        
    Returns:
        Dictionary containing aggregated results
    """
    aggregated_repositories = []
    failed_files = []
    
    for file_path in result_files:
        data = load_result_file(file_path)
        if data is None:
            failed_files.append(str(file_path))
            continue
            
        # Add repositories from this file
        repositories = data.get('repositories', [])
        aggregated_repositories.extend(repositories)
    
    # Create aggregated metadata
    metadata = {
        'aggregation_timestamp': datetime.now().isoformat(),
        'source_files': [str(f) for f in result_files],
        'failed_files': failed_files,
        'total_source_files': len(result_files),
        'successful_files': len(result_files) - len(failed_files),
        'total_repositories': len(aggregated_repositories)
    }
    
    # Calculate aggregate statistics
    total_commits = sum(r.get('total_commits', 0) for r in aggregated_repositories)
    total_pac_changes = sum(r.get('pac_changes_count', 0) for r in aggregated_repositories)
    total_pac_commits = sum(r.get('pac_commits_count', 0) for r in aggregated_repositories)
    
    metadata['summary'] = {
        'total_commits': total_commits,
        'total_pac_changes': total_pac_changes,
        'total_pac_commits': total_pac_commits,
        'pac_change_ratio': total_pac_changes / total_commits if total_commits > 0 else 0,
        'pac_commit_ratio': total_pac_commits / total_commits if total_commits > 0 else 0
    }
    
    return {
        'metadata': metadata,
        'repositories': aggregated_repositories
    }


def save_aggregated_results(data: Dict[str, Any], output_path: str) -> str:
    """Save aggregated results to a JSON file.
    
    Args:
        data: Aggregated data to save
        output_path: Path where to save the file
        
    Returns:
        Absolute path to the saved file
    """
    output_file = Path(output_path)
    
    # If the path is not absolute, make it relative to the project root
    if not output_file.is_absolute():
        project_root = Path(__file__).parent.parent
        output_file = project_root / output_file
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    absolute_path = str(output_file.resolve())
    logging.info(f"Aggregated results saved to {absolute_path}")
    return absolute_path


def print_summary(data: Dict[str, Any], output_path: str) -> None:
    """Print aggregation summary to console."""
    metadata = data['metadata']
    summary = metadata.get('summary', {})
    
    print(f"\n{'='*70}")
    print("POLICY AS CODE AGGREGATION SUMMARY")
    print(f"{'='*70}")
    print(f"Source files processed:    {metadata['successful_files']}/{metadata['total_source_files']}")
    print(f"Failed files:              {len(metadata['failed_files'])}")
    print(f"Total repositories:        {metadata['total_repositories']}")
    print(f"Total commits:             {summary.get('total_commits', 0)}")
    print(f"Total PAC changes:         {summary.get('total_pac_changes', 0)}")
    print(f"PAC commits:               {summary.get('total_pac_commits', 0)}")
    
    if summary.get('total_commits', 0) > 0:
        print(f"PAC change ratio:          {summary.get('pac_change_ratio', 0):.2%}")
        print(f"PAC commit ratio:          {summary.get('pac_commit_ratio', 0):.2%}")
    
    if metadata['failed_files']:
        print(f"\nFailed files:")
        for failed_file in metadata['failed_files']:
            print(f"  - {failed_file}")
    
    print(f"\nAggregated results saved to: {output_path}")
    print(f"{'='*70}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Aggregate Policy as Code analysis results from multiple JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Aggregate all files in outputs/ → outputs/aggregated_results.json
  %(prog)s --input-dir results/              # Aggregate files in results/ directory
  %(prog)s --output combined.json            # Save to custom output file
  %(prog)s --input-dir outputs/ --verbose    # Verbose output with detailed logging
        """
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default='outputs',
        metavar='DIR',
        help='Directory containing JSON result files to aggregate (default: %(default)s)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='outputs/aggregated_results.json',
        metavar='FILE',
        help='Output file path for aggregated results (default: %(default)s)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    return parser


def main() -> int:
    """Main function to orchestrate the aggregation process."""
    try:
        # Parse command line arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Setup logging
        setup_logging(args.verbose)
        
        # Find result files
        result_files = find_result_files(args.input_dir)
        
        # Aggregate results
        logging.info("Starting aggregation process...")
        aggregated_data = aggregate_results(result_files)
        
        # Save results
        output_path = save_aggregated_results(aggregated_data, args.output)
        
        # Print summary
        print_summary(aggregated_data, output_path)
        
        logging.info("Aggregation completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())