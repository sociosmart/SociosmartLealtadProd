from redis import Redis

from core.config import settings

redis = Redis.from_url(str(settings.redis.redis_connection_uri))
