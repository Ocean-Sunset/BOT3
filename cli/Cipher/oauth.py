"""
Simple OAuth helper for Cipher.

This module provides an `OAuthManager` that:
- loads client id/secret from environment or file
- builds Discord OAuth2 URLs
- verifies an OAuth2 code by exchanging it for a token (using `requests`)
- stores a small in-memory verification log

This is intentionally lightweight and synchronous to keep integration simple.
"""
from __future__ import annotations
import os
import time
import uuid
import json
from typing import Optional, Dict
import requests

DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"


class OAuthManager:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, redirect_uri: Optional[str] = None):
        self.client_id = client_id or "1323734010345689189"
        self.client_secret = client_secret or os.getenv("DISCORD_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or "https://ciphers-oauth2-system.onrender.com/callback"
        self.verify_log: Dict[str, Dict] = {}

    def build_authorize_url(self, scopes: Optional[str] = "identify") -> str:
        state = str(uuid.uuid4())
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
            "prompt": "consent",
        }
        # save state for later verification
        self.verify_log[state] = {"created": time.time(), "scopes": scopes}
        query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items() if v)
        return f"{DISCORD_AUTHORIZE_URL}?{query}"

    def exchange_code(self, code: str) -> Dict:
        """Exchange an OAuth code for tokens.

        Returns a dict with the response or raises requests.HTTPError on failure.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        # record exchange in log
        self.verify_log[result.get("access_token", code)] = {
            "timestamp": time.time(),
            "result": result,
        }
        return result

    def cleanup_log(self, max_age: int = 3600):
        cutoff = time.time() - max_age
        self.verify_log = {k: v for k, v in self.verify_log.items() if v.get("timestamp", v.get("created", 0)) > cutoff}


OAUTH = OAuthManager()


def load_from_env():
    OAUTH.client_id = os.getenv("DISCORD_CLIENT_ID")
    OAUTH.client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    OAUTH.redirect_uri = os.getenv("DISCORD_OAUTH_REDIRECT")


if __name__ == "__main__":
    load_from_env()
    print("OAuthManager ready. Example authorize URL:")
    print(OAUTH.build_authorize_url())
