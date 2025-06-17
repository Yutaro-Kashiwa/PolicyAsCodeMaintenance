import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns

from data_validate import find_output_files
from modules.config import OUTPUTS_DIR


def read_outputfiles(output_files):
    # Read the content of each output file
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
    pass
    return all_data



def measure_pac_maintenance_frequency(all_data):
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
    
    return results


def measure_size_of_pac_and_non_pac_commit(all_data):
    """
    Calculate the median number of changed lines in commits modifying pac code and commits not modifying pac code for each repository.
    :param all_data: list of commits from repositories
    :return: list of the median number for each repository
    """
    import statistics
    
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

def create_violin_plots(frequencies, percentage_contributors, median_changed_lines, pac_only_changes):
    """
    Create violin plots for the four metrics using seaborn.
    """
    # Set the style
    sns.set_style("whitegrid")
    
    # Create a figure with 4 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. PAC Maintenance Frequency violin plot
    freq_data = [item['pac_maintenance_frequency'] for item in frequencies]
    sns.violinplot(y=freq_data, ax=axes[0, 0], color='lightblue')
    axes[0, 0].set_title('PAC Maintenance Frequency Distribution', fontsize=14, fontweight='bold')
    axes[0, 0].set_ylabel('Percentage (%)', fontsize=12)
    axes[0, 0].set_ylim(bottom=0)  # Ensure no negative values
    
    # 2. PAC Maintainer Percentage violin plot
    pct_data = [item['pac_maintainer_percentage'] for item in percentage_contributors]
    sns.violinplot(y=pct_data, ax=axes[0, 1], color='lightgreen')
    axes[0, 1].set_title('PAC Maintainer Percentage Distribution', fontsize=14, fontweight='bold')
    axes[0, 1].set_ylabel('Percentage (%)', fontsize=12)
    axes[0, 1].set_ylim(bottom=0)  # Ensure no negative values
    
    # 3. Median Changed Lines - Two-sided comparison
    # Prepare data for two-sided violin plot
    pac_sizes = []
    non_pac_sizes = []
    for item in median_changed_lines:
        pac_sizes.append(item['pac_commit_median_size'])
        non_pac_sizes.append(item['non_pac_commit_median_size'])
    
    # Create DataFrame for two-sided comparison
    df_sizes = pd.DataFrame({
        'Median Lines Changed': pac_sizes + non_pac_sizes,
        'Commit Type': ['PAC'] * len(pac_sizes) + ['Non-PAC'] * len(non_pac_sizes)
    })
    
    sns.violinplot(data=df_sizes, x='Commit Type', y='Median Lines Changed', ax=axes[1, 0],
                   palette=['lightcoral', 'lightskyblue'])
    axes[1, 0].set_title('Median Commit Size Distribution', fontsize=14, fontweight='bold')
    axes[1, 0].set_ylabel('Median Lines Changed', fontsize=12)
    axes[1, 0].set_yscale('log')
    axes[1, 0].set_yticks([1, 10, 100, 1000, 10000, 100000])
    axes[1, 0].set_ylim(bottom=0.1)  # Ensure no negative values, use 0.1 for log scale
    
    # 4. PAC vs Non-PAC Code Changes - Two-sided comparison
    # Prepare data for two-sided violin plot
    pac_code_changes = []
    non_pac_code_changes = []
    for item in pac_only_changes:
        if item['pac_code_median_changes'] > 0:
            pac_code_changes.append(item['pac_code_median_changes'])
        if item['non_pac_code_median_changes'] > 0:
            non_pac_code_changes.append(item['non_pac_code_median_changes'])
    
    # Create DataFrame for two-sided comparison
    df_code_changes = pd.DataFrame({
        'Median Lines Changed': pac_code_changes + non_pac_code_changes,
        'Code Type': ['PAC Code'] * len(pac_code_changes) + ['Non-PAC Code'] * len(non_pac_code_changes)
    })
    
    sns.violinplot(data=df_code_changes, x='Code Type', y='Median Lines Changed', ax=axes[1, 1],
                   palette=['salmon', 'skyblue'])
    axes[1, 1].set_title('PAC vs Non-PAC Code Changes Distribution', fontsize=14, fontweight='bold')
    axes[1, 1].set_ylabel('Median Lines Changed (within PAC commits)', fontsize=12)
    axes[1, 1].set_yscale('log')
    axes[1, 1].set_yticks([1, 10, 100, 1000, 10000])
    axes[1, 1].set_ylim(bottom=0.1)  # Ensure no negative values, use 0.1 for log scale

    plt.tight_layout()
    
    # Save the plot
    output_path = Path(OUTPUTS_DIR).parent / 'pac_metrics_violin_plots.pdf'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nViolin plots saved to: {output_path}")
    
    # Also show the plot
    plt.show()


def measure_percentage_pac_maintainer(all_data):
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


def measure_pac_and_non_pac_code_changes(all_data):
    """
    Calculate the median number of changed lines in PAC code and non-PAC code separately.
    This function counts lines changed in PAC files vs non-PAC files within commits that modify PAC code.
    :param all_data: list of commits from repositories
    :return: list of the median number of PAC-specific and non-PAC-specific changed lines for each repository
    """
    import statistics
    
    results = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Extract repository data
        for repo in data.get('repositories', []):
            pac_only_changes = []
            non_pac_only_changes = []
            
            # Collect PAC-specific and non-PAC-specific line changes
            for commit in repo.get('commits', []):
                if commit.get('has_pac_changes', False):
                    # Get PAC-specific line changes
                    pac_added = commit.get('pac_added_lines', 0)
                    pac_deleted = commit.get('pac_deleted_lines', 0)
                    pac_total_changes = pac_added + pac_deleted
                    
                    # Get total changes and calculate non-PAC changes
                    total_added = commit.get('total_added_lines', 0)
                    total_deleted = commit.get('total_deleted_lines', 0)
                    total_changes = total_added + total_deleted
                    
                    # Calculate non-PAC changes (total - PAC)
                    non_pac_changes = total_changes - pac_total_changes
                    
                    if pac_total_changes > 0:
                        pac_only_changes.append(pac_total_changes)
                    
                    if non_pac_changes > 0:
                        non_pac_only_changes.append(non_pac_changes)
            
            # Calculate medians
            pac_median = statistics.median(pac_only_changes) if pac_only_changes else 0
            non_pac_median = statistics.median(non_pac_only_changes) if non_pac_only_changes else 0
            
            results.append({
                'repository': repo.get('project_name', repository_name),
                'pac_commits_with_changes': len(pac_only_changes),
                'pac_code_median_changes': pac_median,
                'pac_changes_min': min(pac_only_changes) if pac_only_changes else 0,
                'pac_changes_max': max(pac_only_changes) if pac_only_changes else 0,
                'non_pac_commits_with_changes': len(non_pac_only_changes),
                'non_pac_code_median_changes': non_pac_median,
                'non_pac_changes_min': min(non_pac_only_changes) if non_pac_only_changes else 0,
                'non_pac_changes_max': max(non_pac_only_changes) if non_pac_only_changes else 0
            })
    
    return results


def main() -> int:
    """Main function to orchestrate the aggregation process."""
    try:
        output_files = find_output_files(OUTPUTS_DIR)
        
        data = read_outputfiles(output_files)
        
        frequencies = measure_pac_maintenance_frequency(data)
        percentage_contributors = measure_percentage_pac_maintainer(data)
        median_changed_lines = measure_size_of_pac_and_non_pac_commit(data)
        pac_and_non_pac_changes = measure_pac_and_non_pac_code_changes(data)
        
        # Display results
        print("\n=== PAC Maintenance Frequency ===")
        print("  Median freq: ", np.median([freq['pac_maintenance_frequency'] for freq in frequencies]))
        print("    Median pac_commits: ", np.median([freq['pac_commits'] for freq in frequencies]))
        print("    Median total_commits: ", np.median([freq['total_commits'] for freq in frequencies]))

        print("\n=== PAC Maintainer Percentage ===")
        print("  Median pac_maintainer_percentage: ", np.median([per['pac_maintainer_percentage'] for per in percentage_contributors]))
        print("    Median pac_authors: ", np.median([per['pac_authors'] for per in percentage_contributors]))
        print("    Median total_authors: ", np.median([per['total_authors'] for per in percentage_contributors]))

        
        print("\n=== Median Commit Sizes ===")
        print("  Median (PAC commits): ", np.median([lines['pac_commit_median_size'] for lines in median_changed_lines]))
        print("  Median (non-PAC commits): ", np.median([lines['non_pac_commit_median_size'] for lines in median_changed_lines]))

        print("\n=== PAC vs Non-PAC Code Changes ===")
        print("  Median PAC code changes: ", np.median([changes['pac_code_median_changes'] for changes in pac_and_non_pac_changes]))
        print("  Median non-PAC code changes: ", np.median([changes['non_pac_code_median_changes'] for changes in pac_and_non_pac_changes if changes['non_pac_code_median_changes'] > 0]))
        print("  Total repos with PAC changes: ", len([c for c in pac_and_non_pac_changes if c['pac_commits_with_changes'] > 0]))

        # Create violin plots
        create_violin_plots(frequencies, percentage_contributors, median_changed_lines, pac_and_non_pac_changes)
        
        return 0
        
    except Exception as e:

        return 1


if __name__ == "__main__":
    sys.exit(main())