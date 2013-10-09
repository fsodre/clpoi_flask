import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/q/<city>')
def query(city):
    return 'Query: %s' % city
