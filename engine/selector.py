"""
engine/selector.py — Topic Selector
===================================
Helper logic to select the next curriculum day to question the candidate on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from engine.analyzer import StrategyBrief, TopicEntry


def pick_next_topic(
    brief: StrategyBrief,
    days_already_asked: set[int]
) -> Optional[TopicEntry]:
    """
    Selects the next eligible topic from the strategy brief.
    
    Parameters
    ----------
    brief : StrategyBrief
        The compiled candidate strategy brief containing prioritized topics.
    days_already_asked : set[int]
        The set of day numbers that have already been queried in the session.
        
    Returns
    -------
    TopicEntry | None
        The next topic entry to ask about, or None if all topics are exhausted.
    """
    # Walk ordered_topics in pre-sorted priority order
    for topic in brief.ordered_topics:
        if topic.day not in days_already_asked:
            return topic
            
    return None
