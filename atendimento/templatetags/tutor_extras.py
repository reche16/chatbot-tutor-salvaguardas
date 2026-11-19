import re

from django import template

register = template.Library()


@register.filter
def sem_markdown(texto):
    """Prévia em texto corrido: tira cercas de código, negrito e crases."""
    if not texto:
        return texto
    texto = re.sub(r"```[\w+-]*", " ", texto)
    texto = texto.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", texto).strip()


@register.filter
def markdown_simples(texto):
    """Mesmo Markdown mínimo do chat, no servidor: escapa todo o HTML antes de marcar
    blocos de código, `código`, **negrito** e *itálico* (telas do professor)."""
    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    if not texto:
        return texto
    partes = re.split(r"```[\w+-]*\n?", escape(texto))
    saida = []
    for i, p in enumerate(partes):
        if i % 2:
            saida.append("<pre><code>" + p.rstrip("\n") + "</code></pre>")
        else:
            p = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", p)
            p = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", p)
            p = re.sub(r"(^|[\s(])\*([^*\n]+)\*(?=[\s).,:;!?]|$)", r"\1<em>\2</em>", p, flags=re.M)
            saida.append(re.sub(r"\$([^$\n]{1,40})\$", r"\1", p))
    return mark_safe("".join(saida))
