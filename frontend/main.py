from flask import Flask, render_template, request
from pymongo import MongoClient
from config import *

app = Flask(__name__)

# MongoDB setup
client = MongoClient(mongo_url)
db = client[db_name]
collection = db[collection_name]

# Homepage - Select date or agent name
@app.route('/')
def index():
    # Get distinct dates and agent names from MongoDB for selection
    dates = collection.distinct('Date')
    agent_names = collection.distinct('agent_name')
    return render_template('index.html', dates=dates, agent_names=agent_names)

# Redirect based on date or agent name selection
@app.route('/data', methods=['POST'])
def data():
    selected_date = request.form.get('date')
    selected_agent = request.form.get('agent_name')
    
    query = {}
    if selected_date:
        query['Date'] = selected_date
    if selected_agent:
        query['agent_name'] = selected_agent
    
    # Fetch data from MongoDB
    records = list(collection.find(query, {'Filename': 1, 'Date': 1, 'Call_Duration': 1, 'Processed_Audio_Duration': 1, 'call_type': 1, 'agent_name': 1
    }).sort('Filename', 1))
    return render_template('data.html', records=records)

# Call details page
@app.route('/call_data/<filename>')
def call_data(filename):
    # Fetch the specific document from MongoDB
    record = collection.find_one({'Filename': filename})
    return render_template('call_data.html', record=record)

if __name__ == '__main__':
    app.run(debug=True, host="172.16.101.152", port=5000)