import click
import sys

import gevent


__all__ = [
    'runtests'
]


@click.command()
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def runtests(ctx, module):
    config, logger = (
        ctx.obj['config'],
        ctx.obj['logger'],
    )

    if module:
        modules = {
            module_name: 1
            for module_name in module
        }
        config['init'] = dict(modules)

    # !! Tests need demo data
    config['without_demo'] = '' # Enables demo data
    config['test_enable'] = True
    config['xmlrpc_port'] = 8000


    # !! Database signalling needs to be turned off while
    #    running tests
    import odoo
    odoo.multi_process = False

    # Now import further
    from odoo.tests.common import PORT
    from odoo.modules.registry import RegistryManager
    from odooku.wsgi import WSGIServer

    server = WSGIServer(
        PORT,
        max_accept=1
    )

    gevent.spawn(server.serve_forever)

    def runtests():
        registry = RegistryManager.new(config['db_name'])
        total = (registry._assertion_report.successes + registry._assertion_report.failures)
        failures = registry._assertion_report.failures
        logger.info("Completed (%s) tests. %s failures." % (total, failures))
        sys.exit(1 if failures else 0)

    gevent.spawn(runtests).join()
