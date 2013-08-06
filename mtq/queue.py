'''
Created on Aug 2, 2013

@author: sean
'''
from bson.objectid import ObjectId
from datetime import datetime
from mtq.job import Job
from mtq.utils import now, is_str

class QueueError(Exception):
    pass

class Queue(object):
    '''
    A queue to enqueue an pop tasks
    
    Do not create directly use MTQConnection.queue 
    '''
    def __str__(self):
        return self.name
        
    def __init__(self, factory, name=u'default', tags=(), priority=0):
        
        self.name = name or u'default'
        self.factory = factory
        self.tags = tuple(tags) if tags else ()
        self.priority = priority
        

    def enqueue(self, func_or_str, *args, **kwargs):
        '''
        Creates a job to represent the delayed function call and enqueues
        it.
        
        Expects the function to call, along with the arguments and keyword
        arguments.
        
        The function argument `func_or_str` may be a function or a string representing the location of a function
        '''
        return self.enqueue_call(func_or_str, args, kwargs)
    
    def enqueue_call(self, func_or_str, args=(), kwargs=None, tags=(), priority=None, timeout=None):
        '''
        Creates a job to represent the delayed function call and enqueues
        it.
        
        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for MQ itself.
        '''
        if not is_str(func_or_str):
            name = getattr(func_or_str, '__name__', None)
            module = getattr(func_or_str, '__module__', None)
            
            if not (name and module):
                raise QueueError('can not enqueue %r (type %r)' % (func_or_str, type(func_or_str)))
            
            func_or_str = '%s.%s' % (module, name)
            
        if args is None:
            args = ()
        elif not isinstance(args, (list, tuple)):
            raise TypeError('argument args must be a tuple')
        if kwargs is None:
            kwargs = {}
        elif not isinstance(kwargs, dict):
            raise TypeError('argument kwargs must be a dict')
        
        execute = {'func_str': func_or_str, 'args':tuple(args), 'kwargs': dict(kwargs)}
        
        if priority is None:
            priority = self.priority
             
        doc = {
               'qname':self.name,
               'tags': self.tags + tuple(tags),
               
               'execute': execute,
               'process_after': now(),
               'enqueued_at': now(),
               'started_at': datetime.fromtimestamp(0),
               'finsished_at': datetime.fromtimestamp(0),
               'priority': priority,
               'processed': False,
               'failed': False,
               'timeout':timeout,
               'worker_id': ObjectId('000000000000000000000000'),
               }
    
        collection = self.factory.queue_collection
        collection.insert(doc)
        
        return Job(self.factory, doc)
    
    
    @property
    def _query(self):
        query = {'processed':False,
                'priority':{'$gte':self.priority},
                'process_after': {'$lte': now()},
                 }
        
        if self.name:
            query.update(qname=self.name)
            
        query.update(self._tag_query)
        return query
        
    @property
    def count(self):
        'The number of jobs in this queue (filtering by tags too)'
        collection = self.factory.queue_collection
        query = self.factory.make_query([self.name], self.tags, self.priority)
        return collection.find(query).count()
    
    @property
    def all_tags(self):
        'All the unique tags of jobs in this queue'
        collection = self.factory.queue_collection
        return collection.find({'qname':self.name}).distinct('tags')

    def pop(self, worker_id=None):
        'Pop a job off the queue'
        return self.factory.pop_item(worker_id, [self.name], self.tags, self.priority)
    
    def tag_count(self, tags):
        'Number of pending jobs in this queue with this tag'
        collection = self.factory.queue_collection
        
        if not isinstance(tags, (list, tuple)):
            tags = [tags]
        query = {'qname':self.name, 'processed':False}
        query.update(self.factory.make_tag_query(tags))
        
        return collection.find(query).count()
