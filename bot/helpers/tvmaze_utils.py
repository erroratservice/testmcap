"""
TVMaze API integration for fetching series and movie data with caching.
"""

import logging
from pytvmaze.tvmaze import TVMaze as PyTVMaze, ShowNotFound
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

class TVMaze:
    """A helper class for interacting with the TVMaze API with MongoDB caching."""

    def __init__(self):
        self.api = PyTVMaze()

    def search_show(self, title):
        """
        Search for a show by its title, using a cache to avoid redundant API calls.
        """
        cached_result = MongoDB.get_tvmaze_cache(title)
        if cached_result:
            LOGGER.info(f"Found '{title}' in TVMaze show cache.")
            return cached_result.get('data')

        LOGGER.info(f"'{title}' not in cache. Querying TVMaze API for the show.")
        try:
            show = self.api.get_show(show_name=title, embed='episodes')
            if show:
                show_data = vars(show)
                # Cache the main show data
                MongoDB.set_tvmaze_cache(title, show_data)
                # Separately cache the episodes
                if hasattr(show, 'episodes'):
                    episodes_data = [vars(ep) for ep in show.episodes]
                    MongoDB.set_tvmaze_episodes_cache(show.maze_id, episodes_data)
                return show_data
        except ShowNotFound:
            LOGGER.warning(f"Show '{title}' not found on TVMaze.")
        except Exception as e:
            LOGGER.error(f"TVMaze API error while searching for '{title}': {e}")

        return None

    def get_episodes(self, maze_id):
        """
        Get a list of all episodes for a given show, using a cache.
        """
        cached_episodes = MongoDB.get_tvmaze_episodes_cache(maze_id)
        if cached_episodes:
            LOGGER.info(f"Found episodes for Maze ID {maze_id} in cache.")
            return cached_episodes.get('episodes')

        LOGGER.info(f"Episodes for Maze ID {maze_id} not in cache. Querying TVMaze API.")
        try:
            show = self.api.get_show(maze_id=maze_id, embed='episodes')
            if hasattr(show, 'episodes'):
                episodes_data = [vars(ep) for ep in show.episodes]
                MongoDB.set_tvmaze_episodes_cache(show.maze_id, episodes_data)
                return episodes_data
        except Exception as e:
            LOGGER.error(f"Error fetching episodes for Maze ID {maze_id}: {e}")

        return []

# Initialize a single instance to be used across the application
tvmaze_api = TVMaze()
