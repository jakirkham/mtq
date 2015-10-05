# -*- coding: utf-8 -*-
"""
Compatibility layer for writing pymongo3.x looking code that works on both
pymongo2.8 and 3.x
"""
# Third party imports
import bson
import pymongo


# Constants
PYMONGO_28 = pymongo.version_tuple == (2, 8)
PYMONGO_3 = pymongo.version_tuple[0] == 3
RENAME_MAP = {'filter': 'spec',
              'projection': 'fields',
              'allow_partial_results': 'partial'}


class Error(Exception):
    pass


class PyMongoVersionError(Error):
    pass


class PyMongoMigrationHelperError(Error):
    pass


class _CodecOptions:
    """
    Mock CodecOption object for use with pymongo 2.8.

    http://api.mongodb.org/python/3.0/api/bson/codec_options.html#bson.codec_options.CodecOptions
    """
    def __init__(self, document_class):
        self.document_class = document_class


def _mongo_client(*args, **kwargs):
    """
    Helper function for use with pymongo 2.8 that returns either a MongoClient
    or a MongoReplicaSetClient.

    In pymongo 3.x there is a single client.

    http://api.mongodb.org/python/3.0/changelog.html#mongoclient-changes
    """
    if getattr(kwargs, 'replicaSet', None):
        MongoClient = pymongo.mongo_replica_set_client.MongoReplicaSetClient
    else:
        MongoClient = pymongo.mongo_client.MongoClient

    return MongoClient(*args, **kwargs)


if PYMONGO_28:
    CodecOptions = _CodecOptions
    MongoClient = _mongo_client
elif PYMONGO_3:
    CodecOptions = bson.codec_options.CodecOptions
    MongoClient = pymongo.mongo_client.MongoClient
else:
    raise PyMongoVersionError


def _fix_kwargs(kwargs):
    """
    Adapt the kwargs so that renamed keywords are passed to the method
    according to the correct version.

    http://api.mongodb.org/python/3.0/changelog.html#collection-changes
    """
    for new_key in RENAME_MAP:
        if new_key in kwargs:
            old_key = RENAME_MAP[new_key]
            kwargs[old_key] = kwargs.pop(new_key)
    return kwargs


def _find_like_method(*args, **kwargs):
    """
    Helper method that adapts the find_like methods so that code looks like
    pymongo3.x but can run on both 2.8 and 3.x series
    """
    collection = kwargs.pop('collection', None)
    method = kwargs.pop('find_like_method', None)
    func = getattr(collection, method, None)

    if not collection or not method or not func:
        raise PyMongoMigrationHelperError

    if PYMONGO_28:
        kwargs = _fix_kwargs(kwargs)
        kwargs['as_class'] = collection._as_class
        cursor_or_document = func(*args, **kwargs)
    elif PYMONGO_3:
        cursor_or_document = func(*args, **kwargs)
    else:
        raise PyMongoVersionError

    return cursor_or_document


def find(*args, **kwargs):
    """
    Wraps the find method making the syntax similar to pymongo3.x.
    """
    kwargs['find_like_method'] = 'find'
    return _find_like_method(*args, **kwargs)


def find_and_modify(*args, **kwargs):
    """
    Wraps the find_and_modify method making the syntax similar to pymongo3.x.
    """
    kwargs['find_like_method'] = 'find_and_modify'
    return _find_like_method(*args, **kwargs)


def find_one(*args, **kwargs):
    """
    Wraps the find_one method making the syntax similar to pymongo3.x.
    """
    kwargs['find_like_method'] = 'find_one'
    return _find_like_method(*args, **kwargs)


def with_options(codec_options=None, collection=None):
    """
    Helper method for using a document_class (as_class) in pymongo 2.8.

    http://api.mongodb.org/python/3.0/api/pymongo/collection.html#pymongo.collection.Collection.with_options
    """
    if not collection or not codec_options:
        raise PyMongoMigrationHelperError

    if PYMONGO_28:
        collection._as_class = codec_options.document_class
    elif PYMONGO_3:
        collection = collection.with_options(codec_options=codec_options)
    else:
        raise PyMongoVersionError

    return collection