from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class PluginManifest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = []

class BaseSEOPlugin(ABC):
    """
    Abstract base class for all SEO plugins.
    Ensures a consistent interface and versioning.
    """
    
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin logic.
        Args:
            context: A dictionary containing the site URL, crawled pages, etc.
        Returns:
            A dictionary containing findings, actions, and scores.
        """
        pass

    def validate_dependencies(self, installed_plugins: List[str]) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in self.manifest.dependencies:
            if dep not in installed_plugins:
                return False
        return True
