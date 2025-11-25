"""
Git service for interacting with Git repositories
"""
import git
from pathlib import Path
from typing import List, Optional
from ..utils.logger import setup_logger


class GitService:
    """Handles Git repository operations"""

    def __init__(self, repo_path: str):
        """
        Initialize Git service

        Args:
            repo_path: Path to the Git repository
        """
        self.logger = setup_logger('git')
        self.repo_path = Path(repo_path)

        try:
            self.repo = git.Repo(repo_path)
            self.logger.info(f"Initialized Git repository: {repo_path}")
        except git.InvalidGitRepositoryError:
            self.logger.error(f"Not a valid Git repository: {repo_path}")
            raise ValueError(f"Not a valid Git repository: {repo_path}")

    def get_current_commit(self) -> str:
        """Get the current HEAD commit hash"""
        try:
            commit_hash = self.repo.head.commit.hexsha
            self.logger.info(f"Current commit: {commit_hash}")
            return commit_hash
        except Exception as e:
            self.logger.error(f"Error getting current commit: {e}")
            raise

    def get_commit_message(self, commit_hash: str = None) -> str:
        """Get commit message for a specific commit or HEAD"""
        try:
            if commit_hash:
                commit = self.repo.commit(commit_hash)
            else:
                commit = self.repo.head.commit
            return commit.message.strip()
        except Exception as e:
            self.logger.error(f"Error getting commit message: {e}")
            return ""

    def get_changed_files(self, from_commit: str, to_commit: str = None) -> List[str]:
        """
        Get list of files changed between two commits

        Args:
            from_commit: Starting commit hash
            to_commit: Ending commit hash (default: HEAD)

        Returns:
            List of changed file paths relative to repo root
        """
        try:
            if to_commit is None:
                to_commit = self.repo.head.commit.hexsha

            from_commit_obj = self.repo.commit(from_commit)
            to_commit_obj = self.repo.commit(to_commit)

            # Get diff between commits
            diff = from_commit_obj.diff(to_commit_obj)

            changed_files = []
            for item in diff:
                # a_path is the old path, b_path is the new path
                # For new files, a_path is None
                # For deleted files, b_path is None
                if item.b_path:  # File exists in the new commit
                    changed_files.append(item.b_path)
                elif item.a_path:  # File was deleted
                    # We don't need to push deleted files
                    pass

            self.logger.info(f"Found {len(changed_files)} changed files between {from_commit[:7]} and {to_commit[:7]}")
            return changed_files

        except Exception as e:
            self.logger.error(f"Error getting changed files: {e}")
            raise

    def get_all_tracked_files(self) -> List[str]:
        """
        Get all tracked files in the repository

        Returns:
            List of all tracked file paths
        """
        try:
            # Get all files tracked by git
            tracked_files = []
            for item in self.repo.head.commit.tree.traverse():
                if item.type == 'blob':  # It's a file
                    tracked_files.append(item.path)

            self.logger.info(f"Found {len(tracked_files)} tracked files")
            return tracked_files

        except Exception as e:
            self.logger.error(f"Error getting tracked files: {e}")
            raise

    def file_exists_in_commit(self, file_path: str, commit_hash: str = None) -> bool:
        """
        Check if a file exists in a specific commit

        Args:
            file_path: Path to the file (relative to repo root)
            commit_hash: Commit hash (default: HEAD)

        Returns:
            bool: True if file exists
        """
        try:
            if commit_hash is None:
                commit = self.repo.head.commit
            else:
                commit = self.repo.commit(commit_hash)

            try:
                commit.tree / file_path
                return True
            except KeyError:
                return False

        except Exception as e:
            self.logger.error(f"Error checking file existence: {e}")
            return False

    def get_repo_root(self) -> str:
        """Get the root directory of the repository"""
        return str(self.repo_path)

    def is_dirty(self) -> bool:
        """Check if the repository has uncommitted changes"""
        return self.repo.is_dirty()

    def get_untracked_files(self) -> List[str]:
        """Get list of untracked files"""
        return self.repo.untracked_files

    def get_recent_commits(self, count: int = 10) -> List[dict]:
        """
        Get the most recent commits from the repository

        Args:
            count: Number of commits to retrieve (default 10)

        Returns:
            List of dicts with commit info: {hash, short_hash, message, author, date}
        """
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=count):
                commits.append({
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:7],
                    'message': commit.message.strip().split('\n')[0],  # First line only
                    'author': str(commit.author),
                    'date': commit.committed_datetime.strftime('%Y-%m-%d %H:%M')
                })
            self.logger.info(f"Retrieved {len(commits)} recent commits")
            return commits
        except Exception as e:
            self.logger.error(f"Error getting recent commits: {e}")
            return []

    def get_files_in_commits(self, commit_hashes: List[str]) -> List[str]:
        """
        Get all files that were changed in the specified commits

        Args:
            commit_hashes: List of commit hashes to get files from

        Returns:
            List of unique file paths that exist in the current tree
        """
        try:
            all_files = set()

            for commit_hash in commit_hashes:
                commit = self.repo.commit(commit_hash)

                # Get files changed in this commit by comparing to parent
                if commit.parents:
                    # Compare with first parent
                    diff = commit.parents[0].diff(commit)
                else:
                    # First commit - all files are new
                    for item in commit.tree.traverse():
                        if item.type == 'blob':
                            all_files.add(item.path)
                    continue

                for item in diff:
                    # Include files that exist in the commit (not deleted)
                    if item.b_path:
                        all_files.add(item.b_path)

            # Filter to only include files that exist in current tree
            current_files = set(self.get_all_tracked_files())
            existing_files = [f for f in all_files if f in current_files]

            self.logger.info(f"Found {len(existing_files)} unique files from {len(commit_hashes)} commits")
            return sorted(existing_files)

        except Exception as e:
            self.logger.error(f"Error getting files from commits: {e}")
            raise
