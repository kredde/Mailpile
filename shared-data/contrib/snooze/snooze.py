from mailpile.i18n import gettext as _
from mailpile.commands import Command
from mailpile.urlmap import UrlMap
from mailpile.workers import Cron

class snoozeCommand(Command):
    """ API command to schedule snooze tag removal """

    cron_worker = None

    SYNOPSIS_ARGS = '[<data to hash>]'
    SPLIT_ARG = False
    HTTP_CALLABLE = ('GET', 'POST')
    HTTP_QUERY_VARS = {
       'data': 'Data to hash'
    }    

    def command(self):
        # the id of the message
        data = self.args[0]

        # the time in seconds to schedule tag removal
        time = int(self.args[1])

        def task():
            """ the task that untags the coversation and marks it as new """

            post_data =  {
                'csrf': self.session.ui.html_variables['csrf_token'],
                'add': ['new', 'inbox'],
                'del': ['snooze'],
                'mid': [data]
            }
            um = UrlMap(self.session)
            commands = um.map(None, 'POST', '/api/0/tag/', {}, post_data)
            commands[1].run()
            
            # cancel the task after it has been performed one time
            self.cron_worker.cancel_task(data)
            
        # initialize the cronworker
        if not self.cron_worker:
            self.cron_worker = Cron({}, 'snoozeWorker', self.session)
            self.cron_worker.start()

        # schedule the tag removal task
        # params: name, seconds, task
        self.cron_worker.add_task(data, time, task)

        return self._success(_('success'))
