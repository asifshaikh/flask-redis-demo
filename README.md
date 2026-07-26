# Flask + Redis Caching Demo

This project demonstrates how **Redis caching** can significantly
improve the response time of a Flask API.

The Flask application fetches posts from the JSONPlaceholder API:

`https://jsonplaceholder.typicode.com/posts`

The experiment is performed in two stages:

1.  Fetch the data directly from the external API without using cached
    data.
2.  Store the API response in Redis and serve subsequent requests from
    the Redis cache.

The response times are then compared using Postman.

---

## Architecture

### Without Cache

```text
Postman
   |
   | GET /posts
   v
Flask Application
   |
   | HTTP GET
   v
JSONPlaceholder API
   |
   v
Flask
   |
   v
Postman
```

Every request requires the Flask application to contact the external
API.

### With Redis Cache

```text
Postman
   |
   | GET /posts
   v
Flask Application
   |
   | Check "posts"
   v
Redis
   |
   +---- Cache HIT ----> Return cached data
   |
   +---- Cache MISS ---> JSONPlaceholder API
                            |
                            v
                       Store in Redis
                            |
                            v
                         Response
```

This follows the **cache-aside pattern**.

---

## Prerequisites

Make sure the following are installed:

- Python 3
- pip
- Docker
- Postman

Verify the installations:

```bash
python --version
pip --version
docker --version
```

---

## 1. Create the Flask Project

Create a project directory:

```bash
mkdir flask-redis-demo
cd flask-redis-demo
```

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

Install the required Python packages:

```bash
pip install flask requests redis
```

The packages are used for:

- **Flask** --- creating the REST API.
- **requests** --- calling the JSONPlaceholder API.
- **redis** --- communicating with the Redis server.

---

## 2. Flask API Without Caching

Create an `app.py` file:

```python
from flask import Flask, jsonify
import requests

app = Flask(__name__)

API_URL = "https://jsonplaceholder.typicode.com/posts"

@app.route('/', methods=['GET'])
def get_posts():
    response = requests.get(API_URL)
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
```

Start the Flask application:

```bash
python app.py
```

The application will be available at:

`http://localhost:5000`

Call the endpoint from Postman:

```text
GET http://localhost:5000/posts
```

---

## 3. Response Time Before Caching

Before Redis caching is used, Flask must contact JSONPlaceholder to
retrieve the posts.

In this test, Postman reported a response time of approximately **1725
ms**.

![Response time before Redis
caching](assets/image.png)

The request flow is:

```text
Postman → Flask → JSONPlaceholder → Flask → Postman
```

The external network request contributes significantly to the total
response time.

---

## 4. Start Redis Using Docker

Redis can be started without installing it directly on the host machine
by using Docker:

```bash
docker run -d \
  --name redis-server \
  -p 6379:6379 \
  redis:latest
```

Verify that the container is running:

```bash
docker ps
```

Redis listens on port `6379` by default.

Test the Redis server:

```bash
docker exec -it redis-server redis-cli
```

Inside Redis CLI:

```text
PING
```

Expected response:

```text
PONG
```

---

## 5. Add Redis Caching to Flask

Update `app.py`:

```python
from flask import Flask, jsonify
import requests
import redis

app = Flask(__name__)

API_URL = "https://jsonplaceholder.typicode.com/posts"

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

CACHE_EXPIRATION = 60  # Cache expiration time in seconds
CACHE_KEY = "posts"

@app.route('/', methods=['GET'])
def get_posts():
    # Check if the data is already cached in Redis
    cached_data = redis_client.get(CACHE_KEY)
    if cached_data:
        return jsonify(eval(cached_data))

    # Fetch the data from the API
    response = requests.get(API_URL)
    # Cache the data in Redis
    redis_client.setex(CACHE_KEY, CACHE_EXPIRATION, str(response.json()))
    return jsonify(response.json())

@app.route('/clear_cache', methods=['DELETE'])
def clear_cache():
    # Clear the cached data in Redis
    redis_client.delete(CACHE_KEY)
    return jsonify({"message": "Cache cleared successfully."})
if __name__ == '__main__':
    app.run(debug=True)
```

---

## 6. Cache MISS

The first request after the cache is empty follows this flow:

```text
GET /posts
    |
    v
Flask
    |
    v
Redis
    |
    | Key "posts" not found
    v
CACHE MISS
    |
    v
JSONPlaceholder
    |
    v
Store result in Redis
    |
    v
Return response
```

The response is stored under the Redis key:

```text
posts
```

with a TTL of 60 seconds.

---

## 7. Response Time After Caching

Send the same request again before the cache expires:

```text
GET http://localhost:5000/posts
```

This time Redis already contains the posts, producing a **cache HIT**.

In this test, Postman reported a response time of approximately **9
ms**.

![Response time after Redis
caching](assets/image-1.png)

The request flow is now:

```text
Postman → Flask → Redis → Flask → Postman
```

The Flask application does **not** need to contact JSONPlaceholder for
this request.

### Performance Comparison

Request Data Source Postman Time

---

Before caching JSONPlaceholder API 1725 ms
After caching Redis 9 ms

For this particular test, the cached request was about **192× faster**
based on the Postman timings.

> Actual response times will vary depending on network conditions,
> machine performance, Docker, and the external API. The important
> observation is that a cache HIT avoids the external HTTP request.

---

## 8. Verify the Cache in Redis CLI

Open Redis CLI:

```bash
docker exec -it redis-server redis-cli
```

List the keys:

```text
KEYS *
```

The `posts` key can be seen in Redis.

Check how long the key has before it expires:

```text
TTL posts
```

Example from this test:

![Redis CLI showing the posts key and
TTL](assets/image-2.png)

The screenshot shows:

```text
KEYS *
1) "posts"

TTL posts
(integer) 48
```

This means the `posts` key exists and has approximately **48 seconds
remaining** before Redis automatically removes it.

You can also inspect the cached value:

```text
GET posts
```

---

## 9. Understanding the TTL

The cache is created using:

```python
redis_client.setex(CACHE_KEY, CACHE_EXPIRATION, str(response.json()))
```

where:

```python
CACHE_TTL = 60
```

Therefore:

```text
First request
     |
     v
CACHE MISS
     |
     v
Fetch from API
     |
     v
Store in Redis for 60 seconds
     |
     v
Subsequent requests → CACHE HIT
     |
     v
60 seconds expire
     |
     v
Redis removes the key
     |
     v
Next request → CACHE MISS
```

TTL prevents cached information from remaining in Redis indefinitely and
provides a simple way to refresh potentially stale data.

---

## 10. Useful Redis Commands

```text
PING
```

Check whether Redis is responding.

```text
KEYS *
```

Display keys currently stored in Redis. This is convenient for a small
development/demo environment.

```text
GET posts
```

Retrieve the cached posts.

```text
TTL posts
```

Check the remaining lifetime of the cache entry.

```text
DEL posts
```

Delete the cache manually.

After running:

```text
DEL posts
```

the next `/posts` request will be a cache MISS and will fetch fresh data
from JSONPlaceholder.

---

## Conclusion

This demo shows the core idea behind application caching with Redis.

Without caching:

```text
Client → Flask → External API → Flask → Client
```

With a cache HIT:

```text
Client → Flask → Redis → Flask → Client
```

In the captured test:

```text
Without cached data : 1725 ms
With Redis cache    :    9 ms
```

Redis is not making the JSONPlaceholder API itself faster. Instead, it
improves the application's response time by allowing Flask to **avoid
making the external API request** when the required data is already
cached.

This same concept can be applied to expensive database queries,
third-party API responses, computed results, sessions, and other
frequently accessed data.
