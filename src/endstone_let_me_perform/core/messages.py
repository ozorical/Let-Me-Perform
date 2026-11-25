PREFIX = "§8[§bLMP§8]§r "


def tell(sender, text: str) -> None:
    sender.send_message(f"{PREFIX}§7{text}")


def tell_success(sender, text: str) -> None:
    sender.send_message(f"{PREFIX}§a{text}")


def tell_failure(sender, text: str) -> None:
    sender.send_error_message(f"{PREFIX}§c{text}")


def tell_line(sender, label: str, value) -> None:
    sender.send_message(f"§7{label}: §f{value}")


def tell_heading(sender, text: str) -> None:
    sender.send_message(f"§6{text}")


def broadcast(server, text: str) -> None:
    server.broadcast_message(f"{PREFIX}{text}")


def show_tip(player, text: str) -> None:
    try:
        if player.is_valid:
            player.send_tip(text)
    except Exception:
        return


def describe_chunk(chunk) -> str:
    dimension, x, z = chunk
    return f"{dimension} chunk {x}, {z} (around {x * 16 + 8}, {z * 16 + 8})"
