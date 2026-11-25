from endstone.event import (
    ActorDeathEvent,
    ActorExplodeEvent,
    ActorRemoveEvent,
    ActorSpawnEvent,
    BlockPistonExtendEvent,
    BlockPistonRetractEvent,
    PlayerInteractEvent,
    PlayerQuitEvent,
    event_handler,
)


class Listeners:
    def __init__(self, plugin):
        self.plugin = plugin
        self.spawn_gates = ()
        self.interact_hooks = ()

    def rebind(self) -> None:
        plugin = self.plugin
        self.spawn_gates = tuple(gate.admit for gate in (plugin.mob_cap, plugin.projectile_cap) if gate.enabled)
        self.interact_hooks = tuple(hook.on_interact for hook in (plugin.vehicle_cap, plugin.travel_cooldown) if hook.enabled)

    @event_handler(ignore_cancelled=True)
    def on_actor_spawn(self, event: ActorSpawnEvent) -> None:
        index = self.plugin.index
        if not index.active:
            return

        entry = index.classify(event.actor)
        if entry is None:
            return

        index.forget(entry.id)
        if not index.spawning:
            for admit in self.spawn_gates:
                if not admit(entry):
                    event.is_cancelled = True
                    return

        index.track(entry)

    @event_handler
    def on_actor_remove(self, event: ActorRemoveEvent) -> None:
        index = self.plugin.index
        if index.active:
            index.forget(event.actor.id)

    @event_handler
    def on_actor_death(self, event: ActorDeathEvent) -> None:
        stacker = self.plugin.mob_stacker
        if stacker.enabled:
            stacker.on_death(event)

    @event_handler(ignore_cancelled=True)
    def on_actor_explode(self, event: ActorExplodeEvent) -> None:
        guard = self.plugin.tnt_guard
        if guard.enabled:
            guard.on_explode(event)

    @event_handler(ignore_cancelled=True)
    def on_piston_extend(self, event: BlockPistonExtendEvent) -> None:
        guard = self.plugin.piston_guard
        if guard.enabled:
            guard.on_piston(event)

    @event_handler(ignore_cancelled=True)
    def on_piston_retract(self, event: BlockPistonRetractEvent) -> None:
        guard = self.plugin.piston_guard
        if guard.enabled:
            guard.on_piston(event)

    @event_handler(ignore_cancelled=True)
    def on_player_interact(self, event: PlayerInteractEvent) -> None:
        hooks = self.interact_hooks
        if not hooks or not event.has_item:
            return

        item = event.item
        item_id = item.type.id
        for hook in hooks:
            hook(event, item, item_id)

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        name = event.player.name
        self.plugin.afk.forget(name)
        self.plugin.travel_cooldown.forget(name)
