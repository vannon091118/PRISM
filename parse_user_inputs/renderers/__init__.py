"""
parse_user_inputs.renderers
============================
Output-Renderer: Markdown, HTML (Jinja2), JSON.
"""

from parse_user_inputs.renderers.markdown import render_markdown
from parse_user_inputs.renderers.html_dashboard import render_html_dashboard
from parse_user_inputs.renderers.json_output import render_json

__all__ = ["render_markdown", "render_html_dashboard", "render_json"]
