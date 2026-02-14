import logging
import sys
import os
from typing import Tuple, Dict

import yaml

def load_yaml_file(file_path: str) -> dict:
    """
    Load a YAML file and return its contents as a dictionary.
    
    :param file_path: Path to the YAML file.
    :return: Contents of the YAML file as a dictionary.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError:
        logging.error(f"Error loading YAML file: {file_path}")
        sys.exit(1)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        sys.exit(1)

def load_config(config_path: str = "config.yaml") -> Tuple[str, str, str, str]:
    """
    Load the configuration file and return the required values.
    
    :param config_path: Path to the configuration YAML file.
    :return: A tuple containing username, API key, API secret, and app language.
    """
    config = load_yaml_file(config_path)
    try:
        username = config.get('USER', {}).get('USERNAME')
        api_key = config.get('API', {}).get('KEY')
        api_secret = config.get('API', {}).get('SECRET')
        app_lang = config.get('APP', {}).get('LANG', 'en-US')

        if not all([username, api_key, api_secret]):
            logging.error("Configuration incomplete. Please check USERNAME, API KEY, and API SECRET in config.yaml.")
            sys.exit(1)
            
        logging.info("Configuration loaded successfully.")
        return username, api_key, api_secret, app_lang
    except Exception as e:
        logging.error(f"Error validating configuration: {e}")
        sys.exit(1)

def load_translations(app_lang: str, translations_dir: str) -> Dict[str, str]:
    """
    Load the translations from a specific file based on the language code.
    
    :param app_lang: Language code for the translations (e.g., 'en-US', 'tr-TR').
    :param translations_dir: Path to the translations directory.
    :return: A dictionary containing translations.
    """
    file_path = os.path.join(translations_dir, f"{app_lang}.yaml")
    
    try:
        translations = load_yaml_file(file_path)
        logging.info(f"Translations for '{app_lang}' loaded successfully from {file_path}")
        return translations
    except Exception:
        logging.error(f"Could not load translations for language: {app_lang}")
        sys.exit(1)
