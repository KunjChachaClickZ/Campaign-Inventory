from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({'status': 'success', 'message': 'Flask is working!'})

@app.route('/test')
def test():
    return jsonify({'status': 'success', 'message': 'Test endpoint working!'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5004))
    app.run(debug=True, port=port)


