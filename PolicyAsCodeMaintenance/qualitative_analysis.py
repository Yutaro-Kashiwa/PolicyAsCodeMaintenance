import sys
import csv
import logging
import random
from pathlib import Path
from typing import Dict, List, Any

# Import data loading functions from quantitative_analysis
from quantitative_analysis import read_outputfiles
from data_validate import find_output_files
from modules.config import OUTPUTS_DIR


def generate_github_commit_url(project_name: str, commit_sha: str) -> str:
    """
    Generate GitHub commit URL from project name and commit SHA.
    
    Args:
        project_name: Full project name (e.g., 'owner/repository')
        commit_sha: Commit SHA hash
        
    Returns:
        GitHub commit URL
    """
    if project_name and '/' in project_name and commit_sha:
        return f"https://github.com/{project_name}/commit/{commit_sha}"
    return ""


def extract_pac_commits(all_data: List[Dict]) -> List[Dict]:
    """
    Extract all commits that modify PaC files from the loaded data.
    
    Args:
        all_data: List of repository data from JSON files
        
    Returns:
        List of dictionaries containing commit information
    """
    pac_commits = []
    
    for item in all_data:
        data = item['data']
        
        # Process each repository
        for repo in data.get('repositories', []):
            project_name = repo.get('project_name', '')
            
            # Process each commit
            for commit in repo.get('commits', []):
                if commit.get('has_pac_changes', False):
                    # Extract commit information
                    commit_info = {
                        'project_name': project_name,
                        'commit_sha': commit.get('commit_id', ''),
                        'commit_message': commit.get('message', '').replace('\n', ' '),
                        'author': commit.get('author', ''),
                        'date': commit.get('date', ''),
                        'pac_files_count': len(commit.get('pac_changes', [])),
                        'other_files_count': len(commit.get('other_changes', [])),
                        'pac_added_lines': commit.get('pac_added_lines', 0),
                        'pac_deleted_lines': commit.get('pac_deleted_lines', 0),
                        'total_added_lines': commit.get('total_added_lines', 0),
                        'total_deleted_lines': commit.get('total_deleted_lines', 0),
                        'github_url': generate_github_commit_url(project_name, commit.get('commit_id', ''))
                    }
                    
                    # Add information about changed PAC files
                    pac_files = []
                    pac_files_detailed = []
                    for pac_change in commit.get('pac_changes', []):
                        file_path = pac_change.get('file', '')
                        additions = pac_change.get('additions', 0)
                        deletions = pac_change.get('deletions', 0)
                        
                        pac_files.append(file_path)
                        pac_files_detailed.append(f"{file_path} (+{additions}/-{deletions})")
                    
                    commit_info['pac_files'] = '; '.join(pac_files)
                    commit_info['pac_files_detailed'] = '; '.join(pac_files_detailed)
                    
                    pac_commits.append(commit_info)
    
    return pac_commits


def sample_pac_commits(pac_commits: List[Dict], sample_size: int = None, 
                      random_seed: int = 42) -> List[Dict]:
    """
    Sample a subset of PaC commits for manual inspection.
    
    Args:
        pac_commits: List of all PaC commits
        sample_size: Number of commits to sample (None for all commits)
        random_seed: Random seed for reproducibility
        
    Returns:
        Sampled list of commits
    """
    if sample_size is None or sample_size >= len(pac_commits):
        return pac_commits
    
    random.seed(random_seed)
    return random.sample(pac_commits, sample_size)


def write_commits_to_csv(commits: List[Dict], output_file: str):
    """
    Write commit information to a CSV file.
    
    Args:
        commits: List of commit dictionaries
        output_file: Path to output CSV file
    """
    if not commits:
        print("No commits to write.")
        return
    
    # Define CSV columns
    fieldnames = [
        'project_name',
        'commit_sha',
        'commit_message',
        'author',
        'date',
        'github_url',
        'pac_files_count',
        'other_files_count',
        'pac_added_lines',
        'pac_deleted_lines',
        'total_added_lines',
        'total_deleted_lines',
        'pac_files',
        'pac_files_detailed'
    ]
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(commits)
    
    print(f"Successfully wrote {len(commits)} commits to {output_file}")


def generate_commit_statistics(commits: List[Dict]) -> Dict:
    """
    Generate statistics about the PaC commits.
    
    Args:
        commits: List of commit dictionaries
        
    Returns:
        Dictionary containing various statistics
    """
    if not commits:
        return {}
    
    # Count commits by project
    project_counts = {}
    for commit in commits:
        project = commit['project_name']
        project_counts[project] = project_counts.get(project, 0) + 1
    
    # Calculate line change statistics
    pac_line_changes = [c['pac_added_lines'] + c['pac_deleted_lines'] for c in commits]
    total_line_changes = [c['total_added_lines'] + c['total_deleted_lines'] for c in commits]
    
    stats = {
        'total_commits': len(commits),
        'unique_projects': len(set(c['project_name'] for c in commits)),
        'commits_by_project': project_counts,
        'avg_pac_files_per_commit': sum(c['pac_files_count'] for c in commits) / len(commits),
        'avg_other_files_per_commit': sum(c['other_files_count'] for c in commits) / len(commits),
        'avg_pac_line_changes': sum(pac_line_changes) / len(commits),
        'avg_total_line_changes': sum(total_line_changes) / len(commits),
        'commits_with_only_pac': len([c for c in commits if c['other_files_count'] == 0]),
        'commits_with_mixed_changes': len([c for c in commits if c['other_files_count'] > 0])
    }
    
    return stats


def print_commit_statistics(stats: Dict):
    """
    Print commit statistics in a formatted way.
    
    Args:
        stats: Statistics dictionary from generate_commit_statistics
    """
    print("\n" + "="*60)
    print("PAC COMMIT STATISTICS")
    print("="*60)
    
    print(f"\nTotal PaC commits: {stats.get('total_commits', 0)}")
    print(f"Unique projects: {stats.get('unique_projects', 0)}")
    print(f"\nCommit composition:")
    print(f"  - Only PaC files: {stats.get('commits_with_only_pac', 0)} ({stats.get('commits_with_only_pac', 0)/stats.get('total_commits', 1)*100:.1f}%)")
    print(f"  - Mixed changes: {stats.get('commits_with_mixed_changes', 0)} ({stats.get('commits_with_mixed_changes', 0)/stats.get('total_commits', 1)*100:.1f}%)")
    
    print(f"\nAverage per commit:")
    print(f"  - PaC files: {stats.get('avg_pac_files_per_commit', 0):.2f}")
    print(f"  - Other files: {stats.get('avg_other_files_per_commit', 0):.2f}")
    print(f"  - PaC line changes: {stats.get('avg_pac_line_changes', 0):.0f}")
    print(f"  - Total line changes: {stats.get('avg_total_line_changes', 0):.0f}")
    
    print(f"\nTop 10 projects by PaC commits:")
    sorted_projects = sorted(stats.get('commits_by_project', {}).items(), 
                           key=lambda x: x[1], reverse=True)[:10]
    for project, count in sorted_projects:
        print(f"  {project}: {count} commits")


def main(sample_size: int = None, output_filename: str = None):
    """
    Main function to generate CSV file for manual inspection.
    
    Args:
        sample_size: Number of commits to sample (None for all)
        output_filename: Custom output filename (default: pac_commits_for_inspection.csv)
    """
    try:
        # Set default output filename
        if output_filename is None:
            output_filename = "pac_commits_for_inspection.csv"
        
        # Load data
        print("Loading repository data...")
        output_files = find_output_files(OUTPUTS_DIR)
        all_data = read_outputfiles(output_files)
        
        # Extract PaC commits
        print("\nExtracting PaC commits...")
        pac_commits = extract_pac_commits(all_data)
        print(f"Found {len(pac_commits)} commits that modify PaC files")
        
        # Generate statistics
        stats = generate_commit_statistics(pac_commits)
        print_commit_statistics(stats)
        
        # Sample commits if requested
        if sample_size:
            print(f"\nSampling {sample_size} commits for inspection...")
            sampled_commits = sample_pac_commits(pac_commits, sample_size)
        else:
            sampled_commits = pac_commits
        
        # Sort commits by project and date for better organization
        sampled_commits.sort(key=lambda x: (x['project_name'], x['date']))
        
        # Write to CSV
        output_path = Path(OUTPUTS_DIR).parent / output_filename
        print(f"\nWriting commits to CSV...")
        write_commits_to_csv(sampled_commits, str(output_path))
        
        print(f"\nCSV file created: {output_path}")
        print(f"Total commits in CSV: {len(sampled_commits)}")
        
        # Also create a smaller sample for quick inspection
        if len(sampled_commits) > 100 and sample_size is None:
            sample_output = Path(OUTPUTS_DIR).parent / "pac_commits_sample_100.csv"
            sample_100 = sample_pac_commits(pac_commits, 100)
            sample_100.sort(key=lambda x: (x['project_name'], x['date']))
            write_commits_to_csv(sample_100, str(sample_output))
            print(f"\nAlso created a sample of 100 commits: {sample_output}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error in qualitative analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Can be called with sample size as argument
    if len(sys.argv) > 1:
        try:
            sample_size = int(sys.argv[1])
            sys.exit(main(sample_size=sample_size))
        except ValueError:
            print("Usage: python qualitative_analysis.py [sample_size]")
            sys.exit(1)
    else:
        # https://www.calculator.net/sample-size-calculator.html?type=1&cl=95&ci=5&pp=50&ps=8815&x=Calculate
        sys.exit(main(sample_size=369))