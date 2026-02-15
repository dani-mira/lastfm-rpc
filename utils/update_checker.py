import requests
import logging
from packaging import version
import constants.project as project

logger = logging.getLogger('app')

def check_for_updates():
    """
    Checks GitHub for the latest release and compares it with the current VERSION.
    Returns a tuple (is_available, latest_version_name, html_url)
    """
    try:
        response = requests.get(project.GITHUB_RELEASES_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get('tag_name', '').replace('v', '')
            current_version = project.VERSION.replace('v', '')
            
            if version.parse(latest_version) > version.parse(current_version):
                logger.info(f"New update available: {latest_version} (Current: {project.VERSION})")
                return True, data.get('tag_name'), data.get('html_url')
            else:
                logger.info(f"App is up to date: {project.VERSION}")
        else:
            logger.warning(f"Failed to check for updates: GitHub API returned {response.status_code}")
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        
    return False, None, None
