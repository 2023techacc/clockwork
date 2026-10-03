"""Clockwork headless simulator."""
from .config import DEFAULT_RULES, RulesConfig
from .engine import CW, CCW, State, apply, legal_actions, new_fight, render, summary
