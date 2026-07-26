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