import enum
import math
import sys
import types
import uuid
from datetime import datetime
from pathlib import Path

import tomlkit


class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class Location:
    def __init__(self, dimension, x, y, z, pitch=0.0, yaw=0.0):
        self.dimension = dimension
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.pitch = pitch
        self.yaw = yaw

    @property
    def block_x(self):
        return math.floor(self.x)

    @property
    def block_y(self):
        return math.floor(self.y)

    @property
    def block_z(self):
        return math.floor(self.z)

    def distance_squared(self, other):
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2

    def distance(self, other):
        return math.sqrt(self.distance_squared(other))


class BlockFace(enum.Enum):
    DOWN = 0
    UP = 1
    NORTH = 2
    SOUTH = 3
    WEST = 4
    EAST = 5


class Block:
    def __init__(self, dimension, x, y, z, type_id="minecraft:air"):
        self.dimension = dimension
        self.x = x
        self.y = y
        self.z = z
        self.type = type_id

    @property
    def location(self):
        return Location(self.dimension, self.x, self.y, self.z)

    def get_relative(self, offset_x, offset_y, offset_z):
        return Block(self.dimension, self.x + offset_x, self.y + offset_y, self.z + offset_z, self.type)


class Chunk:
    def __init__(self, dimension, x, z):
        self.dimension = dimension
        self.level = dimension.level
        self.x = x
        self.z = z


class Dimension:
    def __init__(self, level, name):
        self.level = level
        self.name = name
        self.blocks = {}
        self.loaded_chunks = []

    def get_block_at(self, x, y=None, z=None):
        if y is None:
            x, y, z = x.block_x, x.block_y, x.block_z
        return self.blocks.get((x, y, z)) or Block(self, x, y, z)

    def set_block(self, x, y, z, type_id):
        block = Block(self, x, y, z, type_id)
        self.blocks[(x, y, z)] = block
        return block

    def spawn_actor(self, location, type_id):
        actor = Mob(type_id, location)
        self.level.server.spawn(actor)
        return actor if actor.is_valid else None

    def drop_item(self, location, item):
        actor = Item(location, item)
        self.level.server.spawn(actor)
        return actor

    @property
    def actors(self):
        return [actor for actor in self.level.actors if actor.location.dimension is self]


class Level:
    def __init__(self, server):
        self.server = server
        self.name = "Bedrock level"
        self.dimensions = [Dimension(self, name) for name in ("Overworld", "Nether", "TheEnd")]
        self.held = {}

    @property
    def actors(self):
        return list(self.held.values()) + list(self.server.online_players)

    def get_dimension(self, name):
        wanted = name.lower().replace("_", "")
        for dimension in self.dimensions:
            if dimension.name.lower() == wanted:
                return dimension
        return None


class Actor:
    next_id = 1000

    def __init__(self, type_id, location):
        Actor.next_id += 1
        self.id = Actor.next_id
        self.runtime_id = Actor.next_id
        self.type = type_id
        self.location = location
        self.is_valid = True
        self.name_tag = ""
        self.is_name_tag_visible = True
        self.is_name_tag_always_visible = False
        self.is_on_ground = True
        self.velocity = Vector()
        self.tags = []

    @property
    def dimension(self):
        return self.location.dimension

    @property
    def level(self):
        return self.location.dimension.level

    @property
    def is_dead(self):
        return not self.is_valid

    @property
    def scoreboard_tags(self):
        return list(self.tags)

    def add_scoreboard_tag(self, tag):
        if tag in self.tags:
            return False
        self.tags.append(tag)
        return True

    def remove_scoreboard_tag(self, tag):
        if tag not in self.tags:
            return False
        self.tags.remove(tag)
        return True

    def teleport(self, location):
        self.location = location
        return True

    def remove(self):
        if not self.is_valid:
            return
        self.is_valid = False
        self.level.server.removed(self)


class Mob(Actor):
    def __init__(self, type_id, location):
        super().__init__(type_id, location)
        self.health = 20
        self.max_health = 20
        self.is_gliding = False


class Item(Actor):
    def __init__(self, location, item_stack):
        super().__init__("minecraft:item", location)
        self.item_stack = item_stack
        self.pickup_delay = 0
        self.is_unlimited_lifetime = False
        self.thrower = None


class GameMode(enum.Enum):
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    SPECTATOR = 3


class PlayerInventory:
    def __init__(self):
        self.item_in_main_hand = None
        self.item_in_off_hand = None


class Player(Mob):
    def __init__(self, name, location):
        super().__init__("minecraft:player", location)
        self.name = name
        self.unique_id = uuid.uuid4()
        self.game_mode = GameMode.SURVIVAL
        self.is_op = False
        self.is_flying = False
        self.is_sneaking = False
        self.ping = 20
        self.inventory = PlayerInventory()
        self.granted = set()
        self.messages = []
        self.errors = []
        self.tips = []
        self.popups = []
        self.toasts = []
        self.forms = []
        self.kicked = None

    def send_message(self, message):
        self.messages.append(message)

    def send_error_message(self, message):
        self.errors.append(message)

    def send_tip(self, message):
        self.tips.append(message)

    def send_popup(self, message):
        self.popups.append(message)

    def send_toast(self, title, content):
        self.toasts.append((title, content))

    def send_form(self, form):
        self.forms.append(form)

    def close_form(self):
        return

    def has_permission(self, name):
        return self.is_op or name in self.granted

    def kick(self, message):
        self.kicked = message
        self.level.server.quit(self)


class ConsoleCommandSender:
    name = "Server"
    is_op = True

    def __init__(self):
        self.messages = []
        self.errors = []

    def send_message(self, message):
        self.messages.append(message)

    def send_error_message(self, message):
        self.errors.append(message)

    def has_permission(self, name):
        return True


class CommandSender:
    pass


class Command:
    def __init__(self, name):
        self.name = name


class ItemType:
    def __init__(self, type_id, max_stack_size=64):
        self.id = type_id
        self.max_stack_size = max_stack_size


class ItemMeta:
    def __init__(self):
        self.enchants = {}
        self.display_name = None

    @property
    def has_enchants(self):
        return bool(self.enchants)

    def has_enchant(self, enchant_id):
        return enchant_id in self.enchants

    def get_enchant_level(self, enchant_id):
        return self.enchants.get(enchant_id, 0)


class ItemStack:
    def __init__(self, type_id, amount=1, data=0, max_stack_size=64):
        self.type = ItemType(type_id, max_stack_size)
        self.amount = amount
        self.data = data
        self.item_meta = ItemMeta()

    @property
    def max_stack_size(self):
        return self.type.max_stack_size

    def is_similar(self, other):
        return (
            self.type.id == other.type.id
            and self.data == other.data
            and self.item_meta.enchants == other.item_meta.enchants
            and self.item_meta.display_name == other.item_meta.display_name
        )


class DamageSource:
    def __init__(self, type_id="entity_attack", actor=None, damaging_actor=None):
        self.type = type_id
        self.actor = actor
        self.damaging_actor = damaging_actor or actor
        self.is_indirect = False


class EventPriority(enum.IntEnum):
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    MONITOR = 5


class Event:
    is_cancelled = False

    def cancel(self):
        self.is_cancelled = True


class ActorEvent(Event):
    def __init__(self, actor):
        self.actor = actor


class ActorSpawnEvent(ActorEvent):
    pass


class ActorRemoveEvent(ActorEvent):
    pass


class ActorDeathEvent(ActorEvent):
    def __init__(self, actor, damage_source=None):
        super().__init__(actor)
        self.damage_source = damage_source or DamageSource()


class ActorExplodeEvent(ActorEvent):
    def __init__(self, actor, location=None, block_list=None):
        super().__init__(actor)
        self.location = location or actor.location
        self.block_list = list(block_list or [])


class BlockEvent(Event):
    def __init__(self, block):
        self.block = block


class BlockPistonExtendEvent(BlockEvent):
    def __init__(self, block, direction=BlockFace.UP):
        super().__init__(block)
        self.direction = direction


class BlockPistonRetractEvent(BlockPistonExtendEvent):
    pass


class PlayerEvent(Event):
    def __init__(self, player):
        self.player = player


class PlayerJoinEvent(PlayerEvent):
    pass


class PlayerQuitEvent(PlayerEvent):
    pass


class PlayerInteractEvent(PlayerEvent):
    class Action(enum.Enum):
        LEFT_CLICK_BLOCK = 0
        RIGHT_CLICK_BLOCK = 1
        LEFT_CLICK_AIR = 2
        RIGHT_CLICK_AIR = 3

    LEFT_CLICK_BLOCK = Action.LEFT_CLICK_BLOCK
    RIGHT_CLICK_BLOCK = Action.RIGHT_CLICK_BLOCK
    LEFT_CLICK_AIR = Action.LEFT_CLICK_AIR
    RIGHT_CLICK_AIR = Action.RIGHT_CLICK_AIR

    def __init__(self, player, action, item=None, block=None, block_face=BlockFace.UP):
        super().__init__(player)
        self.action = action
        self.item = item
        self.block = block
        self.block_face = block_face
        self.clicked_position = None

    @property
    def has_item(self):
        return self.item is not None

    @property
    def has_block(self):
        return self.block is not None


def event_handler(func=None, *, priority=EventPriority.NORMAL, ignore_cancelled=False):
    def mark(handler):
        handler.is_event_handler = True
        handler.priority = priority
        handler.ignore_cancelled = ignore_cancelled
        return handler

    if func is not None:
        return mark(func)
    return mark


class Button:
    def __init__(self, text="", icon=None, on_click=None):
        self.text = text
        self.icon = icon
        self.on_click = on_click


class Label:
    def __init__(self, text=""):
        self.text = text


class Header:
    def __init__(self, label=""):
        self.label = label


class Divider:
    pass


class Toggle:
    def __init__(self, label="", default_value=False):
        self.label = label
        self.default_value = default_value


class Slider:
    def __init__(self, label="", min=0, max=100, step=20, default_value=None):
        self.label = label
        self.min = min
        self.max = max
        self.step = step
        self.default_value = default_value


class Dropdown:
    def __init__(self, label="", options=None, default_index=None):
        self.label = label
        self.options = list(options or [])
        self.default_index = default_index


class StepSlider(Dropdown):
    pass


class TextInput:
    def __init__(self, label="", placeholder="", default_value=None):
        self.label = label
        self.placeholder = placeholder
        self.default_value = default_value


class ActionForm:
    def __init__(self, title="", content="", buttons=None, on_submit=None, on_close=None):
        self.title = title
        self.content = content
        self.controls = list(buttons or [])
        self.on_submit = on_submit
        self.on_close = on_close

    @property
    def buttons(self):
        return [control for control in self.controls if isinstance(control, Button)]

    def add_button(self, text, icon=None, on_click=None):
        self.controls.append(Button(text, icon, on_click))
        return self

    def add_label(self, text):
        self.controls.append(Label(text))
        return self

    def add_header(self, text):
        self.controls.append(Header(text))
        return self

    def add_divider(self):
        self.controls.append(Divider())
        return self

    def press(self, player, index):
        button = self.buttons[index]
        if self.on_submit is not None:
            self.on_submit(player, index)
        if button.on_click is not None:
            button.on_click(player)


class MessageForm:
    def __init__(self, title="", content="", button1="", button2="", on_submit=None, on_close=None):
        self.title = title
        self.content = content
        self.button1 = button1
        self.button2 = button2
        self.on_submit = on_submit
        self.on_close = on_close


class ModalForm:
    def __init__(self, title="", controls=None, submit_button=None, icon=None, on_submit=None, on_close=None):
        self.title = title
        self.controls = list(controls or [])
        self.submit_button = submit_button
        self.icon = icon
        self.on_submit = on_submit
        self.on_close = on_close

    def add_control(self, control):
        self.controls.append(control)
        return self


class Allowance:
    def __init__(self, checks):
        self.left = checks

    def spent(self):
        self.left -= 1
        return self.left < 0


class Task:
    next_id = 0

    def __init__(self, owner, run, due, period):
        Task.next_id += 1
        self.task_id = Task.next_id
        self.owner = owner
        self.run = run
        self.due = due
        self.period = period
        self.is_cancelled = False
        self.is_sync = True

    def cancel(self):
        self.is_cancelled = True


class Scheduler:
    def __init__(self):
        self.tick = 0
        self.tasks = []

    def run_task(self, plugin, task, delay=0, period=0):
        created = Task(plugin, task, self.tick + max(1, delay), period)
        self.tasks.append(created)
        return created

    def cancel_task(self, task_id):
        for task in self.tasks:
            if task.task_id == task_id:
                task.cancel()

    def cancel_tasks(self, plugin):
        for task in self.tasks:
            if task.owner is plugin:
                task.cancel()

    def get_pending_tasks(self):
        return [task for task in self.tasks if not task.is_cancelled]

    def advance(self, ticks=1):
        for _ in range(ticks):
            self.tick += 1
            for task in list(self.tasks):
                if task.is_cancelled or task.due > self.tick:
                    continue
                task.run()
                if task.period > 0:
                    task.due = self.tick + task.period
                else:
                    task.cancel()
            self.tasks = [task for task in self.tasks if not task.is_cancelled]


class Logger:
    def __init__(self):
        self.lines = []

    def debug(self, message):
        self.lines.append(("debug", message))

    def info(self, message):
        self.lines.append(("info", message))

    def warning(self, message):
        self.lines.append(("warning", message))

    def error(self, message):
        self.lines.append(("error", message))

    def said(self, level):
        return [message for kind, message in self.lines if kind == level]


class Server:
    def __init__(self):
        self.scheduler = Scheduler()
        self.logger = Logger()
        self.online_players = []
        self.level = Level(self)
        self.command_sender = ConsoleCommandSender()
        self.handlers = []
        self.broadcasts = []
        self.dispatched = []
        self.current_mspt = 10.0
        self.average_mspt = 10.0
        self.current_tps = 20.0
        self.average_tps = 20.0
        self.current_tick_usage = 0.2
        self.average_tick_usage = 0.2
        self.max_players = 20
        self.start_time = datetime.now()

    @property
    def overworld(self):
        return self.level.dimensions[0]

    def at(self, x, y, z, dimension=None):
        return Location(dimension or self.overworld, x, y, z)

    def register(self, listener):
        for name in dir(listener):
            handler = getattr(listener, name)
            if not callable(handler) or not getattr(handler, "is_event_handler", False):
                continue
            event_type = next(iter(handler.__annotations__.values()))
            if not isinstance(event_type, type):
                raise RuntimeError("invalid event handler signature")
            self.handlers.append((handler.priority, event_type, handler))
        self.handlers.sort(key=lambda entry: entry[0])

    def fire(self, event):
        for _, event_type, handler in self.handlers:
            if type(event) is not event_type:
                continue
            if handler.ignore_cancelled and event.is_cancelled:
                continue
            handler(event)
        return event

    def spawn(self, actor):
        self.level.held[actor.id] = actor
        event = self.fire(ActorSpawnEvent(actor))
        if event.is_cancelled:
            actor.is_valid = False
            self.level.held.pop(actor.id, None)
        return actor

    def spawn_mob(self, type_id, x=0, y=64, z=0, dimension=None):
        return self.spawn(Mob(type_id, self.at(x, y, z, dimension)))

    def spawn_plain(self, type_id, x=0, y=64, z=0, dimension=None):
        return self.spawn(Actor(type_id, self.at(x, y, z, dimension)))

    def drop(self, item_id, amount=1, x=0, y=64, z=0, dimension=None, max_stack_size=64):
        stack = ItemStack(item_id, amount, max_stack_size=max_stack_size)
        return self.spawn(Item(self.at(x, y, z, dimension), stack))

    def removed(self, actor):
        if self.level.held.pop(actor.id, None) is not None:
            self.fire(ActorRemoveEvent(actor))

    def kill(self, mob, killer=None):
        self.fire(ActorDeathEvent(mob, DamageSource(actor=killer)))
        mob.remove()

    def join(self, name, x=0, y=64, z=0, dimension=None):
        player = Player(name, self.at(x, y, z, dimension))
        self.online_players.append(player)
        self.fire(PlayerJoinEvent(player))
        return player

    def quit(self, player):
        if player in self.online_players:
            self.online_players.remove(player)
            self.fire(PlayerQuitEvent(player))
        player.is_valid = False

    def get_player(self, name):
        for player in self.online_players:
            if player.name.lower() == str(name).lower():
                return player
        return None

    def broadcast_message(self, message):
        self.broadcasts.append(message)
        for player in self.online_players:
            player.send_message(message)

    def dispatch_command(self, sender, command_line):
        self.dispatched.append(command_line)
        return True


class Plugin:
    def __init__(self):
        self.server = None
        self.logger = None
        self.data_folder = None
        self.held_config = None
        self.is_enabled = False

    def attach(self, server, folder):
        self.server = server
        self.logger = server.logger
        self.data_folder = Path(folder)

    @property
    def config(self):
        if self.held_config is None:
            self.reload_config()
        return self.held_config

    def reload_config(self):
        path = Path(self.data_folder) / "config.toml"
        self.held_config = tomlkit.parse(path.read_text(encoding="utf-8"))
        return self.held_config

    def save_config(self):
        if self.held_config is None:
            return
        path = Path(self.data_folder) / "config.toml"
        path.write_text(tomlkit.dumps(self.held_config), encoding="utf-8")

    def register_events(self, listener):
        self.server.register(listener)


def module(name, **members):
    created = types.ModuleType(name)
    for key, value in members.items():
        setattr(created, key, value)
    sys.modules[name] = created
    return created


def install():
    root = module("endstone", Player=Player, GameMode=GameMode, Server=Server, __version__="0.11.16", __minecraft_version__="26.65")
    root.actor = module("endstone.actor", Actor=Actor, Mob=Mob, Item=Item)
    root.block = module("endstone.block", Block=Block, BlockFace=BlockFace)
    root.command = module("endstone.command", Command=Command, CommandSender=CommandSender, ConsoleCommandSender=ConsoleCommandSender)
    root.inventory = module("endstone.inventory", ItemStack=ItemStack, ItemType=ItemType, ItemMeta=ItemMeta)
    root.level = module("endstone.level", Level=Level, Dimension=Dimension, Location=Location, Chunk=Chunk)
    root.plugin = module("endstone.plugin", Plugin=Plugin)
    root.scheduler = module("endstone.scheduler", Scheduler=Scheduler, Task=Task)
    root.util = module("endstone.util", Vector=Vector)
    root.damage = module("endstone.damage", DamageSource=DamageSource)
    root.event = module(
        "endstone.event",
        Event=Event,
        EventPriority=EventPriority,
        event_handler=event_handler,
        ActorSpawnEvent=ActorSpawnEvent,
        ActorRemoveEvent=ActorRemoveEvent,
        ActorDeathEvent=ActorDeathEvent,
        ActorExplodeEvent=ActorExplodeEvent,
        BlockPistonExtendEvent=BlockPistonExtendEvent,
        BlockPistonRetractEvent=BlockPistonRetractEvent,
        PlayerInteractEvent=PlayerInteractEvent,
        PlayerJoinEvent=PlayerJoinEvent,
        PlayerQuitEvent=PlayerQuitEvent,
    )
    root.form = module(
        "endstone.form",
        ActionForm=ActionForm,
        MessageForm=MessageForm,
        ModalForm=ModalForm,
        Button=Button,
        Label=Label,
        Header=Header,
        Divider=Divider,
        Toggle=Toggle,
        Slider=Slider,
        StepSlider=StepSlider,
        Dropdown=Dropdown,
        TextInput=TextInput,
    )
