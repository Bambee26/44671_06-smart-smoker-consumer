import pika
import sys
import time
from collections import deque
from datetime import datetime

# Configure Logging
from util_logger import setup_logger

logger, logname = setup_logger(__file__)

# RabbitMQ setup
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
    """Declare queues."""
    for queue_name in queues:
        channel.queue_declare(queue=queue_name, durable=True)
        logger.info(f"Queue '{queue_name}' declared.")

# Initialize deques for each queue
smoker_deque = deque(maxlen=5)  # 2.5 minutes window
roast_deque = deque(maxlen=20)  # 10 minutes window
ribs_deque = deque(maxlen=20)  # 10 minutes window

def process_smoker_data(time, temp):
    smoker_deque.append((time, temp))
    if len(smoker_deque) == smoker_deque.maxlen:
        _, initial_temp = smoker_deque[0]  # Unpack only the necessary variable
        if initial_temp - temp >= 15:
            logger.warning(f"Smoker alert! Temperature dropped by 15°F or more in 2.5 minutes. Initial: {initial_temp}, Current: {temp}")
            # Implement additional alert actions here

def process_food_data(food_deque, time, temp, food_name):
    food_deque.append((time, temp))
    if len(food_deque) == food_deque.maxlen:
        _, initial_temp = food_deque[0]  # Unpack only the necessary variable
        if abs(initial_temp - temp) <= 1:
            logger.warning(f"Food stall alert! {food_name} temperature change is 1°F or less in 10 minutes. Initial: {initial_temp}, Current: {temp}")
            # Implement additional alert actions here


# Define callback function
def callback(ch, method, properties, body):
    """Callback function to process received messages."""
    data = body.decode().split(',')
    timestamp = datetime.strptime(data[0].split(': ')[1], '%m/%d/%Y %H:%M')  # Extract and parse timestamp
    temperature = float(data[1].split(': ')[1])  # Extract and parse temperature
    queue_name = method.routing_key  # Get the queue name from the routing key
    if queue_name == 'Smoker':
        process_smoker_data(timestamp, temperature)
    elif queue_name == 'Roast':
        process_food_data(roast_deque, timestamp, temperature, "Roast")
    elif queue_name == 'Ribs':
        process_food_data(ribs_deque, timestamp, temperature, "Ribs")
    else:
        logger.warning(f"Received message from unknown queue: {queue_name}")

# Define main function
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
