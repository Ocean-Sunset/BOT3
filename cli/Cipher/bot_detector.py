"""
Cipher Bot Detection System
Percentage-based algorithm to detect bot accounts

Scoring Algorithm:
- Account Age (30% weight)
- Username Patterns (25% weight)
- Avatar Analysis (15% weight)
- Behavior Analysis (30% weight)

Total Score: 0-100% (higher = more likely bot)
"""

import discord
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

print("✅ - Bot Detector loaded.")


@dataclass
class BotAnalysis:
    """Result of bot detection analysis"""
    member: discord.Member
    total_score: int
    breakdown: Dict[str, int]
    is_likely_bot: bool
    risk_level: str  # "low", "medium", "high", "critical"
    
    def __str__(self):
        return f"Bot Score: {self.total_score}% ({self.risk_level.upper()} risk)"


class BotDetector:
    """
    Advanced bot account detection system
    
    Uses multi-factor analysis to determine likelihood of bot accounts:
    1. Account age and creation patterns
    2. Username structure and patterns
    3. Avatar/profile analysis
    4. Behavioral patterns
    """
    
    # Pattern definitions
    SEQUENTIAL_NUMBERS = re.compile(r'\d{4,}')  # 4+ consecutive digits
    RANDOM_CHARS = re.compile(r'^[a-z]{2,4}\d{2,4}[a-z]{0,2}$', re.IGNORECASE)
    BOT_KEYWORDS = ['bot', 'user', 'member', 'discord', 'alt', 'backup']
    
    # Thresholds
    THRESHOLD_LOW = 30
    THRESHOLD_MEDIUM = 50
    THRESHOLD_HIGH = 70
    
    def __init__(self):
        """Initialize bot detector"""
        # Track join patterns for raid detection
        self.recent_joins: Dict[int, List[datetime]] = {}  # guild_id -> join times
        
    # ==================== Main Analysis Function ====================
    
    def analyze_account(
        self, 
        member: discord.Member,
        check_raid_pattern: bool = True
    ) -> BotAnalysis:
        """
        Perform comprehensive bot analysis on a member
        
        Args:
            member: Discord member to analyze
            check_raid_pattern: Include raid pattern analysis (requires recent joins tracking)
            
        Returns:
            BotAnalysis with score, breakdown, and verdict
        """
        breakdown = {}
        
        # Account age analysis (30% weight)
        breakdown['account_age'] = self._check_account_age(member)
        
        # Username pattern analysis (25% weight)
        breakdown['username'] = self._check_username_patterns(member)
        
        # Avatar analysis (15% weight)
        breakdown['avatar'] = self._check_avatar(member)
        
        # Behavior analysis (30% weight)
        behavior_score = 0
        if check_raid_pattern:
            behavior_score = self._check_behavior_patterns(member)
        breakdown['behavior'] = behavior_score
        
        # Calculate total score
        total_score = sum(breakdown.values())
        
        # Determine risk level
        if total_score < self.THRESHOLD_LOW:
            risk_level = "low"
        elif total_score < self.THRESHOLD_MEDIUM:
            risk_level = "medium"
        elif total_score < self.THRESHOLD_HIGH:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        # Determine if likely bot (default threshold: 60%)
        is_likely_bot = total_score >= 60
        
        return BotAnalysis(
            member=member,
            total_score=total_score,
            breakdown=breakdown,
            is_likely_bot=is_likely_bot,
            risk_level=risk_level
        )
    
    # ==================== Analysis Components ====================
    
    def _check_account_age(self, member: discord.Member) -> int:
        """
        Check account age (30% max weight)
        
        < 1 week: +30 points
        < 1 month: +15 points
        < 3 months: +5 points
        """
        account_age = datetime.utcnow() - member.created_at.replace(tzinfo=None)
        
        if account_age < timedelta(days=7):
            return 30
        elif account_age < timedelta(days=30):
            return 15
        elif account_age < timedelta(days=90):
            return 5
        else:
            return 0
    
    def _check_username_patterns(self, member: discord.Member) -> int:
        """
        Check username for bot patterns (25% max weight)
        
        - Sequential numbers (e.g., user1234): +25 points
        - Random chars (e.g., xj9d2k): +20 points
        - Bot keywords (e.g., user_bot_###): +25 points
        """
        username = member.name.lower()
        score = 0
        
        # Check for sequential numbers
        if self.SEQUENTIAL_NUMBERS.search(username):
            score += 25
        
        # Check for random character pattern
        elif self.RANDOM_CHARS.match(username):
            score += 20
        
        # Check for bot keywords
        for keyword in self.BOT_KEYWORDS:
            if keyword in username:
                score = max(score, 25)  # Max 25 for any keyword match
                break
        
        return min(score, 25)  # Cap at 25
    
    def _check_avatar(self, member: discord.Member) -> int:
        """
        Check avatar/profile (15% max weight)
        
        - Default Discord avatar: +15 points
        - No avatar hash change: +10 points
        """
        # Check if using default avatar
        if member.avatar is None:
            return 15
        
        # Check if avatar is very generic (low discriminator variation)
        # This is a heuristic - default avatars often have patterns
        if member.display_avatar.url.startswith("https://cdn.discordapp.com/embed/avatars/"):
            return 10
        
        return 0
    
    def _check_behavior_patterns(self, member: discord.Member) -> int:
        """
        Check behavioral patterns (30% max weight)
        
        - Joined during raid window: +30 points
        - Similar join time to other accounts: +25 points
        """
        score = 0
        guild_id = member.guild.id
        
        # Track this join
        if guild_id not in self.recent_joins:
            self.recent_joins[guild_id] = []
        
        now = datetime.utcnow()
        self.recent_joins[guild_id].append(now)
        
        # Clean old joins (older than 5 minutes)
        self.recent_joins[guild_id] = [
            join_time for join_time in self.recent_joins[guild_id]
            if now - join_time < timedelta(minutes=5)
        ]
        
        # Check join rate (raid pattern)
        recent_count = len(self.recent_joins[guild_id])
        if recent_count >= 10:  # 10+ joins in 5 minutes
            score += 30
        elif recent_count >= 5:  # 5+ joins in 5 minutes
            score += 25
        
        return min(score, 30)  # Cap at 30
    
    # ==================== Helper Functions ====================
    
    def get_bot_score(self, member: discord.Member) -> int:
        """Quick bot score check (returns just the percentage)"""
        analysis = self.analyze_account(member)
        return analysis.total_score
    
    def is_likely_bot(self, member: discord.Member, threshold: int = 60) -> bool:
        """
        Check if member is likely a bot account
        
        Args:
            member: Discord member to check
            threshold: Custom threshold (default: 60%)
            
        Returns:
            True if bot score >= threshold
        """
        score = self.get_bot_score(member)
        return score >= threshold
    
    def get_detailed_report(self, analysis: BotAnalysis) -> str:
        """
        Generate detailed text report from analysis
        
        Returns formatted string suitable for embed description
        """
        report = []
        report.append(f"**Bot Detection Score: {analysis.total_score}%**")
        report.append(f"**Risk Level: {analysis.risk_level.upper()}**\n")
        
        report.append("**Breakdown:**")
        report.append(f"• Account Age: {analysis.breakdown['account_age']}/30 points")
        report.append(f"• Username Pattern: {analysis.breakdown['username']}/25 points")
        report.append(f"• Avatar Analysis: {analysis.breakdown['avatar']}/15 points")
        report.append(f"• Behavior Pattern: {analysis.breakdown['behavior']}/30 points")
        
        report.append(f"\n**Verdict:** {'🚨 Likely Bot Account' if analysis.is_likely_bot else '✅ Likely Human'}")
        
        return "\n".join(report)
    
    def cleanup_old_joins(self, guild_id: int):
        """Manually clean up old join data for a guild"""
        if guild_id in self.recent_joins:
            now = datetime.utcnow()
            self.recent_joins[guild_id] = [
                join_time for join_time in self.recent_joins[guild_id]
                if now - join_time < timedelta(minutes=5)
            ]
