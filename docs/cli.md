# Command Line Interface (CLI)

This project provides a powerful CLI for backend operations, available via `src/cli.py` and powered by [Typer](https://typer.tiangolo.com/). You can use it to manage migrations, patches, encryption, applet seeding, arbitrary server settings, and more.

## Usage

```bash
python src/cli.py [COMMAND] [SUBCOMMAND] [OPTIONS]
```

## Available Top-Level Commands
- `mfa` – MFA management (clear, status)
- `arbitrary` – Manage arbitrary server settings and data transfer
- `patch` – Execute or list database/data patches
- `encryption` – Encrypt, decrypt, or re-encrypt data
- `applet` – Applet management and seeding
- `applet-ema` – Export EMA schedules
- `activities` – Commands for processing activities
- `assessments` – Commands for processing assessments
- `token` - Generate access token

## Getting Help
All commands and subcommands support `--help` for detailed usage, arguments, and options:

```bash
python src/cli.py [COMMAND] --help
```

## Example Commands
- Run a patch:
  ```bash
  python src/cli.py patch exec M2-8568 -a <applet_id>
  ```
- Seed applet data from YAML:
  ```bash
  python src/cli.py applet seed /path/to/config.yaml
  ```
- Add arbitrary server settings:
  ```bash
  python src/cli.py arbitrary add <owner_email> --db-uri <uri> --storage-type <type> --storage-secret-key <key>
  ```

## More CLI Documentation
Some commands (such as applet seeding) have detailed documentation in their respective subfolders, e.g.:
- [`src/apps/applets/commands/applet/seed/v1/README.md`](src/apps/applets/commands/applet/seed/v1/README.md)

Refer to these files for configuration schemas and advanced usage.
