#!/bin/bash

# Spark Cluster Restart Script
# This script safely restarts the Spark cluster
# Use with caution - this will terminate all running Spark jobs

set -e

LOG_FILE="/var/log/spark_restart.log"
SPARK_HOME="/opt/spark"
SPARK_MASTER_URL="spark://localhost:7077"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if Spark master is running
is_spark_master_running() {
    if pgrep -f "spark.master.Master" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if Spark workers are running
is_spark_worker_running() {
    if pgrep -f "spark.worker.Worker" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to stop Spark cluster
stop_spark_cluster() {
    log_message "Stopping Spark cluster..."
    
    # Stop Spark workers first
    if is_spark_worker_running; then
        log_message "Stopping Spark workers..."
        pkill -f "spark.worker.Worker" || true
        sleep 5
    fi
    
    # Stop Spark master
    if is_spark_master_running; then
        log_message "Stopping Spark master..."
        pkill -f "spark.master.Master" || true
        sleep 5
    fi
    
    # Force kill if still running
    if is_spark_master_running || is_spark_worker_running; then
        log_message "Force killing Spark processes..."
        pkill -9 -f "spark." || true
        sleep 2
    fi
    
    log_message "Spark cluster stopped"
}

# Function to start Spark cluster
start_spark_cluster() {
    log_message "Starting Spark cluster..."
    
    # Start Spark master
    log_message "Starting Spark master..."
    cd "$SPARK_HOME"
    ./sbin/start-master.sh
    
    # Wait for master to start
    sleep 10
    
    # Start Spark worker
    log_message "Starting Spark worker..."
    ./sbin/start-worker.sh "$SPARK_MASTER_URL"
    
    # Wait for worker to start
    sleep 5
    
    # Verify cluster is running
    if is_spark_master_running && is_spark_worker_running; then
        log_message "Spark cluster started successfully"
        return 0
    else
        log_message "Failed to start Spark cluster"
        return 1
    fi
}

# Function to get Spark status
get_spark_status() {
    log_message "Getting Spark cluster status..."
    
    if is_spark_master_running; then
        log_message "Spark Master: RUNNING"
    else
        log_message "Spark Master: STOPPED"
    fi
    
    if is_spark_worker_running; then
        log_message "Spark Worker: RUNNING"
    else
        log_message "Spark Worker: STOPPED"
    fi
    
    # Try to get cluster info from master UI
    if command -v curl > /dev/null && is_spark_master_running; then
        log_message "Attempting to get cluster info from master UI..."
        curl -s "http://localhost:8080" > /dev/null && log_message "Spark Master UI accessible" || log_message "Spark Master UI not accessible"
    fi
}

# Main execution
main() {
    log_message "Starting Spark cluster restart process..."
    
    # Check if running as root (required for system operations)
    if [[ $EUID -ne 0 ]]; then
        log_message "This script must be run as root"
        exit 1
    fi
    
    # Get current status
    get_spark_status
    
    # Stop cluster
    stop_spark_cluster
    
    # Wait a bit before starting
    log_message "Waiting 10 seconds before starting cluster..."
    sleep 10
    
    # Start cluster
    if start_spark_cluster; then
        log_message "Spark cluster restart completed successfully"
        
        # Final status check
        get_spark_status
        
        exit 0
    else
        log_message "Spark cluster restart failed"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "status")
        get_spark_status
        ;;
    "stop")
        stop_spark_cluster
        ;;
    "start")
        start_spark_cluster
        ;;
    "restart")
        main
        ;;
    *)
        echo "Usage: $0 {status|stop|start|restart}"
        echo "  status  - Show Spark cluster status"
        echo "  stop    - Stop Spark cluster"
        echo "  start   - Start Spark cluster"
        echo "  restart - Restart Spark cluster (default)"
        exit 1
        ;;
esac
