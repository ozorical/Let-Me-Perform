BUTTON_LABEL = "§0"
BUTTON_HINT = "§8"
BUTTON_ON = "§2"
BUTTON_OFF = "§4"

PROSE = "§7"
VALUE = "§f"
ON = "§a"
OFF = "§c"
COUNT = "§e"
HEADING = "§6"

YES = f"{BUTTON_ON}Yes"
NO = f"{BUTTON_OFF}No"


def button(label: str, hint: str) -> str:
    return f"{BUTTON_LABEL}{label}\n{BUTTON_HINT}[ {hint} {BUTTON_HINT}]"


def switch(on: bool) -> str:
    if on:
        return f"{BUTTON_ON}On{BUTTON_HINT}"
    return f"{BUTTON_OFF}Off{BUTTON_HINT}"


def prose(text: str) -> str:
    return f"{PROSE}{text}"


def heading(text: str) -> str:
    return f"{HEADING}{text}"


def line(label: str, value) -> str:
    return f"{PROSE}{label}: {VALUE}{value}"


def state(on: bool) -> str:
    return f"{ON}On" if on else f"{OFF}Off"


def count(value) -> str:
    return f"{COUNT}{value}{PROSE}"


def paragraphs(texts) -> str:
    return "\n\n".join(prose(text) for text in texts)


def tables(blocks) -> str:
    drawn = []
    for title, rows in blocks:
        lines = [heading(title)]
        lines.extend(line(label, value) for label, value in rows)
        drawn.append("\n".join(lines))
    return "\n\n".join(drawn)
