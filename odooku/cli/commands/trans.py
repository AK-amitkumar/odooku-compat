import sys
import os
import tempfile
import click

from odooku.cli.resolve import resolve_db_name


__all__ = [
    'trans'
]


CHUNK_SIZE = 16 * 1024


@click.command()
@click.argument('language', nargs=1)
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def export(ctx, language, db_name, module):
    modules = module or ['all']

    from odoo.modules.registry import RegistryManager
    from odoo.api import Environment
    from odoo.tools import trans_export
    with tempfile.TemporaryFile() as t:
        registry = RegistryManager.get(db_name)
        with Environment.manage():
            with registry.cursor() as cr:
                trans_export(language, modules, t, 'po', cr)

        t.seek(0)
        # Pipe to stdout
        while True:
            chunk = t.read(CHUNK_SIZE)
            if not chunk:
                break
            sys.stdout.write(chunk)


@click.command('import')
@click.argument('language', nargs=1)
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.option(
    '--overwrite',
    is_flag=True
)
@click.pass_context
def import_(ctx, language, db_name, overwrite):
    context = {
        'overwrite': overwrite
    }

    from odoo.modules.registry import RegistryManager
    from odoo.api import Environment
    from odoo.tools import trans_load

    with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as t:
        registry = RegistryManager.get(db_name)

        # Read from stdin
        while True:
            chunk = sys.stdin.read(CHUNK_SIZE)
            if not chunk:
                break
            t.write(chunk)
        t.close()

        with Environment.manage():
            with registry.cursor() as cr:
                trans_load(cr, t.name, language, context=context)

        os.unlink(t.name)



@click.group()
@click.pass_context
def trans(ctx):
    pass


trans.add_command(export)
trans.add_command(import_)
