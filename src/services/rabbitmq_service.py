import asyncio
import json,random
from typing import Optional, Callable, Dict, Any
import aio_pika
from aio_pika.exceptions import AMQPConnectionError, AMQPChannelError
from aiormq.exceptions import ChannelInvalidStateError
from utils.logger import get_logger
from exceptions import DeviceError
from collections import Counter
logger = get_logger(__name__)

class RabbitMQService:
    def __init__(self, amqp_url: str, device_id: str,
                 exchange_name: str = 'device.exchange',
                 reconnect_interval: int = 5,
                 max_retries: int = -1, buzzer=None):
        self.amqp_url = amqp_url
        self.device_id = device_id
        self.exchange_name = exchange_name
        self.reconnect_interval = reconnect_interval
        self.max_retries = max_retries
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.queue: Optional[aio_pika.Queue] = None
        self._message_handlers: Dict[str, Callable] = {}
        self._connected = asyncio.Event()
        self._should_stop = False
        self.buzzer = buzzer
        self.consumer_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        retry_count = 0
        while not self._should_stop:
            try:
                if self.max_retries != -1 and retry_count >= self.max_retries:
                    raise DeviceError("Max reconnection attempts reached")

                await self._connect_and_setup()
                logger.info(f"RabbitMQ Connected.({self.device_id})")

                # Start consumer loop
                self.consumer_task = asyncio.create_task(self._consume_loop())
                self._connected.set()

                # Wait for either:
                # 1. Connection to break (cleared by consumer if lost)
                # 2. Manual stop() request
                while not self._should_stop and self._connected.is_set():
                    await asyncio.sleep(1)

                logger.warning("Connection lost or service stopping, triggering reconnect...")
                self._connected.clear()
                await self._safe_cleanup()

                retry_count += 1
                if not self._should_stop:
                    await asyncio.sleep(self.reconnect_interval)

            except (AMQPConnectionError, AMQPChannelError, ChannelInvalidStateError,OSError) as e:
                logger.error(f"RabbitMQ connection/channel error: {e}")
                self._connected.clear()
                await self._safe_cleanup()
                retry_count += 1
                if not self._should_stop:
                    reconnect_delay =self.get_exponential_backoff(retry_count)
                    await asyncio.sleep(reconnect_delay)

            except DeviceError as e:
                logger.critical(f"Device error: {e}")
                break

            except Exception as e:
                logger.error(f"Unexpected error in RabbitMQ service: {e}-{type(e)}")
                self._connected.clear()
                await self._safe_cleanup()
                retry_count += 1
                if not self._should_stop:
                   
                    reconnect_delay =self.get_exponential_backoff(retry_count)
                    await asyncio.sleep(reconnect_delay)
    def get_exponential_backoff(self,retry_count):
        base_delay = min(30, self.reconnect_interval * (2 ** min(retry_count, 10)))
        jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
        reconnect_delay = base_delay * jitter
        logger.info(f"Reconnect attempt {retry_count} scheduled in {reconnect_delay:.2f} seconds")
        return reconnect_delay
        
    # Add a timeout-aware wrapper for RabbitMQ operations
    async def safe_rabbitmq_operation(self, operation_name, coro, timeout=10.0):
        """Run a RabbitMQ operation with timeout protection"""
        try:
            # Run the operation with a timeout
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"RabbitMQ operation '{operation_name}' timed out after {timeout}s")
            # Attempt to reconnect if operation times out
            await self.rabbitmq_service.reconnect()
            raise
        except ChannelInvalidStateError as e:
            self.logger.error(f"RabbitMQ channel error in '{operation_name}': {e}")
            # Attempt to reconnect
            await self.rabbitmq_service.reconnect()
            raise
    async def reconnect(self):
        """Reconnect to RabbitMQ after connection issues"""
        try:
            # First close any existing connection
            await self.stop()
        except:
            pass
            
        # Then create a new connection
        try:
            # Connection logic here
            self.logger.info("Reconnected to RabbitMQ")
        except Exception as e:
            self.logger.error(f"Failed to reconnect to RabbitMQ: {e}")

    async def stop(self):
        """Properly close RabbitMQ connection with timeout protection"""
        if not hasattr(self, 'connection') or self.connection is None:
            return
            
        try:
            # Close with timeout protection
            close_task = asyncio.create_task(self.connection.close())
            await asyncio.wait_for(close_task, timeout=2.0)
        except asyncio.TimeoutError:
            self.logger.warning("RabbitMQ connection close timed out")
        except Exception as e:
            self.logger.error(f"Error closing RabbitMQ connection: {e}")
        finally:
            # Ensure connection is marked as closed
            self.connection = None

    async def _safe_cleanup(self) -> None:
        try:
            if self.consumer_task and not self.consumer_task.done():
                self.consumer_task.cancel()
                try:
                    await self.consumer_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
        except Exception:
            pass

    async def _connect_and_setup(self) -> None:
            logger.info("🔌 Connecting to RabbitMQ...")
            try:
                self.connection = await aio_pika.connect_robust(self.amqp_url)
                self.channel = await self.connection.channel()

                logger.info("📡 Setting up exchange and queue...")
                self.exchange = await self.channel.declare_exchange(
                    self.exchange_name,
                    type=aio_pika.ExchangeType.DIRECT,
                    durable=True
                )

                self.queue = await self.channel.declare_queue(
                    self.device_id,
                    durable=True,
                    auto_delete=False,
                    arguments={
                        'x-dead-letter-exchange': 'dlx.exchange',
                        'x-dead-letter-routing-key': f"dlx.{self.device_id}"
                    }
                )
                dlx = await self.channel.declare_exchange(
                    'dlx.exchange',
                    type=aio_pika.ExchangeType.DIRECT,
                    durable=True
                )

                dlq = await self.channel.declare_queue(
                    f"dlx.{self.device_id}",
                    durable=True
                )
                await self.queue.bind(self.exchange, routing_key=self.device_id)
                await dlq.bind(dlx, routing_key=f"dlx.{self.device_id}")

                logger.info("✅ RabbitMQ setup complete")

                if self.buzzer:
                    self.buzzer.single_click()
            except AMQPConnectionError as a:
                logger.error(f"❌ RabbitMQ Connection Error: {a}")
                raise a
            except OSError as o:
                logger.error(f"❌ Network Error: {o}")
                raise o
            except Exception as e:
                logger.error(f"❌ Failed to Connect: {e}")
                raise e
               

    async def _consume_loop(self) -> None:
        try:
            if not self.queue:
                return
            async with self.queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if self._should_stop or self.connection.is_closed:
                        logger.warning("Connection lost or service stopping, exiting consumer loop.")
                        self._connected.clear()
                        break

                    try:
                        await self._process_message(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        # Handle error - ack or reject based on your policy
                        if not message.processed:
                            await message.reject(requeue=False) 

        except asyncio.CancelledError:
            logger.info("✅ Consumer task cancelled cleanly")
        except Exception as e:
            logger.error(f"Consumer loop crashed unexpectedly: {e}")
            self._connected.clear()
    def addMessageHandler(self,key,callable:Callable):
         self.message_handlers[key] = callable
         return self
    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        try:
            if message.body_size == 0:
                logger.info(f"Received empty message, acknowledging without processing")
                if not message.processed:
                    await message.ack()
                return
            
            body = message.body.decode()
            data = json.loads(body)
            message_type = data.get('type', 'DEFAULT')
            print(message_type)
            notify = data.get('notify', False)
            if not notify and "summary" in data:
                summary = data.get('summary', {})
                notify = summary.get('notify', False)
                
            

            if notify and self.buzzer:
                self.buzzer.double_click()

            handler = self._message_handlers.get(message_type)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    # It's async, await it
                    await handler(data)
                else:
                    # It's a regular function, just call it
                    handler(data)
            elif "DEFAULT" in self._message_handlers:
                handler = self._message_handlers["DEFAULT"]
                if asyncio.iscoroutinefunction(handler):
                    # It's async, await it
                    await handler(data)
                else:
                    # It's a regular function, just call it
                    handler(data)
            else:
                logger.warning(f"No handler registered for message type: {message_type}")
            if not message.processed:
                await message.ack()

        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {message.body}")
            if not message.processed:
               await message.reject(requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if not message.processed:
                await message.reject(requeue=False)
    def add_counter(self,c:Counter):
        self.counter=c
    def register_handler(self, message_type: str, handler: Callable) -> None:
        self._message_handlers[message_type] = handler

    async def publish_message(self, routing_key: str, message: dict) -> None:
        if not self._connected.is_set():
            raise DeviceError("Not connected to RabbitMQ")

        try:
            message_body = json.dumps(message).encode()
            message=aio_pika.Message(
                    body=message_body,
                    content_type='application/json',
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                )
            return await self.safe_rabbitmq_operation(
                "exchange_publish",
                self.exchange.publish(
                    message=message,
                    routing_key=routing_key
                ),
                timeout=5.0  # 5 second timeout
            )
            
        except (ChannelInvalidStateError, AMQPChannelError):
            logger.warning("⚠️ Channel lost while publishing, triggering reconnect.")
            self._connected.clear()
            raise DeviceError("Channel lost during publish")
        except Exception as e:
            logger.error("Failed to publish message")
            raise DeviceError("Failed to publish message") from e
