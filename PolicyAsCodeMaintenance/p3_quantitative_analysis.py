import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import statistics

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns

from PolicyAsCodeMaintenance.modules.config import (
    FIG_TITLE_FONTSIZE, 
    FIG_LABEL_FONTSIZE, 
    FIGSIZE,
    OUTPUTS_DIR
)
from p2_data_validate import find_output_files

# Visualization settings
PALETTE = ['#E8E8E8', '#808080', '#C0C0C0', '#404040']
sns.set_style("whitegrid")
sns.set_palette("gray")
def read_outputfiles(output_files: Dict[str, Path]) -> List[Dict[str, Any]]:
    """Read and parse output files from repositories.
    
    Args:
        output_files: Dictionary mapping repository names to file paths
        
    Returns:
        List of dictionaries containing repository data
    """
    all_data = []
    for repo_name, file_path in output_files.items():
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                all_data.append({
                    'repository': repo_name,
                    'file_path': str(file_path),
                    'data': data
                })
                logging.info(f"Successfully read data from {file_path}")
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            continue

    print(f"Successfully read {len(all_data)} output files")
    for item in all_data:
        print(f"- {item['repository']}: {item['file_path']}")
    return all_data



def measure_pac_maintenance_frequency(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate what percentage of commits modify pac code out of all commits for each repository.
    :param all_data: list of commits from repositories
    :return: list of the percentages for each repository
    """
    results = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Extract repository data
        for repo in data.get('repositories', []):
            total_commits = len(repo.get('commits', []))
            if total_commits == 0:
                continue
                
            # Count commits that have PAC changes
            pac_commits = sum(1 for commit in repo.get('commits', []) 
                            if commit.get('has_pac_changes', False))
            
            # Calculate percentage
            percentage = (pac_commits / total_commits) * 100 if total_commits > 0 else 0
            
            results.append({
                'repository': repo.get('project_name', repository_name),
                'total_commits': total_commits,
                'pac_commits': pac_commits,
                'pac_maintenance_frequency': percentage
            })
            print(repo.get('project_name', repository_name), ",", percentage)
    
    return results


def measure_size_of_pac_and_non_pac_commit(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate the median number of changed lines in commits modifying pac code and commits not modifying pac code for each repository.
    :param all_data: list of commits from repositories
    :return: list of the median number for each repository
    """
    results = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Extract repository data
        for repo in data.get('repositories', []):
            pac_commit_sizes = []
            non_pac_commit_sizes = []
            
            # Collect commit sizes
            for commit in repo.get('commits', []):
                total_changes = (commit.get('total_added_lines', 0) + 
                               commit.get('total_deleted_lines', 0))
                
                if commit.get('has_pac_changes', False):
                    pac_commit_sizes.append(total_changes)
                else:
                    non_pac_commit_sizes.append(total_changes)
            
            # Calculate medians
            pac_median = statistics.median(pac_commit_sizes) if pac_commit_sizes else 0
            non_pac_median = statistics.median(non_pac_commit_sizes) if non_pac_commit_sizes else 0
            
            results.append({
                'repository': repo.get('project_name', repository_name),
                'pac_commits_count': len(pac_commit_sizes),
                'non_pac_commits_count': len(non_pac_commit_sizes),
                'pac_commit_median_size': pac_median,
                'non_pac_commit_median_size': non_pac_median
            })
    
    return results

def _setup_violin_plot(figsize=FIGSIZE):
    """Common setup for violin plots."""
    plt.figure(figsize=figsize, facecolor='white')
    plt.gca().set_facecolor('white')
    plt.grid(False)


def _save_plot(output_path: Path):
    """Save plot with standard settings."""
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()


def plot_pac_maintenance_frequency(frequencies: List[Dict[str, Any]], output_dir: Path):
    """
    Create and save PAC Maintenance Frequency violin plot.
    
    Args:
        frequencies: List of dictionaries containing pac_maintenance_frequency data
        output_dir: Path object for output directory
    """
    _setup_violin_plot()
    freq_data = [item['pac_maintenance_frequency'] for item in frequencies]
    sns.violinplot(x=freq_data, orient='h', color=PALETTE[0], inner='box')
    plt.xlabel('PaC maintenance frequency (%)', fontsize=FIG_LABEL_FONTSIZE)
    plt.xlim(left=0, right=70)
    plt.xticks(fontsize=(FIG_LABEL_FONTSIZE+2))

    output_path = output_dir / 'pac_maintenance_frequency.pdf'
    _save_plot(output_path)
    print(f"PAC Maintenance Frequency plot saved to: {output_path}")


def plot_pac_maintainer_percentage(percentage_contributors: List[Dict[str, Any]], output_dir: Path):
    """
    Create and save PAC Maintainer Percentage violin plot.
    
    Args:
        percentage_contributors: List of dictionaries containing pac_maintainer_percentage data
        output_dir: Path object for output directory
    """
    _setup_violin_plot()
    pct_data = [item['pac_maintainer_percentage'] for item in percentage_contributors]
    sns.violinplot(x=pct_data, orient='h', color=PALETTE[0])
    plt.xlabel('PaC maintainer share (%)', fontsize=FIG_LABEL_FONTSIZE)
    plt.xlim(left=0, right=100)
    plt.xticks(fontsize=FIG_LABEL_FONTSIZE)

    output_path = output_dir / 'pac_maintainer_percentage.pdf'
    _save_plot(output_path)
    print(f"PAC Maintainer Percentage plot saved to: {output_path}")



def plot_pac_vs_nonpac_code_changes(pac_only_changes: List[Dict[str, Any]], output_dir: Path):
    """
    Create and save PAC vs Non-PAC Code Changes comparison violin plot.
    
    Includes three categories:
    1. PAC Code (in PAC commits)
    2. Non-PAC Code (in PAC commits)
    3. Non-PAC Code (in non-PAC commits)
    
    Args:
        pac_only_changes: List of dictionaries containing pac_code_median_changes, 
                         non_pac_code_median_changes, and non_pac_only_median_changes
        output_dir: Path object for output directory
    """
    _setup_violin_plot(figsize=(10, 6))
    
    # Extract data for each category
    pac_code_changes = [item['pac_code_median_changes'] 
                       for item in pac_only_changes 
                       if item['pac_code_median_changes'] > 0]
    
    non_pac_code_changes_in_pac = [item['non_pac_code_median_changes'] 
                                   for item in pac_only_changes 
                                   if item['non_pac_code_median_changes'] > 0]
    
    non_pac_code_changes_only = [item.get('non_pac_only_median_changes', 0) 
                                for item in pac_only_changes 
                                if item.get('non_pac_only_median_changes', 0) > 0]
    
    # Create DataFrame for comparison
    df_code_changes = _create_code_changes_dataframe(
        pac_code_changes, non_pac_code_changes_in_pac, non_pac_code_changes_only
    )
    
    # Define order for y-axis
    order = ['Non-PAC Code\n(in non-PAC commits)',
             'Non-PAC Code\n(in PAC commits)', 
             'PAC Code\n(in PAC commits)']
    
    sns.violinplot(data=df_code_changes, y='Code Type', x='Median Lines Changed', order=order)
    plt.title('Code Changes Distribution by Type and Commit Context', 
              fontsize=FIG_TITLE_FONTSIZE, fontweight='bold')
    plt.xlabel('Median Lines Changed', fontsize=FIG_LABEL_FONTSIZE)
    plt.xlim(left=0.1)
    plt.xticks(fontsize=FIG_LABEL_FONTSIZE)

    output_path = output_dir / 'pac_vs_nonpac_code_changes.pdf'
    _save_plot(output_path)
    print(f"PAC vs Non-PAC Code Changes plot saved to: {output_path}")


def _create_code_changes_dataframe(pac_changes: List[float], 
                                  non_pac_in_pac: List[float], 
                                  non_pac_only: List[float]) -> pd.DataFrame:
    """Create DataFrame for code changes visualization."""
    all_changes = pac_changes + non_pac_in_pac + non_pac_only
    
    all_types = (['PAC Code\n(in PAC commits)'] * len(pac_changes) + 
                 ['Non-PAC Code\n(in PAC commits)'] * len(non_pac_in_pac) + 
                 ['Non-PAC Code\n(in non-PAC commits)'] * len(non_pac_only))
    
    return pd.DataFrame({
        'Median Lines Changed': all_changes,
        'Code Type': all_types
    })


def create_individual_violin_plots(frequencies: List[Dict[str, Any]], 
                                 percentage_contributors: List[Dict[str, Any]], 
                                 pac_only_changes: List[Dict[str, Any]]) -> None:
    """
    Create individual violin plots for the metrics and save them separately.
    
    Args:
        frequencies: Data for PAC maintenance frequency
        percentage_contributors: Data for PAC maintainer percentage
        pac_only_changes: Data for PAC vs non-PAC code changes
    """
    output_dir = Path(OUTPUTS_DIR).parent / 'individual_plots'
    output_dir.mkdir(exist_ok=True)
    
    plot_pac_maintenance_frequency(frequencies, output_dir)
    plot_pac_maintainer_percentage(percentage_contributors, output_dir)
    plot_pac_vs_nonpac_code_changes(pac_only_changes, output_dir)
    
    print(f"\nAll individual plots saved to: {output_dir}")



def measure_percentage_pac_maintainer(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate what percentage of commit authors change pac code out of all the commit authors for each repository.
    :param all_data: list of commits from repositories
    :return: list of the percentage for each repository
    """
    results = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Extract repository data
        for repo in data.get('repositories', []):
            all_authors = set()
            pac_authors = set()
            
            # Collect unique authors
            for commit in repo.get('commits', []):
                author = commit.get('author', '')
                if author:
                    all_authors.add(author)
                    if commit.get('has_pac_changes', False):
                        pac_authors.add(author)
            
            # Calculate percentage
            total_authors = len(all_authors)
            pac_authors_count = len(pac_authors)
            percentage = (pac_authors_count / total_authors) * 100 if total_authors > 0 else 0
            
            results.append({
                'repository': repo.get('project_name', repository_name),
                'total_authors': total_authors,
                'pac_authors': pac_authors_count,
                'pac_maintainer_percentage': percentage
            })
    
    return results


def measure_pac_and_non_pac_code_changes(all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate the median number of changed lines in PAC code and non-PAC code separately.
    This function counts lines changed in PAC files vs non-PAC files within commits that modify PAC code,
    and also tracks non-PAC changes in commits that don't modify PAC code.
    :param all_data: list of commits from repositories
    :return: list of the median number of PAC-specific and non-PAC-specific changed lines for each repository
    """
    results = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Extract repository data
        for repo in data.get('repositories', []):
            pac_only_changes = []
            non_pac_only_changes_in_pac_commits = []
            non_pac_only_changes_in_non_pac_commits = []
            
            # Collect PAC-specific and non-PAC-specific line changes
            for commit in repo.get('commits', []):
                total_added = commit.get('total_added_lines', 0)
                total_deleted = commit.get('total_deleted_lines', 0)
                total_changes = total_added + total_deleted
                
                if commit.get('has_pac_changes', False):
                    # PAC commit - track PAC and non-PAC changes separately
                    pac_added = commit.get('pac_added_lines', 0)
                    pac_deleted = commit.get('pac_deleted_lines', 0)
                    pac_total_changes = pac_added + pac_deleted
                    
                    # Calculate non-PAC changes (total - PAC)
                    non_pac_changes = total_changes - pac_total_changes
                    
                    if pac_total_changes > 0:
                        pac_only_changes.append(pac_total_changes)
                    
                    if non_pac_changes > 0:
                        non_pac_only_changes_in_pac_commits.append(non_pac_changes)
                else:
                    # Non-PAC commit - all changes are non-PAC
                    if total_changes > 0:
                        non_pac_only_changes_in_non_pac_commits.append(total_changes)
            
            # Calculate medians
            pac_median = statistics.median(pac_only_changes) if pac_only_changes else 0
            non_pac_in_pac_median = statistics.median(non_pac_only_changes_in_pac_commits) if non_pac_only_changes_in_pac_commits else 0
            non_pac_in_non_pac_median = statistics.median(non_pac_only_changes_in_non_pac_commits) if non_pac_only_changes_in_non_pac_commits else 0
            
            results.append({
                'repository': repo.get('project_name', repository_name),
                'pac_commits_with_changes': len(pac_only_changes),
                'pac_code_median_changes': pac_median,
                'pac_changes_min': min(pac_only_changes) if pac_only_changes else 0,
                'pac_changes_max': max(pac_only_changes) if pac_only_changes else 0,
                'non_pac_commits_with_changes': len(non_pac_only_changes_in_pac_commits),
                'non_pac_code_median_changes': non_pac_in_pac_median,
                'non_pac_changes_min': min(non_pac_only_changes_in_pac_commits) if non_pac_only_changes_in_pac_commits else 0,
                'non_pac_changes_max': max(non_pac_only_changes_in_pac_commits) if non_pac_only_changes_in_pac_commits else 0,
                # New fields for non-PAC changes in non-PAC commits
                'non_pac_only_commits_count': len(non_pac_only_changes_in_non_pac_commits),
                'non_pac_only_median_changes': non_pac_in_non_pac_median,
                'non_pac_only_changes_min': min(non_pac_only_changes_in_non_pac_commits) if non_pac_only_changes_in_non_pac_commits else 0,
                'non_pac_only_changes_max': max(non_pac_only_changes_in_non_pac_commits) if non_pac_only_changes_in_non_pac_commits else 0
            })
    
    return results


def _display_results(frequencies: List[Dict[str, Any]], 
                    percentage_contributors: List[Dict[str, Any]],
                    median_changed_lines: List[Dict[str, Any]],
                    pac_and_non_pac_changes: List[Dict[str, Any]]) -> None:
    """Display analysis results in a formatted way."""
    print("\n=== PAC Maintenance Frequency ===")
    print(f"  Median freq: {np.median([freq['pac_maintenance_frequency'] for freq in frequencies]):.2f}%")
    print(f"    Median pac_commits: {np.median([freq['pac_commits'] for freq in frequencies]):.0f}")
    print(f"    Median total_commits: {np.median([freq['total_commits'] for freq in frequencies]):.0f}")

    print("\n=== PAC Maintainer Percentage ===")
    print(f"  Median pac_maintainer_percentage: {np.median([per['pac_maintainer_percentage'] for per in percentage_contributors]):.2f}%")
    print(f"    Median pac_authors: {np.median([per['pac_authors'] for per in percentage_contributors]):.0f}")
    print(f"    Median total_authors: {np.median([per['total_authors'] for per in percentage_contributors]):.0f}")

    print("\n=== Median Commit Sizes ===")
    print(f"  Median (PAC commits): {np.median([lines['pac_commit_median_size'] for lines in median_changed_lines]):.0f}")
    print(f"  Median (non-PAC commits): {np.median([lines['non_pac_commit_median_size'] for lines in median_changed_lines]):.0f}")

    print("\n=== PAC vs Non-PAC Code Changes ===")
    pac_code_medians = [changes['pac_code_median_changes'] for changes in pac_and_non_pac_changes]
    non_pac_in_pac = [changes['non_pac_code_median_changes'] for changes in pac_and_non_pac_changes if changes['non_pac_code_median_changes'] > 0]
    non_pac_only = [changes['non_pac_only_median_changes'] for changes in pac_and_non_pac_changes if changes.get('non_pac_only_median_changes', 0) > 0]
    
    print(f"  Median PAC code changes (in PAC commits): {np.median(pac_code_medians):.0f}")
    print(f"  Median non-PAC code changes (in PAC commits): {np.median(non_pac_in_pac):.0f}")
    print(f"  Median non-PAC code changes (in non-PAC commits): {np.median(non_pac_only):.0f}")
    print(f"  Total repos with PAC changes: {len([c for c in pac_and_non_pac_changes if c['pac_commits_with_changes'] > 0])}")
    print(f"  Total repos with non-PAC only commits: {len([c for c in pac_and_non_pac_changes if c.get('non_pac_only_commits_count', 0) > 0])}")


def main() -> int:
    """Main function to orchestrate the quantitative analysis."""
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Find and read output files
        output_files = find_output_files(OUTPUTS_DIR)
        data = read_outputfiles(output_files)
        
        # Perform analyses
        frequencies = measure_pac_maintenance_frequency(data)
        percentage_contributors = measure_percentage_pac_maintainer(data)
        median_changed_lines = measure_size_of_pac_and_non_pac_commit(data)
        pac_and_non_pac_changes = measure_pac_and_non_pac_code_changes(data)
        
        # Display results
        _display_results(frequencies, percentage_contributors, median_changed_lines, pac_and_non_pac_changes)

        # Create visualizations
        create_individual_violin_plots(frequencies, percentage_contributors, pac_and_non_pac_changes)

        return 0
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())