#!/usr/bin/env python3
# Modified: 2026-02-07T17:00:00Z | Author: COPILOT | Change: GitHub achievement tracking and feedback loop integration
"""
GitHub Achievements Tracker - Track and guide users toward GitHub badges.

Integrates with the SLATE learning system to:
- Track progress toward GitHub achievements (Pull Shark, YOLO, Quickdraw, etc.)
- Create learning paths that guide developers to earn badges
- Provide feedback on contribution patterns
- Celebrate milestone achievements

GitHub Achievement Reference:
- Pull Shark: Open PRs that get merged (Bronze/Silver/Gold/Platinum based on count)
- YOLO: Merge PR without code review
- Quickdraw: Close issue/PR within 5 minutes of opening
- Galaxy Brain: Get discussion answers marked as accepted
- Pair Extraordinaire: Co-author commits
- Starstruck: Create repo that gets starred (16/128/512/4096)
- Arctic Code Vault Contributor: Contributed to 2020 GitHub Archive
- Mars 2020 Contributor: Contributed to Mars Helicopter mission repos
- Public Sponsor: Sponsor open source work
"""

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger("slate.github_achievements")


# ── GitHub Achievement Definitions ──────────────────────────────────────────


class AchievementTier(str, Enum):
    """Tier levels for multi-tier achievements."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class AchievementStatus(str, Enum):
    """Status of achievement progress."""
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    EARNED = "earned"


@dataclass
class GitHubAchievement:
    """Definition of a GitHub achievement."""
    id: str
    name: str
    description: str
    icon: str
    category: str  # contributions, community, special
    tiers: Optional[Dict[str, int]] = None  # tier: threshold
    single_threshold: Optional[int] = None
    how_to_earn: str = ""
    learning_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "tiers": self.tiers,
            "single_threshold": self.single_threshold,
            "how_to_earn": self.how_to_earn,
        }


@dataclass
class AchievementProgress:
    """User's progress toward an achievement."""
    achievement_id: str
    current_count: int = 0
    current_tier: Optional[AchievementTier] = None
    status: AchievementStatus = AchievementStatus.LOCKED
    earned_at: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "achievement_id": self.achievement_id,
            "current_count": self.current_count,
            "current_tier": self.current_tier.value if self.current_tier else None,
            "status": self.status.value,
            "earned_at": self.earned_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AchievementProgress":
        tier = data.get("current_tier")
        status = data.get("status", "locked")
        return cls(
            achievement_id=data["achievement_id"],
            current_count=data.get("current_count", 0),
            current_tier=AchievementTier(tier) if tier else None,
            status=AchievementStatus(status),
            earned_at=data.get("earned_at"),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )


# ── Achievement Definitions ─────────────────────────────────────────────────


GITHUB_ACHIEVEMENTS: Dict[str, GitHubAchievement] = {
    # Contribution Achievements
    "pull_shark": GitHubAchievement(
        id="pull_shark",
        name="Pull Shark",
        description="Open pull requests that get merged",
        icon="🦈",
        category="contributions",
        tiers={
            "bronze": 2,
            "silver": 16,
            "gold": 128,
            "platinum": 1024,
        },
        how_to_earn="Open pull requests and get them merged into the default branch",
        learning_steps=[
            "Create a feature branch",
            "Make meaningful changes",
            "Write clear PR descriptions",
            "Address review feedback",
            "Get your PR merged",
        ],
    ),
    "yolo": GitHubAchievement(
        id="yolo",
        name="YOLO",
        description="Merge a pull request without code review",
        icon="🤠",
        category="contributions",
        single_threshold=1,
        how_to_earn="Merge your own PR without requesting or receiving a code review",
        learning_steps=[
            "Create a PR for a small fix",
            "Ensure you have merge permissions",
            "Merge directly without review",
        ],
    ),
    "quickdraw": GitHubAchievement(
        id="quickdraw",
        name="Quickdraw",
        description="Close an issue or PR within 5 minutes of opening",
        icon="🔫",
        category="contributions",
        single_threshold=1,
        how_to_earn="Close an issue or PR within 5 minutes of it being opened",
        learning_steps=[
            "Identify a quick-fix issue",
            "Have the solution ready",
            "Open and close rapidly",
        ],
    ),
    "starstruck": GitHubAchievement(
        id="starstruck",
        name="Starstruck",
        description="Create a repository that gets starred",
        icon="⭐",
        category="community",
        tiers={
            "bronze": 16,
            "silver": 128,
            "gold": 512,
            "platinum": 4096,
        },
        how_to_earn="Create repositories that others find valuable and star",
        learning_steps=[
            "Build something useful",
            "Write great documentation",
            "Add a compelling README",
            "Share with the community",
            "Maintain and improve",
        ],
    ),
    "galaxy_brain": GitHubAchievement(
        id="galaxy_brain",
        name="Galaxy Brain",
        description="Get discussion answers marked as accepted",
        icon="🧠",
        category="community",
        tiers={
            "bronze": 2,
            "silver": 8,
            "gold": 16,
            "platinum": 32,
        },
        how_to_earn="Answer GitHub Discussions and have your answers marked as accepted",
        learning_steps=[
            "Browse GitHub Discussions",
            "Find questions you can answer",
            "Provide detailed, helpful responses",
            "Follow up if needed",
        ],
    ),
    "pair_extraordinaire": GitHubAchievement(
        id="pair_extraordinaire",
        name="Pair Extraordinaire",
        description="Co-author commits with others",
        icon="👥",
        category="contributions",
        tiers={
            "bronze": 1,
            "silver": 10,
            "gold": 24,
            "platinum": 48,
        },
        how_to_earn="Create commits with co-authors using 'Co-authored-by' trailer",
        learning_steps=[
            "Work with a collaborator",
            "Add 'Co-authored-by: name <email>' to commit messages",
            "Push co-authored commits",
        ],
    ),
    "public_sponsor": GitHubAchievement(
        id="public_sponsor",
        name="Public Sponsor",
        description="Sponsor open source maintainers",
        icon="💖",
        category="community",
        single_threshold=1,
        how_to_earn="Publicly sponsor an open source developer or project",
        learning_steps=[
            "Find a project you appreciate",
            "Visit their GitHub Sponsors page",
            "Choose a sponsorship tier",
            "Make your sponsorship public",
        ],
    ),

    # Workflow Achievements (SLATE-specific extensions)
    "ci_master": GitHubAchievement(
        id="ci_master",
        name="CI Master",
        description="Have 10 successful CI workflow runs",
        icon="✅",
        category="workflows",
        tiers={
            "bronze": 10,
            "silver": 50,
            "gold": 200,
            "platinum": 1000,
        },
        how_to_earn="Run GitHub Actions workflows that complete successfully",
        learning_steps=[
            "Set up GitHub Actions",
            "Configure CI workflow",
            "Fix failing tests",
            "Maintain green builds",
        ],
    ),
    "issue_closer": GitHubAchievement(
        id="issue_closer",
        name="Issue Closer",
        description="Close issues with merged PRs",
        icon="🎯",
        category="contributions",
        tiers={
            "bronze": 5,
            "silver": 25,
            "gold": 100,
            "platinum": 500,
        },
        how_to_earn="Close issues by merging PRs that reference them (Closes #123)",
        learning_steps=[
            "Find an open issue",
            "Create a branch to fix it",
            "Reference the issue in your PR",
            "Get the PR merged",
        ],
    ),
    "code_reviewer": GitHubAchievement(
        id="code_reviewer",
        name="Code Reviewer",
        description="Review pull requests from others",
        icon="👀",
        category="contributions",
        tiers={
            "bronze": 5,
            "silver": 25,
            "gold": 100,
            "platinum": 500,
        },
        how_to_earn="Leave reviews on pull requests submitted by others",
        learning_steps=[
            "Browse open PRs",
            "Read the changes carefully",
            "Leave constructive feedback",
            "Approve or request changes",
        ],
    ),
    "release_maker": GitHubAchievement(
        id="release_maker",
        name="Release Maker",
        description="Create GitHub releases",
        icon="📦",
        category="contributions",
        tiers={
            "bronze": 1,
            "silver": 5,
            "gold": 20,
            "platinum": 100,
        },
        how_to_earn="Create tagged releases for your repositories",
        learning_steps=[
            "Tag your code (git tag)",
            "Push tags to GitHub",
            "Create a release from the tag",
            "Write release notes",
        ],
    ),
}


# ── Learning Path for GitHub Mastery ────────────────────────────────────────


GITHUB_LEARNING_STEPS = [
    {
        "id": "gh_intro",
        "title": "GitHub Contribution Fundamentals",
        "description": "Learn the basics of contributing on GitHub and earning achievements",
        "category": "concept",
        "xp_reward": 25,
        "hints": [
            "GitHub awards achievements for various contributions",
            "Achievements have tiers: Bronze, Silver, Gold, Platinum",
            "Check your profile to see earned achievements",
        ],
    },
    {
        "id": "gh_first_pr",
        "title": "Create Your First Pull Request",
        "description": "Open a PR and start your journey to Pull Shark",
        "category": "hands_on",
        "xp_reward": 50,
        "achievement_trigger": "first_pr",
        "action_command": "gh pr create --fill",
        "hints": [
            "Use 'gh pr create' or the GitHub web interface",
            "Write a clear title and description",
            "Reference any related issues",
        ],
    },
    {
        "id": "gh_merge_pr",
        "title": "Get Your PR Merged",
        "description": "Work with reviewers to get your PR merged",
        "category": "hands_on",
        "xp_reward": 75,
        "hints": [
            "Address review feedback promptly",
            "Keep your branch up to date",
            "Squash commits if needed",
        ],
    },
    {
        "id": "gh_co_author",
        "title": "Pair Programming Achievement",
        "description": "Create a co-authored commit for Pair Extraordinaire",
        "category": "hands_on",
        "xp_reward": 50,
        "achievement_trigger": "pair_extraordinaire",
        "hints": [
            "Add 'Co-authored-by: Name <email>' to commit messages",
            "SLATE uses: Co-Authored-By: Claude <noreply@anthropic.com>",
            "Both authors get credit for the commit",
        ],
    },
    {
        "id": "gh_review_pr",
        "title": "Review a Pull Request",
        "description": "Start earning Code Reviewer by reviewing others' work",
        "category": "hands_on",
        "xp_reward": 50,
        "achievement_trigger": "code_reviewer",
        "action_command": "gh pr list --state open",
        "hints": [
            "Look for PRs needing review",
            "Check code quality and tests",
            "Leave constructive feedback",
        ],
    },
    {
        "id": "gh_close_issue",
        "title": "Close an Issue with a PR",
        "description": "Reference and close issues automatically",
        "category": "hands_on",
        "xp_reward": 75,
        "achievement_trigger": "issue_closer",
        "hints": [
            "Use 'Closes #123' or 'Fixes #123' in PR description",
            "The issue closes automatically when PR is merged",
            "Multiple issues can be closed in one PR",
        ],
    },
    {
        "id": "gh_create_release",
        "title": "Create a GitHub Release",
        "description": "Package and release your work for Release Maker",
        "category": "hands_on",
        "xp_reward": 100,
        "achievement_trigger": "release_maker",
        "action_command": "gh release create",
        "hints": [
            "Tag your code with semantic versioning",
            "Write comprehensive release notes",
            "Attach build artifacts if applicable",
        ],
    },
    {
        "id": "gh_ci_setup",
        "title": "Set Up CI/CD Workflows",
        "description": "Configure GitHub Actions for CI Master",
        "category": "hands_on",
        "xp_reward": 100,
        "achievement_trigger": "ci_master",
        "hints": [
            "Create .github/workflows/*.yml files",
            "Set up automated testing",
            "Configure build and deployment",
        ],
    },
    {
        "id": "gh_discussions",
        "title": "Engage in GitHub Discussions",
        "description": "Answer questions to earn Galaxy Brain",
        "category": "hands_on",
        "xp_reward": 75,
        "achievement_trigger": "galaxy_brain",
        "hints": [
            "Find discussions in repositories you know well",
            "Provide detailed, helpful answers",
            "Follow up to ensure the solution works",
        ],
    },
    {
        "id": "gh_sponsor",
        "title": "Support Open Source",
        "description": "Become a Public Sponsor of open source",
        "category": "explore",
        "xp_reward": 100,
        "achievement_trigger": "public_sponsor",
        "hints": [
            "Find a project you use and appreciate",
            "Check if they have GitHub Sponsors enabled",
            "Choose a tier that works for you",
        ],
    },
]


# ── GitHub Achievement Tracker ──────────────────────────────────────────────


class GitHubAchievementTracker:
    """
    Tracks progress toward GitHub achievements.

    Integrates with GitHub CLI to fetch contribution data and
    calculate progress toward various achievements.
    """

    STATE_FILE = ".slate_identity/github_achievements.json"

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.state_file = self.workspace / self.STATE_FILE
        self._progress: Dict[str, AchievementProgress] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted achievement progress."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._progress = {
                        k: AchievementProgress.from_dict(v)
                        for k, v in data.get("progress", {}).items()
                    }
                    logger.info(f"Loaded {len(self._progress)} achievement progress records")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load achievement state: {e}")

    def _save_state(self) -> None:
        """Persist achievement progress."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "progress": {k: v.to_dict() for k, v in self._progress.items()},
            "last_updated": datetime.now().isoformat(),
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save achievement state: {e}")

    async def refresh_from_github(self) -> Dict[str, Any]:
        """Fetch current stats from GitHub and update progress."""
        stats = await self._fetch_github_stats()

        if not stats.get("success"):
            return {"success": False, "error": stats.get("error", "Unknown error")}

        updates = []

        # Update Pull Shark progress
        merged_prs = stats.get("merged_prs", 0)
        if merged_prs > 0:
            update = self._update_progress("pull_shark", merged_prs)
            if update:
                updates.append(update)

        # Update CI Master progress
        successful_runs = stats.get("successful_workflow_runs", 0)
        if successful_runs > 0:
            update = self._update_progress("ci_master", successful_runs)
            if update:
                updates.append(update)

        # Update Issue Closer progress
        closed_issues = stats.get("issues_closed_by_prs", 0)
        if closed_issues > 0:
            update = self._update_progress("issue_closer", closed_issues)
            if update:
                updates.append(update)

        # Update Code Reviewer progress
        reviews = stats.get("pr_reviews", 0)
        if reviews > 0:
            update = self._update_progress("code_reviewer", reviews)
            if update:
                updates.append(update)

        # Update Release Maker progress
        releases = stats.get("releases_created", 0)
        if releases > 0:
            update = self._update_progress("release_maker", releases)
            if update:
                updates.append(update)

        # Check for co-authored commits (Pair Extraordinaire)
        coauthored = stats.get("coauthored_commits", 0)
        if coauthored > 0:
            update = self._update_progress("pair_extraordinaire", coauthored)
            if update:
                updates.append(update)

        self._save_state()

        return {
            "success": True,
            "stats": stats,
            "updates": updates,
            "progress": {k: v.to_dict() for k, v in self._progress.items()},
        }

    def _update_progress(
        self,
        achievement_id: str,
        count: int,
    ) -> Optional[Dict[str, Any]]:
        """Update progress for an achievement and return any tier changes."""
        achievement = GITHUB_ACHIEVEMENTS.get(achievement_id)
        if not achievement:
            return None

        progress = self._progress.get(achievement_id)
        if not progress:
            progress = AchievementProgress(achievement_id=achievement_id)
            self._progress[achievement_id] = progress

        old_tier = progress.current_tier
        old_count = progress.current_count
        progress.current_count = count
        progress.last_updated = datetime.now().isoformat()

        # Calculate new tier
        new_tier = None
        if achievement.tiers:
            for tier_name, threshold in sorted(
                achievement.tiers.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                if count >= threshold:
                    new_tier = AchievementTier(tier_name)
                    break

            if new_tier:
                progress.current_tier = new_tier
                if progress.status != AchievementStatus.EARNED:
                    progress.status = AchievementStatus.IN_PROGRESS

        elif achievement.single_threshold:
            if count >= achievement.single_threshold:
                progress.status = AchievementStatus.EARNED
                progress.earned_at = datetime.now().isoformat()

        # Check for tier upgrade
        if new_tier and new_tier != old_tier:
            return {
                "achievement_id": achievement_id,
                "achievement_name": achievement.name,
                "old_tier": old_tier.value if old_tier else None,
                "new_tier": new_tier.value,
                "count": count,
                "message": f"Upgraded to {new_tier.value.title()} tier!",
            }

        return None

    async def _fetch_github_stats(self) -> Dict[str, Any]:
        """Fetch contribution stats from GitHub CLI."""
        try:
            # Get authenticated user
            user_result = subprocess.run(
                ["gh", "api", "user", "-q", ".login"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if user_result.returncode != 0:
                return {"success": False, "error": "Not authenticated with GitHub"}

            username = user_result.stdout.strip()

            # Get merged PRs count
            pr_result = subprocess.run(
                ["gh", "pr", "list", "--author", username, "--state", "merged", "--json", "number", "-q", "length"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            merged_prs = int(pr_result.stdout.strip()) if pr_result.returncode == 0 and pr_result.stdout.strip() else 0

            # Get successful workflow runs (last 30 days)
            runs_result = subprocess.run(
                ["gh", "run", "list", "--status", "success", "--json", "databaseId", "-q", "length"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            successful_runs = int(runs_result.stdout.strip()) if runs_result.returncode == 0 and runs_result.stdout.strip() else 0

            # Get releases created
            releases_result = subprocess.run(
                ["gh", "release", "list", "--json", "tagName", "-q", "length"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            releases = int(releases_result.stdout.strip()) if releases_result.returncode == 0 and releases_result.stdout.strip() else 0

            # Check for co-authored commits in recent history
            coauthor_result = subprocess.run(
                ["git", "log", "--oneline", "-100", "--grep=Co-authored-by"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace,
            )
            coauthored = len(coauthor_result.stdout.strip().split("\n")) if coauthor_result.returncode == 0 and coauthor_result.stdout.strip() else 0

            return {
                "success": True,
                "username": username,
                "merged_prs": merged_prs,
                "successful_workflow_runs": successful_runs,
                "releases_created": releases,
                "coauthored_commits": coauthored,
                "fetched_at": datetime.now().isoformat(),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "GitHub API timeout"}
        except Exception as e:
            logger.error(f"Failed to fetch GitHub stats: {e}")
            return {"success": False, "error": str(e)}

    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """Get all achievements with current progress."""
        result = []
        for ach_id, achievement in GITHUB_ACHIEVEMENTS.items():
            progress = self._progress.get(ach_id)
            result.append({
                **achievement.to_dict(),
                "progress": progress.to_dict() if progress else None,
                "next_tier": self._get_next_tier(achievement, progress),
            })
        return result

    def _get_next_tier(
        self,
        achievement: GitHubAchievement,
        progress: Optional[AchievementProgress],
    ) -> Optional[Dict[str, Any]]:
        """Calculate progress to next tier."""
        if not achievement.tiers or not progress:
            if achievement.single_threshold and progress:
                remaining = max(0, achievement.single_threshold - progress.current_count)
                return {
                    "tier": "earned",
                    "threshold": achievement.single_threshold,
                    "remaining": remaining,
                    "progress_percent": min(100, int(progress.current_count / achievement.single_threshold * 100)),
                }
            return None

        current_count = progress.current_count if progress else 0

        for tier_name, threshold in sorted(achievement.tiers.items(), key=lambda x: x[1]):
            if current_count < threshold:
                return {
                    "tier": tier_name,
                    "threshold": threshold,
                    "remaining": threshold - current_count,
                    "progress_percent": int(current_count / threshold * 100),
                }

        return None  # Already at max tier

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get personalized recommendations for which achievements to pursue."""
        recommendations = []

        for ach_id, achievement in GITHUB_ACHIEVEMENTS.items():
            progress = self._progress.get(ach_id)
            next_tier = self._get_next_tier(achievement, progress)

            if next_tier and next_tier.get("progress_percent", 0) >= 50:
                # Close to next tier - high priority
                recommendations.append({
                    "achievement": achievement.to_dict(),
                    "priority": "high",
                    "reason": f"Only {next_tier['remaining']} more to reach {next_tier['tier']} tier!",
                    "steps": achievement.learning_steps[:3],
                })
            elif progress and progress.status == AchievementStatus.IN_PROGRESS:
                # Already making progress
                recommendations.append({
                    "achievement": achievement.to_dict(),
                    "priority": "medium",
                    "reason": "Continue your progress",
                    "steps": achievement.learning_steps[:3],
                })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return recommendations[:5]  # Top 5 recommendations

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive achievement status."""
        earned_count = sum(
            1 for p in self._progress.values()
            if p.status == AchievementStatus.EARNED
        )
        in_progress_count = sum(
            1 for p in self._progress.values()
            if p.status == AchievementStatus.IN_PROGRESS
        )

        return {
            "total_achievements": len(GITHUB_ACHIEVEMENTS),
            "earned": earned_count,
            "in_progress": in_progress_count,
            "locked": len(GITHUB_ACHIEVEMENTS) - earned_count - in_progress_count,
            "progress": {k: v.to_dict() for k, v in self._progress.items()},
            "recommendations": self.get_recommendations()[:3],
        }


# ── Factory Function ────────────────────────────────────────────────────────


_tracker_instance: Optional[GitHubAchievementTracker] = None


def get_github_tracker(workspace: Optional[Path] = None) -> GitHubAchievementTracker:
    """Get or create the singleton tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = GitHubAchievementTracker(workspace)
    return _tracker_instance


def reset_github_tracker() -> None:
    """Reset the tracker instance."""
    global _tracker_instance
    _tracker_instance = None


# ── CLI ─────────────────────────────────────────────────────────────────────


async def main_async():
    """Async CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE GitHub Achievement Tracker"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show achievement status",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh stats from GitHub",
    )
    parser.add_argument(
        "--recommendations",
        action="store_true",
        help="Get achievement recommendations",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all achievements",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    args = parser.parse_args()

    tracker = get_github_tracker()

    if args.refresh:
        print("Fetching GitHub stats...")
        result = await tracker.refresh_from_github()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                stats = result.get("stats", {})
                print(f"\n  GitHub Stats for @{stats.get('username', 'unknown')}")
                print("  " + "=" * 40)
                print(f"  Merged PRs:       {stats.get('merged_prs', 0)}")
                print(f"  CI Runs (success): {stats.get('successful_workflow_runs', 0)}")
                print(f"  Releases:         {stats.get('releases_created', 0)}")
                print(f"  Co-authored:      {stats.get('coauthored_commits', 0)}")

                updates = result.get("updates", [])
                if updates:
                    print("\n  Achievement Updates:")
                    for update in updates:
                        print(f"    {update['achievement_name']}: {update['message']}")
            else:
                print(f"  Error: {result.get('error')}")
        return

    if args.recommendations:
        recs = tracker.get_recommendations()
        if args.json:
            print(json.dumps(recs, indent=2))
        else:
            print("\n  Achievement Recommendations")
            print("  " + "=" * 40)
            for rec in recs:
                ach = rec["achievement"]
                print(f"\n  [{rec['priority'].upper()}] {ach['icon']} {ach['name']}")
                print(f"    {rec['reason']}")
                print("    Next steps:")
                for step in rec.get("steps", [])[:2]:
                    print(f"      - {step}")
        return

    if args.list:
        achievements = tracker.get_all_achievements()
        if args.json:
            print(json.dumps(achievements, indent=2))
        else:
            print("\n  GitHub Achievements")
            print("  " + "=" * 40)
            for ach in achievements:
                status_icon = "✓" if ach.get("progress", {}).get("status") == "earned" else "○"
                tier = ach.get("progress", {}).get("current_tier", "")
                tier_str = f" [{tier.upper()}]" if tier else ""
                print(f"  {status_icon} {ach['icon']} {ach['name']}{tier_str}")
                print(f"      {ach['description']}")
        return

    # Default: status
    status = tracker.get_status()
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("=" * 50)
        print("  SLATE GitHub Achievement Tracker")
        print("=" * 50)
        print(f"\n  Total: {status['total_achievements']} achievements")
        print(f"  Earned: {status['earned']}")
        print(f"  In Progress: {status['in_progress']}")
        print(f"  Locked: {status['locked']}")

        recs = status.get("recommendations", [])
        if recs:
            print("\n  Top Recommendations:")
            for rec in recs:
                print(f"    - {rec['achievement']['name']}: {rec['reason']}")
        print("=" * 50)


def main():
    """CLI entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
