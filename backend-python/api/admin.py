"""
System Administration API
Role-based access control, configuration management, and system monitoring
"""
import os
import json
import time
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from cryptography.fernet import Fernet
import threading
import subprocess
from pathlib import Path

# Import config classes
from config import DatabaseConfig, SparkConfig, EmailConfig, SystemConfig

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
logger = logging.getLogger(__name__)

# Encryption key for sensitive data
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# WebSocket connections for real-time logs
log_subscribers = set()

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user from session/token (simplified for demo)
        user_role = request.headers.get('X-User-Role', 'user')
        if user_role != 'admin':
            return jsonify({
                'code': 403,
                'message': 'Admin privileges required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def log_admin_operation(operation):
    """Decorator to log admin operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            try:
                result = f(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Log to system_log table
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'user_id': request.headers.get('X-User-ID', 'unknown'),
                    'operation': operation,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'request_params': json.dumps(request.json) if request.json else '{}',
                    'execution_time_ms': round(execution_time, 2),
                    'status': 'success',
                    'message': 'Operation completed successfully'
                }
                
                # In production, this would be saved to database
                logger.info(f"Admin operation logged: {log_entry}")
                
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Log error
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'user_id': request.headers.get('X-User-ID', 'unknown'),
                    'operation': operation,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'request_params': json.dumps(request.json) if request.json else '{}',
                    'execution_time_ms': round(execution_time, 2),
                    'status': 'error',
                    'message': str(e)
                }
                
                logger.error(f"Admin operation failed: {log_entry}")
                raise
        return decorated_function
    return decorator

def encrypt_sensitive_data(data):
    """Encrypt sensitive data like passwords"""
    if not data:
        return ''
    encrypted = cipher_suite.encrypt(data.encode())
    return encrypted.decode()

def decrypt_sensitive_data(encrypted_data):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return ''
    try:
        decrypted = cipher_suite.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        return '******'

@admin_bp.route('/config/database', methods=['GET'])
@require_admin
@log_admin_operation('get_database_config')
def get_database_config():
    """Get database configuration (with masked password)"""
    try:
        config = DatabaseConfig.from_env()
        
        # Mask password for display
        config_data = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'username': config.username,
            'password': '******' if config.password else '',
            'charset': config.charset,
            'pool_size': config.pool_size,
            'max_overflow': config.max_overflow,
            'pool_timeout': config.pool_timeout,
            'pool_recycle': config.pool_recycle
        }
        
        return jsonify({
            'code': 200,
            'data': config_data,
            'message': 'Database configuration retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Failed to get database config: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to retrieve database configuration: {str(e)}'
        }), 500

@admin_bp.route('/config/database', methods=['PUT'])
@require_admin
@log_admin_operation('update_database_config')
def update_database_config():
    """Update database configuration"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['host', 'port', 'database', 'username']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Encrypt password if provided
        encrypted_password = encrypt_sensitive_data(data.get('password', ''))
        
        # Update environment variables or config file
        config_updates = {
            'DB_HOST': data['host'],
            'DB_PORT': str(data['port']),
            'DB_NAME': data['database'],
            'DB_USER': data['username'],
            'DB_CHARSET': data.get('charset', 'utf8mb4'),
            'DB_POOL_SIZE': str(data.get('pool_size', 10)),
            'DB_MAX_OVERFLOW': str(data.get('max_overflow', 20)),
            'DB_POOL_TIMEOUT': str(data.get('pool_timeout', 30)),
            'DB_POOL_RECYCLE': str(data.get('pool_recycle', 3600))
        }
        
        if encrypted_password:
            config_updates['DB_PASSWORD_ENCRYPTED'] = encrypted_password
        
        # In production, this would update a secure configuration store
        logger.info(f"Database configuration updated by admin")
        
        return jsonify({
            'code': 200,
            'message': 'Database configuration updated successfully'
        })
    except Exception as e:
        logger.error(f"Failed to update database config: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to update database configuration: {str(e)}'
        }), 500

@admin_bp.route('/config/spark', methods=['GET'])
@require_admin
@log_admin_operation('get_spark_config')
def get_spark_config():
    """Get Spark configuration"""
    try:
        config = SparkConfig.from_env()
        
        config_data = {
            'app_name': config.app_name,
            'master': config.master,
            'executor_memory': config.executor_memory,
            'executor_cores': config.executor_cores,
            'driver_memory': config.driver_memory,
            'driver_cores': config.driver_cores,
            'dynamic_allocation': config.dynamic_allocation,
            'min_executors': config.min_executors,
            'max_executors': config.max_executors,
            'executor_memory_overhead': config.executor_memory_overhead,
            'default_parallelism': config.default_parallelism,
            'sql_shuffle_partitions': config.sql_shuffle_partitions
        }
        
        return jsonify({
            'code': 200,
            'data': config_data,
            'message': 'Spark configuration retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Failed to get Spark config: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to retrieve Spark configuration: {str(e)}'
        }), 500

@admin_bp.route('/config/spark', methods=['PUT'])
@require_admin
@log_admin_operation('update_spark_config')
def update_spark_config():
    """Update Spark configuration"""
    try:
        data = request.json
        
        # Update configuration
        config_updates = {
            'SPARK_APP_NAME': data.get('app_name', 'weibo-sentiment-analysis'),
            'SPARK_MASTER': data.get('master', 'local[*]'),
            'SPARK_EXECUTOR_MEMORY': data.get('executor_memory', '2g'),
            'SPARK_EXECUTOR_CORES': str(data.get('executor_cores', 2)),
            'SPARK_DRIVER_MEMORY': data.get('driver_memory', '1g'),
            'SPARK_DRIVER_CORES': str(data.get('driver_cores', 1)),
            'SPARK_DYNAMIC_ALLOCATION': str(data.get('dynamic_allocation', True)).lower(),
            'SPARK_MIN_EXECUTORS': str(data.get('min_executors', 1)),
            'SPARK_MAX_EXECUTORS': str(data.get('max_executors', 10)),
            'SPARK_EXECUTOR_MEMORY_OVERHEAD': str(data.get('executor_memory_overhead', 512)),
            'SPARK_DEFAULT_PARALLELISM': str(data.get('default_parallelism', 100)),
            'SPARK_SQL_SHUFFLE_PARTITIONS': str(data.get('sql_shuffle_partitions', 200))
        }
        
        # In production, this would update configuration files
        logger.info(f"Spark configuration updated by admin")
        
        return jsonify({
            'code': 200,
            'data': {
                'requires_restart': True,
                'message': 'Spark configuration updated. Restart required for changes to take effect.'
            },
            'message': 'Spark configuration updated successfully'
        })
    except Exception as e:
        logger.error(f"Failed to update Spark config: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to update Spark configuration: {str(e)}'
        }), 500

@admin_bp.route('/spark/restart', methods=['POST'])
@require_admin
@log_admin_operation('restart_spark_cluster')
def restart_spark_cluster():
    """Restart Spark cluster (dangerous operation)"""
    try:
        # Add confirmation check
        confirm = request.json.get('confirm', False)
        if not confirm:
            return jsonify({
                'code': 400,
                'message': 'Confirmation required for Spark restart operation'
            }), 400
        
        # Execute restart script (simplified for demo)
        def restart_spark():
            try:
                # In production, this would be a proper Spark restart script
                script_path = Path(__file__).parent.parent / 'scripts' / 'restart_spark.sh'
                if script_path.exists():
                    result = subprocess.run(['bash', str(script_path)], 
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        logger.info("Spark cluster restarted successfully")
                    else:
                        logger.error(f"Spark restart failed: {result.stderr}")
                else:
                    logger.warning("Spark restart script not found, simulating restart")
                    time.sleep(2)  # Simulate restart time
                    
            except subprocess.TimeoutExpired:
                logger.error("Spark restart timed out")
            except Exception as e:
                logger.error(f"Spark restart error: {e}")
        
        # Run restart in background
        thread = threading.Thread(target=restart_spark)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': 'Spark cluster restart initiated. This may take a few minutes.',
            'status': 'restarting'
        })
    except Exception as e:
        logger.error(f"Failed to restart Spark cluster: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to restart Spark cluster: {str(e)}'
        }), 500

@admin_bp.route('/logs/stream', methods=['GET'])
@require_admin
def stream_logs():
    """WebSocket endpoint for real-time log streaming"""
    # This would be implemented with Flask-SocketIO or similar
    # For now, return SSE endpoint
    def generate():
        try:
            log_file = Path(__file__).parent.parent / 'logs' / 'app.log'
            if not log_file.exists():
                yield f"data: {json.dumps({'level': 'INFO', 'message': 'Log file not found', 'timestamp': datetime.now().isoformat()})}\n\n"
                return
            
            # Simulate tail -f
            with open(log_file, 'r') as f:
                f.seek(0, 2)  # Go to end of file
                while True:
                    line = f.readline()
                    if line:
                        try:
                            log_data = {
                                'level': 'INFO',
                                'message': line.strip(),
                                'timestamp': datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(log_data)}\n\n"
                        except Exception as e:
                            logger.error(f"Error processing log line: {e}")
                    else:
                        time.sleep(1)
        except Exception as e:
            logger.error(f"Error in log streaming: {e}")
            yield f"data: {json.dumps({'level': 'ERROR', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return current_app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

@admin_bp.route('/logs', methods=['GET'])
@require_admin
@log_admin_operation('get_system_logs')
def get_system_logs():
    """Get system logs with filtering"""
    try:
        level = request.args.get('level', 'ALL')
        limit = int(request.args.get('limit', 100))
        
        # In production, this would query from system_log table
        logs = []
        for i in range(min(limit, 50)):  # Simulate logs
            logs.append({
                'id': i + 1,
                'level': ['INFO', 'WARNING', 'ERROR', 'DEBUG'][i % 4],
                'message': f'Sample log message {i + 1}',
                'timestamp': datetime.now().isoformat(),
                'module': 'system',
                'user_id': 'admin'
            })
        
        # Filter by level
        if level != 'ALL':
            logs = [log for log in logs if log['level'] == level]
        
        return jsonify({
            'code': 200,
            'data': logs,
            'message': 'System logs retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to retrieve system logs: {str(e)}'
        }), 500

@admin_bp.route('/system/metrics', methods=['GET'])
@require_admin
@log_admin_operation('get_system_metrics')
def get_system_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics = {
            'cpu': {
                'usage': cpu_percent,
                'cores': psutil.cpu_count()
            },
            'memory': {
                'total': memory.total // (1024 * 1024),  # MB
                'used': memory.used // (1024 * 1024),    # MB
                'usage': memory.percent
            },
            'disk': {
                'total': disk.total // (1024 * 1024),    # MB
                'used': disk.used // (1024 * 1024),      # MB
                'usage': (disk.used / disk.total) * 100
            },
            'application': {
                'onlineUsers': 5,  # Would come from session store
                'requestsPerMinute': 120,  # Would come from metrics
                'avgResponseTime': 245.6,  # Would come from metrics
                'errorRate': 0.2  # Would come from metrics
            }
        }
        
        return jsonify({
            'code': 200,
            'data': metrics,
            'message': 'System metrics retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to retrieve system metrics: {str(e)}'
        }), 500

@admin_bp.route('/users', methods=['GET'])
@require_admin
@log_admin_operation('get_users')
def get_users():
    """Get all users with role-based access"""
    try:
        # In production, this would query from database
        users = [
            {
                'id': 1,
                'username': 'admin',
                'name': 'Administrator',
                'email': 'admin@example.com',
                'role': 'admin',
                'status': 'active',
                'lastLoginAt': datetime.now().isoformat(),
                'createdAt': datetime.now().isoformat()
            },
            {
                'id': 2,
                'username': 'user1',
                'name': 'Regular User',
                'email': 'user1@example.com',
                'role': 'user',
                'status': 'active',
                'lastLoginAt': datetime.now().isoformat(),
                'createdAt': datetime.now().isoformat()
            }
        ]
        
        return jsonify({
            'code': 200,
            'data': users,
            'message': 'Users retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to retrieve users: {str(e)}'
        }), 500

@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@require_admin
@log_admin_operation('update_user_role')
def update_user_role(user_id):
    """Update user role"""
    try:
        data = request.json
        new_role = data.get('role')
        
        if new_role not in ['admin', 'user']:
            return jsonify({
                'code': 400,
                'message': 'Invalid role. Must be admin or user'
            }), 400
        
        # In production, this would update the database
        logger.info(f"User {user_id} role updated to {new_role}")
        
        return jsonify({
            'code': 200,
            'message': 'User role updated successfully'
        })
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        return jsonify({
            'code': 500,
            'message': f'Failed to update user role: {str(e)}'
        }), 500
