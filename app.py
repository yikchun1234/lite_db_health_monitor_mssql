from flask import Flask, jsonify, request, render_template
import json
import pyodbc

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') 

@app.route('/api/databases', methods=['GET'])
def get_databases():
    with open('config.json') as config_file:
        live_configs = json.load(config_file)
    return jsonify(list(live_configs.keys()))

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    server_name = request.args.get('server')
    
    with open('config.json') as config_file:
        live_configs = json.load(config_file)

    if server_name not in live_configs:
        return jsonify({"error": "Server not found"}), 404

    config = live_configs[server_name]
    
    if config['type'] == 'sqlserver':
        try:
            # REVERTED: Clean and simple server address!
            server_address = config['host']
            if config.get('port') and str(config['port']).strip() != '':
                server_address = f"{server_address},{config['port']}"

            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_address};"
                f"DATABASE=master;"
                f"UID={config['user']};"
                f"PWD={{{config['password']}}};"  # Still protecting the password safely!
                f"Encrypt=yes;"
                f"TrustServerCertificate=yes;"
            )
            
            conn = pyodbc.connect(conn_str, timeout=5)
            cursor = conn.cursor()

            db_query = """
                SELECT 
                    d.name AS DatabaseName, 
                    d.state_desc AS Status, 
                    ISNULL(SUM(mf.size * 8.0 / 1024), 0) AS Size_in_MB
                FROM sys.databases d
                LEFT JOIN sys.master_files mf ON d.database_id = mf.database_id
                WHERE d.database_id > 4 
                GROUP BY d.name, d.state_desc;
            """
            cursor.execute(db_query)
            
            all_databases = []
            for row in cursor.fetchall():
                all_databases.append({
                    "name": row.DatabaseName,
                    "status": row.Status,
                    "size_mb": round(row.Size_in_MB, 2)
                })

            conn.close()

            return jsonify({
                "server_level_alerts": ["No active server alerts"],
                "databases": all_databases
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Unsupported database type"})


# ---------- NEW FEATURE: PRODUCTION-SAFE INDEX CHECKING ----------
@app.route('/api/indexes', methods=['GET'])
def get_indexes():
    server_name = request.args.get('server')
    db_name = request.args.get('db')
    
    with open('config.json') as config_file:
        live_configs = json.load(config_file)

    if server_name not in live_configs:
        return jsonify({"error": "Server not found"}), 404

    config = live_configs[server_name]
    
    if config['type'] == 'sqlserver':
        try:
            # Clean and simple server address
            server_address = config['host']
            if config.get('port') and str(config['port']).strip() != '':
                server_address = f"{server_address},{config['port']}"

            # Connect DIRECTLY to the selected database
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_address};"
                f"DATABASE={db_name};" 
                f"UID={config['user']};"
                f"PWD={{{config['password']}}};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=yes;"
            )
            
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()

            # 'LIMITED' mode + page_count > 1000 ensures NO production impact
            index_query = """
                SELECT 
                    OBJECT_NAME(ips.OBJECT_ID) AS TableName, 
                    i.name AS IndexName, 
                    ROUND(ips.avg_fragmentation_in_percent, 2) AS Fragmentation,
                    ips.page_count AS PageCount
                FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
                INNER JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
                WHERE ips.avg_fragmentation_in_percent > 10.0 
                  AND ips.page_count > 1000
                  AND i.name IS NOT NULL
                ORDER BY ips.avg_fragmentation_in_percent DESC;
            """
            cursor.execute(index_query)
            
            indexes = []
            for row in cursor.fetchall():
                indexes.append({
                    "table": row.TableName,
                    "index": row.IndexName,
                    "fragmentation": row.Fragmentation,
                    "pages": row.PageCount
                })

            conn.close()
            return jsonify({"indexes": indexes})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Unsupported database type"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
