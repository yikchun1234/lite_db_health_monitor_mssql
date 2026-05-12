from flask import Flask, jsonify, request, render_template
import json

app = Flask(__name__)

# Load configurations
with open('config.json') as config_file:
    db_configs = json.load(config_file)

@app.route('/')
def index():
    return render_template('index.html') # Serves your HTML page

@app.route('/api/databases', methods=['GET'])
def get_databases():
    # Returns just the names for the dropdown
    return jsonify(list(db_configs.keys()))

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    db_name = request.args.get('db')
    if db_name not in db_configs:
        return jsonify({"error": "Database not found"}), 404

    config = db_configs[db_name]
    
    # --- IMPORTANT ---
    # Here is where you use your database library (psycopg2, pyodbc, cx_Oracle) 
    # to connect using the details in 'config' and run your queries.
    # For demonstration, returning mock data:
    
    mock_data = {
        "status": "Healthy",
        "datafile_size": "250 GB",
        "index_details": "All indexes optimized. No fragmentation > 10%.",
        "alerts": ["Warning: High CPU usage at 2 AM", "Info: Backup completed successfully"]
    }
    
    return jsonify(mock_data)

if __name__ == '__main__':
    # Runs a lightweight local server
    app.run(host='0.0.0.0', port=5000)
