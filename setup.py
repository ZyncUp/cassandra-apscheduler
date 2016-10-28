# coding: utf-8
import os.path

from setuptools import setup, find_packages


here = os.path.dirname(__file__)
readme_path = os.path.join(here, 'README.md')
readme = open(readme_path).read()

setup(
    name='CassandraAPScheduler',
    version='0.1.0',
    description='APScheduler that can use datastax cassandra as a jobstore',
    long_description=readme,
    author=u'Chris Coovrey',
    author_email='chris@zync-up.com',
    url='https://github.com/ccoovrey/cassandra-apscheduler',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7'
    ],
    keywords='scheduling cron cassandra',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    setup_requires=[
        'setuptools_scm'
    ],
    install_requires=[
        'setuptools >= 0.7',
        'six >= 1.4.0',
        'pytz',
        'tzlocal >= 1.2',
    ],
    extras_require={
        ':python_version == "2.7"': ['futures', 'funcsigs'],
        'asyncio:python_version == "2.7"': ['trollius'],
        'asyncio:python_version == "3.3"': ['asyncio'],
        'gevent': ['gevent'],
        'twisted': ['twisted'],
        'cassandra': ['cassandra-driver >= 3.6.0'],
        'sqlalchemy': ['sqlalchemy >= 0.8'],
        'mongodb': ['pymongo >= 2.8'],
        'rethinkdb': ['rethinkdb'],
        'redis': ['redis'],
        'tornado': ['tornado >= 4.3'],
        'zookeeper': ['kazoo']
    },
    zip_safe=False,
    entry_points={
        'apscheduler.triggers': [
            'date = apscheduler.triggers.date:DateTrigger',
            'interval = apscheduler.triggers.interval:IntervalTrigger',
            'cron = apscheduler.triggers.cron:CronTrigger'
        ],
        'apscheduler.executors': [
            'debug = apscheduler.executors.debug:DebugExecutor',
            'threadpool = apscheduler.executors.pool:ThreadPoolExecutor',
            'processpool = apscheduler.executors.pool:ProcessPoolExecutor',
            'asyncio = apscheduler.executors.asyncio:AsyncIOExecutor [asyncio]',
            'gevent = apscheduler.executors.gevent:GeventExecutor [gevent]',
            'tornado = apscheduler.executors.tornado:TornadoExecutor [tornado]',
            'twisted = apscheduler.executors.twisted:TwistedExecutor [twisted]'
        ],
        'apscheduler.jobstores': [
            'memory = apscheduler.jobstores.memory:MemoryJobStore',
            'cassandra = apscheduler.jobstores.cassandra:CassandraJobStore [cassandra]',
            'sqlalchemy = apscheduler.jobstores.sqlalchemy:SQLAlchemyJobStore [sqlalchemy]',
            'mongodb = apscheduler.jobstores.mongodb:MongoDBJobStore [mongodb]',
            'rethinkdb = apscheduler.jobstores.rethinkdb:RethinkDBJobStore [rethinkdb]',
            'redis = apscheduler.jobstores.redis:RedisJobStore [redis]',
            'zookeeper = apscheduler.jobstores.zookeeper:ZookeeperJobStore [zookeeper]'
        ]
    }
)
