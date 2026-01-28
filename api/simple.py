from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({"message": "Hello from Vercel!"})

@app.route('/test')
def test():
    return jsonify({"status": "working", "platform": "vercel"})

handler = app