"""
PeerView - Modern BGP Peering Dashboard
Version information and metadata
"""

__version__ = "1.1.1"
__title__ = "PeerView"
__description__ = (
    "Modern BGP peering dashboard for AS200132 with real-time session monitoring"
)
__author__ = "NetOne.nl"
__license__ = "MIT"
__copyright__ = "2024 NetOne.nl"

VERSION_INFO = {
    "version": __version__,
    "title": __title__,
    "description": __description__,
    "author": __author__,
    "license": __license__,
    "copyright": __copyright__,
    "build_date": "2026-03-15",
    "python_version": "3.11+",
    "framework": "Flask 3.1.3",
    "ui_framework": "Bootstrap 5.3.2",
}


def get_version():
    """Return the version string."""
    return __version__


def get_version_info():
    """Return complete version information."""
    return VERSION_INFO
