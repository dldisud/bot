from __future__ import annotations

from typing import Optional

import tweepy


def post_tweet_if_enabled(
    text: str,
    post_enabled: bool,
    consumer_key: Optional[str],
    consumer_secret: Optional[str],
    access_token: Optional[str],
    access_token_secret: Optional[str],
    bearer_token: Optional[str] = None,
) -> Optional[str]:
    """Post a tweet when enabled. Returns tweet ID if posted, otherwise None."""
    if not post_enabled:
        print("[DRY-RUN] 트윗 미게시. 본문:\n" + text)
        return None

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token,
        wait_on_rate_limit=True,
    )
    resp = client.create_tweet(text=text)
    tweet_id = None
    try:
        tweet_id = resp.data.get("id") if hasattr(resp, "data") else None
    except Exception:
        tweet_id = None
    if tweet_id:
        print(f"게시 완료: https://x.com/i/web/status/{tweet_id}")
    else:
        print("게시 완료")
    return tweet_id


