-- Lua script for rate limiting
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current_time = redis.call('TIME')
local now = current_time[1] * 1000000 + current_time[2]

-- Remove old entries
redis.call('ZREMRANGEBYSCORE', key, 0, now - window * 1000000)

-- Get current count
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    return 1
else
    return 0
end
