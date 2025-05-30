import pandas as pd
import pygit2
import os
from pathlib import Path


def load_repository_list(csv_path='repos.csv'):
    """
    CSVファイルからリポジトリ情報を読み込み、リストとして返す

    Args:
        csv_path (str): CSVファイルのパス（デフォルト: 'repos.csv'）

    Returns:
        list: リポジトリ情報の辞書リスト
              [{'repo_name': 'user/repo', 'sha': 'XXXX'}, ...]
              エラーの場合はNone
    """
    try:
        # CSVファイルを読み込み
        df = pd.read_csv(csv_path)

        # 必要な列が存在するかチェック
        required_columns = ['repo_name']#'sha'
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: Column '{col}' not found in CSV file")
                return None

        # 辞書のリストに変換
        repo_list = []
        for index, row in df.iterrows():
            repo_info = {
                'repo_name': row['repo_name'],
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