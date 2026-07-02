"""Shared Jinja2 templates instance."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

templates_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(templates_dir)))


def render(request, template_name: str, context: dict = None):
    """Render a template with the given context."""
    from fastapi.templating import Jinja2Templates as _  # noqa — keep import for reference
    ctx = context or {}
    ctx["request"] = request
    template = env.get_template(template_name)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(template.render(**ctx))
