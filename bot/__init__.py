"""
Clean Media Indexing Bot
Built for MediaInfo extraction and channel organization
"""

__version__ = "1.0.0"
__author__ = "Media Manager Bot"

# Package initialization
from .core.config import Config
from .core.client import TgClient

__all__ = ['Config', 'TgClient']
