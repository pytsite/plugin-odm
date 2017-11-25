"""PytSite ODM Plugin Queue
"""

from pymongo import errors as _pymonog_errors
from bson import errors as _bson_errors
from pytsite import mongodb as _db, queue as _queue, logger as _logger, cache as _cache, reg as _reg

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

_QUEUE = _queue.Queue('odm')
_ENTITIES_CACHE = _cache.get_pool('odm.entities')
_CACHE_TTL = _reg.get('odm.cache.ttl')


def _entity_save(args: dict):
    """Save an entity
    """
    fields_data = args['fields_data']
    collection = _db.get_collection(args['collection_name'])

    # Save data to the database
    try:
        # New entity
        if args['is_new']:
            collection.insert_one(fields_data)

        # Existing entity
        else:
            collection.replace_one({'_id': fields_data['_id']}, fields_data)

        # Update cache
        _ENTITIES_CACHE.put('{}.{}'.format(args['model'], fields_data['_id']), fields_data, _CACHE_TTL)

    except (_bson_errors.BSONError, _pymonog_errors.PyMongoError) as e:
        _logger.error(e)
        _logger.error('Document dump: {}'.format(fields_data))
        raise e


def _entity_delete(args: dict):
    # Delete from DB
    _db.get_collection(args['collection_name']).delete_one({'_id': args['_id']})

    # Update cache
    _ENTITIES_CACHE.rm('{}.{}'.format(args['model'], args['_id']))


def put(op: str, args: dict) -> _queue.Queue:
    """Enqueue a task
    """
    if op == 'entity_save':
        return _QUEUE.put('plugins.odm._queue._entity_save', args)
    elif op == 'entity_delete':
        return _QUEUE.put('plugins.odm._queue._entity_delete', args)
    else:
        raise RuntimeError('Unsupported queue operation: {}'.format(op))
