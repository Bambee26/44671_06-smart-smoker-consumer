"""
    This program sends a message to a queue on the RabbitMQ server.
    Make tasks harder/longer-running by adding dots at the end of the message.

    Author: Bambee Garfield
    Date: May 1st, 2024
"""

import pika
import sys
import csv
import time

# Configure Logging
from util_logger import setup_logger
logger, logname = setup_logger(__file__)

RABBITMQ_HOST = "localhost"

def connect_rabbitmq(host):
    """Connect to RabbitMQ and return connection and channel."""
    try:
        # create a blocking connection to the RabbitMQ server
        connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        # use the connection to create a communication channel
        channel = connection.channel()
        return connection, channel
    except Exception as e:
        logger.error(f"Error: Connection to RabbitMQ server failed: {e}")
        sys.exit(1)

def create_and_declare_queues(channel, queues):
    """Delete existing queues and declare new ones."""
    for queue_name in queues:
        channel.queue_delete(queue=queue_name)
        channel.queue_declare(queue=queue_name, durable=True)
        logger.info(f"Queue '{queue_name}' declared.")

# Read smoker temps from csv and send to RabbitMQ server
def read_and_send_smoker_temps_from_csv(file_path: str, host: str, queues: list):
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            timestamp = row['Time (UTC)']  # Updated to match the actual CSV header
            for queue_name in queues:
                temp_str = row.get(queue_name, '')
                if temp_str:
                    try:
                        temp = float(temp_str)
                        message = f"Time: {timestamp}, {queue_name}: {temp}"
                        send_message(host, queue_name, message)
                    except ValueError as e:
                        logger.error(f"Error converting temperature value to float: {e}")
                else:
                    logger.warning(f"Empty temperature value for {queue_name} at {timestamp}. Skipping.")
            time.sleep(5)  # Sleep for 10 seconds before sending the next message


def send_message(host: str, queue_name: str, message: str):
    """Send a message to the RabbitMQ queue."""
    connection, channel = connect_rabbitmq(host)
    try:
        channel.basic_publish(
            exchange='', 
            routing_key=queue_name, 
            body=message.encode(), 
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
        logger.info(f" [x] Sent '{message}' to queue '{queue_name}'.")
    except Exception as e:
        logger.error(f"Error sending message to queue '{queue_name}'.")
        logger.error(f"The error says: {e}")
    finally:
        connection.close()

# Standard Python idiom to indicate main program entry point
if __name__ == "__main__":  
    file_name = 'smoker-temps.csv'
    host = "localhost"
    queues = ["Smoker", "Roast", "Ribs"]
    connection, channel = connect_rabbitmq(host)
    create_and_declare_queues(channel, queues)
    connection.close()  # Close the initial connection after declaring queues
    read_and_send_smoker_temps_from_csv(file_name, host, queues)
