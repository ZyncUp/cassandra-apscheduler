"""
This example demonstrates the use of the cassandra (using a datastax distribution) job store.
On each run, it adds a new alarm that fires after ten seconds.
You can exit the program, restart it and observe that any previous alarms that have not fired yet
are still active.

You can also give it various arguments, See the Cassandra documentation on how to construct these.
"""

from datetime import datetime, timedelta
import sys
import os

from apscheduler.schedulers.blocking import BlockingScheduler


def alarm(time):
    print('Alarm! This alarm was scheduled at %s.' % time)


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    # various other arguments as examples
    host = sys.argv[1] if len(sys.argv) > 1 else ['127.0.0.1']
    keyspace = sys.argv[2] if len(sys.argv) > 2 else 'apscheduler'
    tablename_jobs = sys.argv[3] if len(sys.argv) > 3 else 'apscheduler_jobs'
    tablename_scheduler = sys.argv[4] if len(sys.argv) > 3 else 'apscheduler_scheduler'

    scheduler.add_jobstore('cassandra', host=host, keyspace=keyspace, tablename_jobs=tablename_jobs,
                           tablename_scheduler=tablename_scheduler)
    alarm_time = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(alarm, 'date', run_date=alarm_time, args=[datetime.now()])
    print('To clear the alarms, delete the example.cassandra file.')
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
