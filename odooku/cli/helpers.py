import click

def resolve_db_name(ctx, param, value):
    config = (
        ctx.obj['config']
    )

    dbs = config['db_name'].split(',') if config['db_name'] else None
    if value:
        if dbs is not None and value not in dbs:
            raise click.BadParameter(
                "database '%s' is not found in explicit configuration."
            )
        return value
    elif dbs is not None and len(dbs) == 1:
        # Running in single db mode, safe to assume the db.
        return dbs[0]

    raise click.BadParameter(
        "no db name given."
    )


def prefix_envvar(envvar):
    return 'ODOOKU_%s' % envvar
