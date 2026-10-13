
from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    if not d: return None
    return d.get(key) or d.get(str(key))

@register.filter
def dict_get2(d, key):
    if not d: return None
    return d.get(key) or d.get(str(key))

@register.filter
def dict_get_attr(d, attr):
    if not d: return ""
    if isinstance(d, dict):
        return d.get(attr, "")
    return getattr(d, attr, "")
