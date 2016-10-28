from __future__ import absolute_import

from apscheduler.jobstores.base import BaseJobStore, JobLookupError
from apscheduler.job import Job
import datetime as dt
import pytz

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle

try:
    from cassandra.cqlengine import connection
    from cassandra.policies import WhiteListRoundRobinPolicy
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.cqlengine.models import Model, columns
    from cassandra.cqlengine.management import sync_table
    from uuid import UUID, uuid1
    from datetime import datetime

except ImportError:  # pragma: nocover
    raise ImportError('CassandraJobStore requires cassandra-driver-dse installed')

DESC = 'DESC'
ASC = 'ASC'


class CassandraJobStore(BaseJobStore):
    """
    Stores jobs in a database table and materialized view using datastax
    cassandra. The table and materialized view will be created if it
    doesn't exist in the cluster.

    Plugin alias: ``cassandra``

    :param host: ip address of the cluster, if not supplied will default to
        a localhost ['127.0.0.1']
    :param str keyspace: a keyspace must be created with associated topology and
        replication factor, default name for keyspace is ``apscheduler''
    :param str tablename_jobs: name of the table to store jobs
    :param str tablename_scheduler: name of the materialized view to store job schedules
    :param metadata: a :class:`~sqlalchemy.MetaData` instance to use instead of creating a new one
    :param int pickle_protocol: pickle protocol level to use (for serialization), defaults to the
        highest available
    :param connect_args: other datastax cassandra arguments for connection
    """
    def __init__(self, host=['127.0.0.1'], keyspace='apscheduler', tablename_jobs='apscheduler_jobs',
                 tablename_scheduler='apscheduler_scheduler', pickle_protocol=pickle.HIGHEST_PROTOCOL,
                 **connect_args):
        super(CassandraJobStore, self).__init__()
        self.utc = pytz.utc
        self.keyspace = keyspace
        self.tablename_jobs = tablename_jobs
        self.tablename_scheduler = tablename_scheduler
        self.pickle_protocol = pickle_protocol
        connection.setup(host, keyspace, **connect_args)
        self.conn = connection.session

        class APSchedulerJobs(Model):
            id = columns.UUID(partition_key=True)
            year = columns.Integer(primary_key=True)
            month = columns.Integer(primary_key=True)
            day = columns.Integer(primary_key=True)
            hour = columns.Integer(primary_key=True)
            next_run_time = columns.DateTime()
            job_state = columns.Blob()

        APSchedulerJobs.__keyspace__ = self.keyspace
        APSchedulerJobs.__table_name__ = self.tablename_jobs

        class APSchedulerSchedule(Model):
            year = columns.Integer(partition_key=True)
            month = columns.Integer(partition_key=True)
            day = columns.Integer(partition_key=True)
            hour = columns.Integer(partition_key=True)
            next_run_time = columns.DateTime(primary_key=True)
            id = columns.UUID(primary_key=True)
            job_state = columns.Blob(required=True)

        APSchedulerSchedule.__keyspace__ = self.keyspace
        APSchedulerSchedule.__table_name__ = self.tablename_scheduler

        self.jobs_t = APSchedulerJobs
        self.sched_t = APSchedulerSchedule

        sync_table(self.jobs_t)
        # insert materialized view
        mv = ("CREATE MATERIALIZED VIEW IF NOT EXISTS {0}.{1} AS " +
              "SELECT * " +
              "FROM {2} " +
              "WHERE year IS NOT NULL and month IS NOT NULL and day IS NOT NULL and hour IS NOT NULL and " +
              "next_run_time IS NOT NULL and id IS NOT NULL " +
              "PRIMARY KEY((year, month, day, hour), next_run_time, id);")
        self.conn.execute(mv.format(self.keyspace, self.tablename_scheduler, self.tablename_jobs))

    def start(self, scheduler, alias):
        super(CassandraJobStore, self).start(scheduler, alias)

    def lookup_job(self, job_id):
        jobs = [i for i in self.jobs_t.filter(id=job_id)]
        job = None
        if len(jobs) > 1:
            raise Exception("More than 1 job with the same id: {0}".format(job_id))
        elif len(jobs) == 1:
            job = jobs[0]

        return self._reconstitute_job(job.job_state) if job else None

    # now is a datetime
    def get_due_jobs(self, now):
        tm = self.get_utc_time(now)
        out = [i for i in self.sched_t.filter(year=tm.year, month=tm.month, day=tm.day, hour=tm.hour,
                                              next_run_time__lte=tm)]
        for i in range(12):
            tm = tm - dt.timedelta(hours=1)
            out.extend([i for i in self.sched_t.filter(year=tm.year, month=tm.month, day=tm.day, hour=tm.hour)])

        for i in out:
            i.next_run_time = i.next_run_time.replace(tzinfo=now.tzinfo)
        return self._get_jobs(out)

    def get_next_run_time(self):
        now = datetime.utcnow()
        result = self.sched_t.filter(year=now.year, month=now.month, day=now.day, hour=now.hour,
                                     next_run_time__gte=now).limit(1)
        if len(result) != 1:
            for i in range(24):
                now = now + dt.timedelta(hours=1)
                result = self.sched_t.filter(year=now.year, month=now.month, day=now.day, hour=now.hour).limit(1)
                if len(result) == 1:
                    break

        return result[0].next_run_time.replace(tzinfo=self.utc) if result else None

    def get_all_jobs(self):
        jobs = [i for i in self.jobs_t.filter().limit(100)]
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def get_utc_time(self, tm):
        assert isinstance(tm, datetime)
        if tm.tzname() is None:
            return tm
        return tm.astimezone(self.utc).replace(tzinfo=None)

    def add_job(self, job):
        d = self.get_utc_time(job.next_run_time)
        self.jobs_t.create(id=job.id, year=d.year, month=d.month, day=d.day, hour=d.hour,
                           next_run_time=job.next_run_time,
                           job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol))

    def update_job(self, job):
        if self.lookup_job(job.id) is None:
            raise JobLookupError(id)
        else:
            d = job.next_run_time.astimezone(self.utc).replace(tzinfo=None)
            self.remove_job(job.id)
            self.jobs_t.create(id=job.id, year=d.year, month=d.month, day=d.day, hour=d.hour,
                               next_run_time=d, job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol))

    def remove_job(self, job_id):
        [i.delete() for i in self.jobs_t.filter(id=job_id)]

    def remove_all_jobs(self):
        results = self.get_all_jobs()
        for row in results:
            self.jobs_t.filter(id=row.id).delete()

    def shutdown(self):
        pass

    def _reconstitute_job(self, job_state):
        job_state = pickle.loads(job_state)
        job_state['jobstore'] = self
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, results):
        jobs = []
        for row in results:
            jobs.append(self._reconstitute_job(self.jobs_t.get(id=row['id']).job_state))
        return jobs

    def __repr__(self):
        return '<%s (url=%s)>' % (self.__class__.__name__, self.engine.url)
