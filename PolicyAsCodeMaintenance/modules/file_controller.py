import pandas as pd
import pygit2
import os
from pathlib import Path


def load_repository_list(csv_path='repos.csv'):
    """
    Load repository information from CSV file and return as a list

    Args:
        csv_path (str): Path to CSV file (default: 'repos.csv')

    Returns:
        list: List of dictionaries containing repository information
              [{'full_name': 'user/repo', 'sha': 'XXXX'}, ...]
              Returns None in case of error
    """
    try:
        # Load CSV file
        df = pd.read_csv(csv_path)

        # Check if required columns exist
        required_columns = ['full_name']#'sha'
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: Column '{col}' not found in CSV file")
                return None

        # Convert to list of dictionaries
        repo_list = []
        for index, row in df.iterrows():
            repo_info = {
                'full_name': row['full_name'],
                'id': row['id'],
                # 'sha': row['sha']
            }
            repo_list.append(repo_info)

        print(f"Loaded {len(repo_list)} repositories from {csv_path}")
        return repo_list

    except FileNotFoundError:
        print(f"CSV file '{csv_path}' not found")
        raise
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        raise





def list_directories(path):
    try:
        # Get a list of directories within the specified path
        directories = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
        return directories
    except FileNotFoundError:
        print("File Not Found")
    except PermissionError:
        print("Permission denied to access the specified path.")