"""
templating.py — Zero-dependency Micro-Template Engine for Aero Suite.
Supports variables {{ var }}, dotted lookups {{ item.name }},
loops {% for x in list %}...{% endfor %}, and conditionals {% if x %}...{% else %}...{% endif %}.
Designed for clean, offline standalone execution without third-party dependencies (Jinja2).
"""
import os
import re
from typing import Any, Dict


class Template:
    """A lightweight, zero-dependency template renderer."""

    def __init__(self, template_str: str):
        self.template_str = template_str

    @classmethod
    def from_file(cls, filepath: str) -> "Template":
        """Loads a template from an absolute or relative filepath with UTF-8 encoding."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls(f.read())

    def render(self, **context: Any) -> str:
        """Renders the template with the provided context dictionary."""
        return self._render_string(self.template_str, context)

    @staticmethod
    def _resolve_var(var_expr: str, context: Dict[str, Any]) -> Any:
        """Resolves dotted variable expressions like 'user.name' or 'item.title'."""
        var_expr = var_expr.strip()
        if not var_expr:
            return ""

        parts = var_expr.split(".")
        val = context.get(parts[0], "")
        for part in parts[1:]:
            if isinstance(val, dict):
                val = val.get(part, "")
            elif hasattr(val, part):
                val = getattr(val, part)
            else:
                return ""
        return val if val is not None else ""

    def _render_string(self, text: str, context: Dict[str, Any]) -> str:
        # 1. Process Loops: {% for item in items %} ... {% endfor %}
        loop_pattern = re.compile(r"{%\s*for\s+(\w+)\s+in\s+([\w\.]+)\s*%}(.*?){%\s*endfor\s*%}", re.DOTALL)

        def eval_loop(m):
            item_var = m.group(1).strip()
            list_var = m.group(2).strip()
            body = m.group(3)
            iterable = self._resolve_var(list_var, context)

            if not iterable or not hasattr(iterable, "__iter__"):
                return ""

            chunks = []
            for item in iterable:
                sub_ctx = dict(context)
                sub_ctx[item_var] = item
                chunks.append(self._render_string(body, sub_ctx))
            return "".join(chunks)

        while loop_pattern.search(text):
            text = loop_pattern.sub(eval_loop, text)

        # 2. Process Conditionals: {% if var %} ... {% else %} ... {% endif %}
        if_pattern = re.compile(
            r"{%\s*if\s+(!?[\w\.]+)\s*%}(.*?)(?:{%\s*else\s*%}(.*?))?{%\s*endif\s*%}",
            re.DOTALL
        )

        def eval_if(m):
            cond_expr = m.group(1).strip()
            if_body = m.group(2)
            else_body = m.group(3) if m.group(3) is not None else ""

            is_negated = cond_expr.startswith("!")
            var_name = cond_expr[1:] if is_negated else cond_expr
            val = self._resolve_var(var_name, context)
            truthy = bool(val)
            if is_negated:
                truthy = not truthy

            active_body = if_body if truthy else else_body
            return self._render_string(active_body, context)

        while if_pattern.search(text):
            text = if_pattern.sub(eval_if, text)

        # 3. Process Variables: {{ var }}
        var_pattern = re.compile(r"{{\s*([\w\.]+)\s*}}")

        def eval_var(m):
            val = self._resolve_var(m.group(1), context)
            return str(val)

        text = var_pattern.sub(eval_var, text)
        return text


def render_template_file(filepath: str, **context) -> str:
    """Helper function to load and render a template file in one call."""
    return Template.from_file(filepath).render(**context)
