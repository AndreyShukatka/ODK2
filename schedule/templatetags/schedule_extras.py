from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    if not d:
        return None
    return d.get(key)

@register.filter
def dict_get2(d, key):
    if not d:
        return None
    # key может быть int, а в словаре int - приводим
    try:
        return d.get(key) or d.get(int(key))
    except:
        return d.get(key)

@register.filter
def dict_get_attr(d, key):
    # для totals: dict_get:emp.id|dict_get:'ur'
    if not d:
        return ""
    if isinstance(d, dict):
        return d.get(key, "")
    return getattr(d, key, "")