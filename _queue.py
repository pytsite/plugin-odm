"""PytSite ODM Plugin Queue
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pymongo.errors import PyMongoError
from bson import errors as bson_errors
from pytsite import mongodb, queue, logger, cache, reg

_QUEUE = queue.Queue('odm')
_ENTITIES_CACHE = cache.get_pool('odm.entities')
_CACHE_TTL = reg.get('odm.cache_ttl', 86400)


def _entity_save(args: dict):
    """Save an entity
    """
    fields_data = args['fields_data']
    collection = mongodb.get_collection(args['collection_name'])

    # Save data to the database
    try:
        # New entity
        if args['is_new']:
            collection.insert_one(fields_data)

        # Existing entity
        else:
            collection.replace_one({'_id': fields_data['_id']}, fields_data)

        # Update cache
        c_key = '{}.{}'.format(fields_data['_model'], fields_data['_id'])
        _ENTITIES_CACHE.put_hash(c_key, fields_data, _CACHE_TTL)

    except (bson_errors.BSONError, PyMongoError) as e:
        logger.error(e)
        logger.error('Document dump: {}'.format(fields_data))
        raise e


def _entity_delete(args: dict):
    # Delete from DB
    mongodb.get_collection(args['collection_name']).delete_one({'_id': args['_id']})

    # Update cache
    _ENTITIES_CACHE.rm('{}.{}'.format(args['model'], args['_id']))


def put(op: str, args: dict) -> queue.Queue:
    """Enqueue a task
    """
    if op == 'entity_save':
        return _QUEUE.put(_entity_save, args)
    elif op == 'entity_delete':
        return _QUEUE.put(_entity_delete, args)
    else:
        raise RuntimeError('Unsupported queue operation: {}'.format(op))
