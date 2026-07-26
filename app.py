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

if __name__ == '__main__':
    app.run(debug=True)