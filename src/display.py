"""Reviewer-facing labels. Persona identity and role remain Gate 1 data."""
from src.models import Persona


def format_persona_label(persona: Persona) -> str:
    return f'{persona.name} ({persona.role})'
