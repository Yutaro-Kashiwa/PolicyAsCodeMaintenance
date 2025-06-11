from typing import List, Dict


def print_summary(results: List[Dict]) -> None:
    """Print summary of analysis results.

    Args:
        results: List of analysis results from repositories
    """
    if not results:
        print("\nNo analysis results to display")
        return

    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    total_repos = len(results)
    total_commits = sum(r['total_commits'] for r in results)
    total_pac_changes = sum(r['pac_changes_count'] for r in results)

    print(f"\nRepositories analyzed: {total_repos}")
    print(f"Total commits: {total_commits}")
    print(f"Total PAC changes: {total_pac_changes}")

    if total_commits > 0:
        print(f"Overall PAC change ratio: {total_pac_changes / total_commits:.2%}")

    print("\nPer-repository results:")
    print("-" * 80)
    print(f"{'Repository':<40} {'PAC Changes':<15} {'Total Commits':<15} {'Ratio':<10}")
    print("-" * 80)

    for result in sorted(results, key=lambda x: x['pac_change_ratio'], reverse=True):
        print(
            f"{result['repository_name']:<40} "
            f"{result['pac_changes_count']:<15} "
            f"{result['total_commits']:<15} "
            f"{result['pac_change_ratio']:<10.2%}"
        )
