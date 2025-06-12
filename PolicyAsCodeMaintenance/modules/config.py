"""Configuration settings for PolicyAsCodeMaintenance."""
import os

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(PARENT_DIR)
REPOS_DIR = os.path.join(ROOT_DIR, 'repos')
INPUTS_DIR = os.path.join(ROOT_DIR, 'inputs')
OUTPUTS_DIR = os.path.join(ROOT_DIR, 'outputs')

# CSV file paths
REPOS_CSV_PATH = os.path.join(INPUTS_DIR, 'repos-full.csv')
REPOS_TEST_CSV_PATH = os.path.join(INPUTS_DIR, 'repos-full-test.csv')
PAC_FILE_NAMES_CSV_PATH = os.path.join(INPUTS_DIR, 'pac_filenames.csv')

# Default settings
DEFAULT_REPOS_CSV = REPOS_CSV_PATH
USE_TEST_MODE = False  # Set to True to use test dataset with single repository