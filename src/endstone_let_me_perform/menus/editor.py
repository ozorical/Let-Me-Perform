import json

from endstone.form import Dropdown, Label, Slider, TextInput, Toggle

from endstone_let_me_perform.menus import theme
from endstone_let_me_perform.settings import CHOICE, LISTING, TOGGLE, Option, Section

SLIDER_STEPS = 100
TEXT_BOX_LENGTH = 100
LISTING_NOTE = f"Put commas between entries. A box holds {TEXT_BOX_LENGTH} characters, so add new ones in the empty box."


class Editor:
    def __init__(self, section: Section, values):
        self.controls = []
        self.owners = []
        for option in section.options:
            if option.key == "enabled":
                continue

            hint = f"{option.hint} {LISTING_NOTE}" if option.kind == LISTING else option.hint
            inputs = inputs_for(option, getattr(values, option.key))
            self.controls.append(Label(theme.prose(hint)))
            self.controls.extend(inputs)
            self.owners.append(None)
            self.owners.extend([option] * len(inputs))

    def read(self, data: str) -> dict:
        answers = json.loads(data)
        owners = self.owners
        if len(answers) != len(owners):
            owners = [owner for owner in owners if owner is not None]

        given = {}
        for option, raw in zip(owners, answers, strict=True):
            if option is not None:
                given.setdefault(option, []).append(raw)
        return {option: answer_for(option, raws) for option, raws in given.items()}


def inputs_for(option: Option, value) -> list:
    if option.kind == TOGGLE:
        return [Toggle(option.label, value)]

    if option.kind == CHOICE:
        return [Dropdown(option.label, list(option.choices), option.choices.index(value))]

    if option.kind == LISTING:
        return listing_boxes(option, value)

    if (option.highest - option.lowest) / option.step > SLIDER_STEPS:
        return [TextInput(option.label, f"{option.lowest} to {option.highest}", str(value))]

    return [Slider(option.label, option.lowest, option.highest, option.step, value)]


def listing_boxes(option: Option, entries: list) -> list:
    texts = [""]
    for entry in entries:
        joined = f"{texts[-1]}, {entry}" if texts[-1] else entry
        if texts[-1] and len(joined) > TEXT_BOX_LENGTH:
            texts.append(entry)
        else:
            texts[-1] = joined

    if texts[-1]:
        texts.append("")

    return [
        TextInput(option.label if number == 1 else f"{option.label}, box {number}", "One entry, another entry", text)
        for number, text in enumerate(texts, 1)
    ]


def answer_for(option: Option, raws: list):
    if option.kind == LISTING:
        return ",".join(raws) if all(isinstance(raw, str) for raw in raws) else None

    raw = raws[0]
    if option.kind != CHOICE:
        return raw

    if type(raw) is int and 0 <= raw < len(option.choices):
        return option.choices[raw]
    return None
