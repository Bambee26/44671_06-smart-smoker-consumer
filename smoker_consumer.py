"""
    This program listens for work messages continuously and sends a warning per configurations.
    
    Author: Bambee Garfield
    Date: June 7th, 2024

"""
# import tools
import pika
import sys
import time
from collections import deque
from datetime import datetime

# Configure Logging
from util_logger import setup_logger

logger, logname = setup_logger(__file__)

# Setup RabbitMQ
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

# Create and declare queues
def create_and_declare_queues(channel, queues):
    """Declare queues."""
    for queue_name in queues:
        channel.queue_declare(queue=queue_name, durable=True)
        logger.info(f"Queue '{queue_name}' declared.")

# Initialize deques for each queue
smoker_deque = deque(maxlen=5)  # 2.5 minutes window
roast_deque = deque(maxlen=20)  # 10 minutes window
ribs_deque = deque(maxlen=20)  # 10 minutes window

# Implement additional alert actions here
def process_smoker_data(smoker_deque, time, temp):
    smoker_deque.append((time, temp))
    if len(smoker_deque) == smoker_deque.maxlen:
        _, initial_temp = smoker_deque[0]
        if initial_temp - temp >= 15:
            logger.warning(f"Smoker alert! Temperature dropped by 15°F or more in 2.5 minutes. Initial: {initial_temp}, Current: {temp}")

def process_roast_data(roast_deque, time, temp):
    roast_deque.append((time, temp))
    if len(roast_deque) == roast_deque.maxlen:
        _, initial_temp = roast_deque[0]
        if abs(initial_temp - temp) <= 1:
            logger.warning(f"Roast alert! Temperature change is 1°F or less in 10 minutes. Initial: {initial_temp}, Current: {temp}")

def process_ribs_data(ribs_deque, time, temp):
    ribs_deque.append((time, temp))
    if len(ribs_deque) == ribs_deque.maxlen:
        _, initial_temp = ribs_deque[0] 
        if abs(initial_temp - temp) <= 1:
            logger.warning(f"Ribs alert! Temperature change is 1°F or less in 10 minutes. Initial: {initial_temp}, Current: {temp}")
            

def process_smoker_message(body):
    """Process message received from the 'Smoker' queue."""
    data = body.decode().split(',')
    timestamp = datetime.strptime(data[0].split(': ')[1], '%m/%d/%Y %H:%M')
    temperature = float(data[1].split(': ')[1])
    logger.info(f"Processing Smoker message: {data}")
    process_smoker_data(smoker_deque, timestamp, temperature)

def process_roast_message(body):
    """Process message received from the 'Roast' queue."""
    data = body.decode().split(',')
    timestamp = datetime.strptime(data[0].split(': ')[1], '%m/%d/%Y %H:%M')
    temperature = float(data[1].split(': ')[1])
    logger.info(f"Processing Roast message: {data}")
    process_roast_data(roast_deque, timestamp, temperature)

def process_ribs_message(body):
    """Process message received from the 'Ribs' queue."""
    data = body.decode().split(',')
    timestamp = datetime.strptime(data[0].split(': ')[1], '%m/%d/%Y %H:%M')
    temperature = float(data[1].split(': ')[1])
    logger.info(f"Processing Ribs message: {data}")
    process_ribs_data(ribs_deque, timestamp, temperature)

# Define a callback function to be called when a message is received
def callback(ch, method, properties, body):
    """Callback function to process received messages."""
    queue_name = method.routing_key
    logger.info(f"Received message from queue: {queue_name}")
    if queue_name == 'Smoker':
        process_smoker_message(body)
    elif queue_name == 'Roast':
        process_roast_message(body)
    elif queue_name == 'Ribs':
        process_ribs_message(body)
    else:
        logger.warning(f"Received message from unknown queue: {queue_name}")
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
# Define main function to run the program
def main(host: str = "localhost", queues: list = ["Smoker", "Roast", "Ribs"]):
    """Main function to consume messages from RabbitMQ."""
    try:
        # Establish a connection to the RabbitMQ server
        connection, channel = connect_rabbitmq(host)

        # Declare queues
        create_and_declare_queues(channel, queues)

        # Configure consumers for each queue
        for queue_name in queues:
            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

        # Start consuming messages
        logger.info(" [*] Ready for work. To exit press CTRL+C")
        channel.start_consuming()

    except Exception as e:
        logger.error("ERROR: Something went wrong.")
        logger.error(f"The error says: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.error(" User interrupted continuous listening process.")
        sys.exit(0)
    finally:
        logger.error("\nClosing connection. Goodbye.\n")
        connection.close()

# Standard Python idiom to indicate main program entry point
if __name__ == "__main__":
    # Call the main function with the provided arguments
    main()
