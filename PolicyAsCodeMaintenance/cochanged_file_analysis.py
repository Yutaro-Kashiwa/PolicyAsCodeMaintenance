import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
from itertools import combinations

# Import data loading functions from quantitative_analysis
from quantitative_analysis import read_outputfiles
from data_validate import find_output_files
from modules.config import OUTPUTS_DIR


def extract_file_extension(file_path: str) -> str:
    """
    Extract file extension from a file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension including the dot (e.g., '.py', '.yaml')
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    # Handle special cases like .tar.gz
    if path.stem and path.stem.endswith('.tar'):
        extension = '.tar' + extension
    
    return extension if extension else 'no_extension'


def extract_cochanged_extensions(all_data: List[Dict]) -> List[Dict]:
    """
    Extract file extensions that are changed together with PaC files in each commit.
    
    Args:
        all_data: List of repository data from JSON files
        
    Returns:
        List of dictionaries containing commit info and co-changed extensions
    """
    cochange_data = []
    
    for item in all_data:
        repository_name = item['repository']
        data = item['data']
        
        # Process each repository
        for repo in data.get('repositories', []):
            repo_id = repo.get('repository_id')
            project_name = repo.get('project_name', repository_name)
            
            # Process each commit
            for commit in repo.get('commits', []):
                if not commit.get('has_pac_changes', False):
                    continue
                
                # Extract PAC file extensions
                pac_extensions = set()
                for pac_change in commit.get('pac_changes', []):
                    ext = extract_file_extension(pac_change['file'])
                    pac_extensions.add(ext)
                
                # Extract non-PAC file extensions
                other_extensions = set()
                for other_change in commit.get('other_changes', []):
                    ext = extract_file_extension(other_change['file'])
                    other_extensions.add(ext)
                
                # Store the co-change information
                if pac_extensions and (pac_extensions or other_extensions):
                    cochange_data.append({
                        'repository': project_name,
                        'commit_id': commit.get('commit_id'),
                        'pac_extensions': list(pac_extensions),
                        'other_extensions': list(other_extensions),
                        'all_extensions': list(pac_extensions | other_extensions),
                        'num_pac_files': len(commit.get('pac_changes', [])),
                        'num_other_files': len(commit.get('other_changes', []))
                    })
    
    return cochange_data


def calculate_extension_statistics(cochange_data: List[Dict]) -> Dict:
    """
    Calculate statistics about file extensions co-changed with PaC files.
    
    Args:
        cochange_data: List of co-change data from extract_cochanged_extensions
        
    Returns:
        Dictionary containing various statistics
    """
    # Count occurrences of each extension type
    pac_extension_counter = Counter()
    other_extension_counter = Counter()
    cochange_counter = Counter()
    
    for data in cochange_data:
        # Count PAC extensions
        for ext in data['pac_extensions']:
            pac_extension_counter[ext] += 1
        
        # Count other extensions
        for ext in data['other_extensions']:
            other_extension_counter[ext] += 1
        
        # Count co-occurrences
        for pac_ext in data['pac_extensions']:
            for other_ext in data['other_extensions']:
                cochange_counter[(pac_ext, other_ext)] += 1
    
    return {
        'pac_extensions': pac_extension_counter,
        'other_extensions': other_extension_counter,
        'cochange_pairs': cochange_counter,
        'total_commits': len(cochange_data),
        'commits_with_other_files': len([d for d in cochange_data if d['other_extensions']])
    }


def mine_association_rules(cochange_data: List[Dict], min_support: float = 0.01, 
                          min_confidence: float = 0.1) -> List[Dict]:
    """
    Mine association rules between PaC extensions and other file extensions.
    
    Args:
        cochange_data: List of co-change data
        min_support: Minimum support threshold (proportion of transactions)
        min_confidence: Minimum confidence threshold
        
    Returns:
        List of association rules with metrics
    """
    # Create transaction database
    transactions = []
    for data in cochange_data:
        if data['pac_extensions'] and data['other_extensions']:
            # Create items as "pac:.ext" and "other:.ext" to distinguish them
            transaction = set()
            for ext in data['pac_extensions']:
                transaction.add(f"pac:{ext}")
            for ext in data['other_extensions']:
                transaction.add(f"other:{ext}")
            transactions.append(transaction)
    
    if not transactions:
        return []
    
    total_transactions = len(transactions)
    min_support_count = int(min_support * total_transactions)
    
    # Calculate item frequencies
    item_counts = Counter()
    for transaction in transactions:
        for item in transaction:
            item_counts[item] += 1
    
    # Find frequent itemsets of size 2 (we're interested in PAC -> Other rules)
    pair_counts = Counter()
    for transaction in transactions:
        items = list(transaction)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                # Only consider PAC -> Other rules
                if items[i].startswith('pac:') and items[j].startswith('other:'):
                    pair_counts[(items[i], items[j])] += 1
                elif items[j].startswith('pac:') and items[i].startswith('other:'):
                    pair_counts[(items[j], items[i])] += 1
    
    # Generate association rules
    rules = []
    for (antecedent, consequent), count in pair_counts.items():
        if count >= min_support_count:
            support = count / total_transactions
            confidence = count / item_counts[antecedent]
            
            if confidence >= min_confidence:
                # Calculate lift
                consequent_support = item_counts[consequent] / total_transactions
                lift = confidence / consequent_support if consequent_support > 0 else 0
                
                rules.append({
                    'antecedent': antecedent.replace('pac:', ''),
                    'consequent': consequent.replace('other:', ''),
                    'support': support,
                    'confidence': confidence,
                    'lift': lift,
                    'count': count,
                    'antecedent_count': item_counts[antecedent],
                    'consequent_count': item_counts[consequent]
                })
    
    # Sort rules by confidence, then by support
    rules.sort(key=lambda x: (x['confidence'], x['support']), reverse=True)
    
    return rules


def visualize_association_rules(rules: List[Dict], stats: Dict, output_dir: Path = None):
    """
    Create visualizations for association rules and co-change patterns.
    
    Args:
        rules: List of association rules
        stats: Statistics from calculate_extension_statistics
        output_dir: Directory to save visualizations
    """
    if output_dir is None:
        output_dir = Path(OUTPUTS_DIR).parent
    
    # Set style
    sns.set_style("whitegrid")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Top PAC extensions
    ax1 = plt.subplot(2, 3, 1)
    pac_exts = stats['pac_extensions'].most_common(10)
    if pac_exts:
        exts, counts = zip(*pac_exts)
        ax1.barh(exts, counts, color='lightcoral')
        ax1.set_xlabel('Number of Commits')
        ax1.set_title('Top 10 PAC File Extensions', fontsize=14, fontweight='bold')
        ax1.invert_yaxis()
    
    # 2. Top co-changed extensions
    ax2 = plt.subplot(2, 3, 2)
    other_exts = stats['other_extensions'].most_common(10)
    if other_exts:
        exts, counts = zip(*other_exts)
        ax2.barh(exts, counts, color='skyblue')
        ax2.set_xlabel('Number of Commits')
        ax2.set_title('Top 10 Co-Changed File Extensions', fontsize=14, fontweight='bold')
        ax2.invert_yaxis()
    
    # 3. Association rules scatter plot (Confidence vs Support)
    ax3 = plt.subplot(2, 3, 3)
    if rules:
        supports = [r['support'] for r in rules[:20]]
        confidences = [r['confidence'] for r in rules[:20]]
        lifts = [r['lift'] for r in rules[:20]]
        
        scatter = ax3.scatter(supports, confidences, c=lifts, s=100, cmap='viridis', alpha=0.6)
        ax3.set_xlabel('Support')
        ax3.set_ylabel('Confidence')
        ax3.set_title('Top 20 Association Rules', fontsize=14, fontweight='bold')
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('Lift')
    
    # 4. Top association rules by confidence
    ax4 = plt.subplot(2, 3, 4)
    if rules:
        top_rules = rules[:10]
        rule_labels = [f"{r['antecedent']} → {r['consequent']}" for r in top_rules]
        confidences = [r['confidence'] for r in top_rules]
        
        ax4.barh(rule_labels, confidences, color='lightgreen')
        ax4.set_xlabel('Confidence')
        ax4.set_title('Top 10 Rules by Confidence', fontsize=14, fontweight='bold')
        ax4.invert_yaxis()
        ax4.set_xlim(0, 1)
    
    # 5. Co-change heatmap for top extensions
    ax5 = plt.subplot(2, 3, 5)
    # Create co-occurrence matrix for top extensions
    top_pac = [ext for ext, _ in stats['pac_extensions'].most_common(5)]
    top_other = [ext for ext, _ in stats['other_extensions'].most_common(5)]
    
    cochange_matrix = np.zeros((len(top_pac), len(top_other)))
    for i, pac_ext in enumerate(top_pac):
        for j, other_ext in enumerate(top_other):
            cochange_matrix[i, j] = stats['cochange_pairs'].get((pac_ext, other_ext), 0)
    
    if cochange_matrix.any():
        sns.heatmap(cochange_matrix, xticklabels=top_other, yticklabels=top_pac,
                   annot=True, fmt='g', cmap='YlOrRd', ax=ax5)
        ax5.set_title('Co-Change Frequency Heatmap', fontsize=14, fontweight='bold')
        ax5.set_xlabel('Co-Changed Extensions')
        ax5.set_ylabel('PAC Extensions')
    
    # 6. Summary statistics
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    summary_text = f"""Association Rule Mining Summary
    
Total Commits with PAC Changes: {stats['total_commits']}
Commits with Co-Changes: {stats['commits_with_other_files']}
Co-Change Rate: {stats['commits_with_other_files']/stats['total_commits']*100:.1f}%

Unique PAC Extensions: {len(stats['pac_extensions'])}
Unique Co-Changed Extensions: {len(stats['other_extensions'])}
Total Association Rules: {len(rules)}

Top 3 Rules by Lift:"""
    
    if rules:
        top_lift_rules = sorted(rules, key=lambda x: x['lift'], reverse=True)[:3]
        for i, rule in enumerate(top_lift_rules, 1):
            summary_text += f"\n{i}. {rule['antecedent']} � {rule['consequent']}"
            summary_text += f"\n   Lift: {rule['lift']:.2f}, Conf: {rule['confidence']:.2f}"
    
    ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes, 
             fontsize=12, verticalalignment='top', fontfamily='monospace')
    
    plt.tight_layout()
    
    # Save the plot
    output_path = output_dir / 'pac_association_rules_analysis.pdf'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nAssociation rules visualization saved to: {output_path}")
    
    plt.show()


def print_association_rules_report(rules: List[Dict], stats: Dict, top_n: int = 20):
    """
    Print a detailed report of association rules.
    
    Args:
        rules: List of association rules
        stats: Statistics from calculate_extension_statistics
        top_n: Number of top rules to display
    """
    print("\n" + "="*80)
    print("ASSOCIATION RULE MINING REPORT")
    print("="*80)
    
    print(f"\nDataset Summary:")
    print(f"  Total commits with PAC changes: {stats['total_commits']}")
    print(f"  Commits with co-changes: {stats['commits_with_other_files']}")
    print(f"  Co-change rate: {stats['commits_with_other_files']/stats['total_commits']*100:.1f}%")
    print(f"  Unique PAC extensions: {len(stats['pac_extensions'])}")
    print(f"  Unique co-changed extensions: {len(stats['other_extensions'])}")
    
    print(f"\n\nTop PAC File Extensions:")
    print(f"  {'Extension':<15} {'Count':<10} {'Percentage':<10}")
    print("  " + "-"*35)
    for ext, count in stats['pac_extensions'].most_common(10):
        pct = count / stats['total_commits'] * 100
        print(f"  {ext:<15} {count:<10} {pct:<10.1f}%")
    
    print(f"\n\nTop Co-Changed File Extensions:")
    print(f"  {'Extension':<15} {'Count':<10} {'Percentage':<10}")
    print("  " + "-"*35)
    for ext, count in stats['other_extensions'].most_common(10):
        pct = count / stats['commits_with_other_files'] * 100 if stats['commits_with_other_files'] > 0 else 0
        print(f"  {ext:<15} {count:<10} {pct:<10.1f}%")
    
    print(f"\n\nTop {min(top_n, len(rules))} Association Rules:")
    print(f"  {'Rule':<30} {'Support':<10} {'Confidence':<12} {'Lift':<10} {'Count':<10}")
    print("  " + "-"*72)
    
    for i, rule in enumerate(rules[:top_n], 1):
        rule_str = f"{rule['antecedent']} � {rule['consequent']}"
        print(f"  {rule_str:<30} {rule['support']:<10.3f} {rule['confidence']:<12.3f} "
              f"{rule['lift']:<10.2f} {rule['count']:<10}")
    
    # Print interpretation guidelines
    print("\n\nInterpretation Guidelines:")
    print("  - Support: Proportion of commits containing both PAC and the co-changed extension")
    print("  - Confidence: Probability of the co-changed extension given the PAC extension")
    print("  - Lift > 1: Positive correlation (extensions appear together more than expected)")
    print("  - Lift = 1: No correlation (independent)")
    print("  - Lift < 1: Negative correlation (extensions appear together less than expected)")


def main():
    """Main function to perform association rule mining on co-changed files."""
    try:
        # Load data using functions from quantitative_analysis
        output_files = find_output_files(OUTPUTS_DIR)
        all_data = read_outputfiles(output_files)
        
        # Extract co-change information
        print("\nExtracting co-change patterns...")
        cochange_data = extract_cochanged_extensions(all_data)
        
        # Calculate statistics
        print("Calculating extension statistics...")
        stats = calculate_extension_statistics(cochange_data)
        
        # Mine association rules
        print("Mining association rules...")
        rules = mine_association_rules(cochange_data, min_support=0.005, min_confidence=0.1)
        
        # Print report
        print_association_rules_report(rules, stats)
        
        # Create visualizations
        print("\nCreating visualizations...")
        visualize_association_rules(rules, stats)
        
        return 0
        
    except Exception as e:
        logging.error(f"Error in association rule mining: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())