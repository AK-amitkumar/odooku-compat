import click
import sys

from odooku.cli.helpers import resolve_db_name


__all__ = [
    'data'
]


@click.command()
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.option(
    '--delayed',
    is_flag=True
)
@click.option(
    '--config-file'
)
@click.pass_context
def export(ctx, db_name, delayed, config_file=None):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)

    from odooku.data import Exporter, ExportConfig
    exporter = Exporter(
        registry,
        config=config_file and ExportConfig.from_file(config_file) or None
    )
    exporter.export(sys.stdout, delayed=delayed)


@click.command('import')
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.option(
    '--fake',
    is_flag=True
)
@click.pass_context
def import_(ctx, db_name, fake):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)
    from odooku.data import Importer
    importer = Importer(registry)
    importer.import_(sys.stdin, fake=fake)


@click.group()
@click.pass_context
def data(ctx):
    pass


data.add_command(export)
data.add_command(import_)
