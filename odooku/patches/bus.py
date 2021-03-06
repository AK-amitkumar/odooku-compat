from odooku.patch import HardPatch

class patch_bus(HardPatch):

    @staticmethod
    def apply_patch():

        import datetime
        import json
        import logging
        import random
        import select
        import threading
        import time

        import odoo
        from odoo import api, fields, models, SUPERUSER_ID
        from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

        _logger = logging.getLogger(__name__)

        # PATCH !!
        # longpolling timeout connection
        # Max is 30 seconds for heroku platform
        from odooku.params import params
        TIMEOUT = getattr(params, 'TIMEOUT', 25)

        import gevent
        from gevent.event import Event

        # PATCH !!
        def _get_imbus_db():
            if odoo.tools.config['db_name']:
                return odoo.tools.config['db_name'].split(',')[0]
            return 'postgres'


        #----------------------------------------------------------
        # Bus
        #----------------------------------------------------------
        def json_dump(v):
            return json.dumps(v, separators=(',', ':'))

        def hashable(key):
            if isinstance(key, list):
                key = tuple(key)
            return key


        class ImBus(models.Model):

            _name = 'bus.bus'

            create_date = fields.Datetime('Create date')
            channel = fields.Char('Channel')
            message = fields.Char('Message')

            @api.model
            def gc(self):
                timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT*2)
                domain = [('create_date', '<', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
                return self.sudo().search(domain).unlink()

            @api.model
            def sendmany(self, notifications):
                channels = set()
                for channel, message in notifications:
                    channels.add(channel)
                    values = {
                        "channel": json_dump(channel),
                        "message": json_dump(message)
                    }
                    self.sudo().create(values)
                    if random.random() < 0.01:
                        self.gc()
                if channels:
                    # We have to wait until the notifications are commited in database.
                    # When calling `NOTIFY imbus`, some concurrent threads will be
                    # awakened and will fetch the notification in the bus table. If the
                    # transaction is not commited yet, there will be nothing to fetch,
                    # and the longpolling will return no notification.
                    def notify():
                        # PATCH !!
                        with odoo.sql_db.db_connect(_get_imbus_db()).cursor() as cr:
                            cr.execute("notify imbus, %s", (json_dump(list(channels)),))
                    self._cr.after('commit', notify)

            @api.model
            def sendone(self, channel, message):
                self.sendmany([[channel, message]])

            @api.model
            def poll(self, channels, last=0, options=None, force_status=False):
                if options is None:
                    options = {}
                # first poll return the notification in the 'buffer'
                if last == 0:
                    timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT)
                    domain = [('create_date', '>', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
                else:  # else returns the unread notifications
                    domain = [('id', '>', last)]
                channels = [json_dump(c) for c in channels]
                domain.append(('channel', 'in', channels))
                notifications = self.sudo().search_read(domain)
                # list of notification to return
                result = []
                for notif in notifications:
                    result.append({
                        'id': notif['id'],
                        'channel': json.loads(notif['channel']),
                        'message': json.loads(notif['message']),
                    })

                if result or force_status:
                    partner_ids = options.get('bus_presence_partner_ids')
                    if partner_ids:
                        partners = self.env['res.partner'].browse(partner_ids)
                        result += [{
                            'id': -1,
                            'channel': (self._cr.dbname, 'bus.presence'),
                            'message': {'id': r.id, 'im_status': r.im_status}} for r in partners]
                return result


        #----------------------------------------------------------
        # Dispatcher
        #----------------------------------------------------------
        class ImDispatch(object):
            def __init__(self):
                self.channels = {}

            def poll(self, dbname, channels, last, options=None, timeout=TIMEOUT):
                if options is None:
                    options = {}

                # Dont hang ctrl-c for a poll request, we need to bypass private
                # attribute access because we dont know before starting the thread that
                # it will handle a longpolling request
                if not odoo.evented:
                    current = threading.current_thread()
                    current._Thread__daemonic = True
                    # rename the thread to avoid tests waiting for a longpolling
                    current.setName("openerp.longpolling.request.%s" % current.ident)

                registry = odoo.registry(dbname)

                # immediatly returns if past notifications exist
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    notifications = env['bus.bus'].poll(channels, last, options)
                # or wait for future ones
                if not notifications:
                    event = self.Event()
                    for channel in channels:
                        self.channels.setdefault(hashable(channel), []).append(event)
                    try:
                        event.wait(timeout=timeout)
                        with registry.cursor() as cr:
                            env = api.Environment(cr, SUPERUSER_ID, {})
                            notifications = env['bus.bus'].poll(channels, last, options, force_status=True)
                    except Exception:
                        # timeout
                        pass
                return notifications

            def loop(self):
                """ Dispatch postgres notifications to the relevant polling threads/greenlets """
                _logger.info("Bus.loop listen imbus on db postgres")
                # PATCH !!
                with odoo.sql_db.db_connect(_get_imbus_db()).cursor() as cr:
                    conn = cr._cnx
                    cr.execute("listen imbus")
                    cr.commit();
                    while True:
                        if select.select([conn], [], [], TIMEOUT) == ([], [], []):
                            pass
                        else:
                            conn.poll()
                            channels = []
                            while conn.notifies:
                                channels.extend(json.loads(conn.notifies.pop().payload))
                            # dispatch to local threads/greenlets
                            events = set()
                            for channel in channels:
                                events.update(self.channels.pop(hashable(channel), []))
                            for event in events:
                                event.set()

            def run(self):
                while True:
                    try:
                        self.loop()
                    except Exception, e:
                        _logger.exception("Bus.loop error, sleep and retry")
                        time.sleep(TIMEOUT)

            def start(self):
                # PATCH !!
                # Force gevent mode
                self.Event = Event
                gevent.spawn(self.run)
                return self

        dispatch = ImDispatch().start()

        return locals()


patch_bus('odoo.addons.bus.models.bus')
