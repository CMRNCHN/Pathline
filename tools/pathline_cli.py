from __future__ import annotations

import typer

from replay.cli import app as replay_app
from runtime.kernel.cli import app as runtime_app

app = typer.Typer(help="IVR assessor CLI")

app.registered_commands.extend(runtime_app.registered_commands)
app.registered_groups.extend(runtime_app.registered_groups)
app.registered_callback = runtime_app.registered_callback

app.registered_commands.extend(replay_app.registered_commands)
app.registered_groups.extend(replay_app.registered_groups)


def main() -> None:
    app()
