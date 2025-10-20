from datetime import datetime, timedelta
from app.models import Post
import math

# Reglas base
MEMBERSHIP_RULES = {
    "bronze": {"max_posts_per_week": 1, "max_words_per_post": 600},
    "silver": {"max_posts_per_week": 3, "max_words_per_post": 900},
    "gold": {"max_posts_per_week": 5, "max_words_per_post": 1200},
    "platinum": {"max_posts_per_week": math.inf, "max_words_per_post": 1500},
}

def get_current_week_number():
    return datetime.utcnow().isocalendar()[1]

def get_membership_limits(level):
    """Devuelve los límites según el nivel de membresía"""
    level = (level or "").replace(" ", "").lower()
    return MEMBERSHIP_RULES.get(level, MEMBERSHIP_RULES["bronze"])

def count_user_posts_this_week(user_id):
    """Cuenta cuántos posts ha creado el usuario esta semana"""
    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    return Post.query.filter(
        Post.user_id == user_id,
        Post.created_at >= start_of_week
    ).count()

def can_user_post(user, current_week_posts):
    membership_level = user.get("membership_level", "bronze").replace(" ", "").lower()
    limits = get_membership_limits(membership_level)
    return current_week_posts < limits["max_posts_per_week"]

def validate_post_length(user, word_count):
    membership_level = user.get("membership_level", "bronze").replace(" ", "").lower()
    limits = get_membership_limits(membership_level)
    return word_count <= limits["max_words_per_post"]

def count_words_from_blocks(blocks):
    total_words = 0
    for block in blocks:
        text = ""
        if isinstance(block, dict):
            text = block.get("text") or block.get("content") or ""
        elif isinstance(block, str):
            text = block
        total_words += len(text.split())
    return total_words
