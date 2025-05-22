from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def getattribute(obj, attr):
    """
    Récupère un attribut d'un objet par son nom.
    Usage: {{ object|getattribute:"attribute_name" }}
    """
    if hasattr(obj, attr):
        return getattr(obj, attr)
    elif hasattr(obj, 'get') and callable(getattr(obj, 'get')):
        return obj.get(attr)
    else:
        return None

@register.filter
def dictsort_by_date(value, arg):
    """
    Trie une liste de dictionnaires par date.
    """
    return sorted(value, key=lambda x: getattr(x, arg))

@register.filter
def groupby_date(sequence, attr):
    """
    Groupe une séquence d'objets par un attribut de date.
    Retourne une liste de tuples (date, liste d'objets).
    """
    result = {}
    for item in sequence:
        attr_value = getattr(item, attr).date() if hasattr(getattr(item, attr), 'date') else getattr(item, attr)
        if attr_value not in result:
            result[attr_value] = []
        result[attr_value].append(item)
    return result.items()

@register.filter
def linebreaks_with_code(value):
    """
    Convertit les sauts de ligne en balises <br> et préserve les blocs de code.
    """
    import re
    
    # Préserver les blocs de code délimités par ```
    code_blocks = re.findall(r'```.*?```', value, re.DOTALL)
    placeholders = []
    
    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{i}__"
        value = value.replace(block, placeholder)
        placeholders.append((placeholder, block))
    
    # Convertir les sauts de ligne en <br>
    value = value.replace('\n', '<br>')
    
    # Restaurer les blocs de code
    for placeholder, block in placeholders:
        formatted_block = f'<pre><code>{block[3:-3]}</code></pre>'
        value = value.replace(placeholder, formatted_block)
    
    return value 