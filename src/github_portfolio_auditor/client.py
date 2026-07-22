"""GitHub client wrapper with caching."""

import os
from github import Github
from github import RateLimitExceededException
import requests_cache

# Enable caching for API calls
requests_cache.install_cache('github_cache', expire_after=3600)  # 1 hour

class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.github = Github(token)
        self.user = self.github.get_user()
    
    def get_repositories(self, username: str = None):
        """List all repositories for user (or authenticated)."""
        if username:
            user = self.github.get_user(username)
        else:
            user = self.user
        return list(user.get_repos())  # Handles pagination internally
    
    def get_repo_metadata(self, repo):
        """Extract key metadata."""
        languages = {k: v for k, v in repo.get_languages().items() if k != "url"}
        return {
            "name": repo.full_name,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "languages": languages,
            "topics": repo.get_topics(),
            "license": repo.license.name if repo.license else None,
            "last_commit": repo.pushed_at,
            "contributors_count": repo.get_contributors().totalCount,
            "releases_count": repo.get_releases().totalCount,
            "is_archived": repo.archived,
            "description": repo.description,
        }