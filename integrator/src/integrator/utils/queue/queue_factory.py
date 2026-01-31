"""
NATS JetStream Queue Manager

A comprehensive queue management system using NATS JetStream with the following features:
1. Publish/enqueue messages
2. Subscribe/dequeue messages in real time with callbacks
3. Message status tracking (pending, in-process, failure, success)
4. Retry failed messages
5. Purge messages

Designed for integration with FastAPI and other Python applications.
Based on nats_poc.py implementation with enhanced functionality.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import weakref

import nats
from nats.js import JetStreamContext
from nats.js.api import (
    StreamConfig, ConsumerConfig, DeliverPolicy, AckPolicy, 
    RetentionPolicy, StorageType
)
from nats.js.errors import NotFoundError
from nats.errors import TimeoutError as NatsTimeout

# Import configuration
from integrator.utils.queue.config import nats_queue_config, ConsumerMode
from integrator.utils.logger import get_logger

# Configure logging
logger = get_logger(__file__)


class MessageStatus(Enum):
    """Message status enumeration"""
    PENDING = "pending"
    IN_PROCESS = "in_process"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


@dataclass
class QueueMessage:
    """Queue message data structure"""
    id: str
    subject: str
    data: Dict[str, Any]
    status: MessageStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        result['status'] = self.status.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueMessage':
        """Create message from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['status'] = MessageStatus(data['status'])
        return cls(**data)


class NATSQueueManager:
    """
    NATS JetStream Queue Manager designed for integration with FastAPI and other applications
    
    Features:
    1. Publish/enqueue messages
    2. Subscribe/dequeue messages with real-time callbacks
    3. Message status tracking (pending, in-process, failure, success)
    4. Retry failed messages
    5. Purge messages
    
    Integration-friendly design:
    - Singleton pattern for shared instances
    - Async-first design compatible with FastAPI
    - Graceful connection handling
    - Background task management
    """
    
    _instances: Dict[str, 'NATSQueueManager'] = {}
    _lock = threading.Lock()
    
    def __new__(cls, nats_url: Optional[str] = None, stream_name: Optional[str] = None, **kwargs):
        """Singleton pattern to ensure one instance per stream."""
        # Use config defaults if not provided
        actual_nats_url = nats_url or nats_queue_config.url
        actual_stream_name = stream_name or nats_queue_config.default_stream_name
        
        instance_key = f"{actual_nats_url}:{actual_stream_name}"
        
        with cls._lock:
            if instance_key not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[instance_key] = instance
                instance._initialized = False
            return cls._instances[instance_key]
    
    def __init__(self, 
                 nats_url: Optional[str] = None,
                 stream_name: Optional[str] = None,
                 max_retries: Optional[int] = None,
                 ack_wait: Optional[float] = None,
                 max_deliver: Optional[int] = None,
                 max_concurrent_callbacks: Optional[int] = None,
                 max_ack_pending: Optional[int] = None,
                 consumer_mode: Optional[ConsumerMode] = nats_queue_config.consumer_mode):
        """
        Initialize NATS Queue Manager
        
        Args:
            nats_url: NATS server URL (uses config default if not provided)
            stream_name: JetStream stream name (uses config default if not provided)
            max_retries: Maximum retry attempts for failed messages (uses config default if not provided)
            ack_wait: Acknowledgment wait time in seconds (uses config default if not provided)
            max_deliver: Maximum delivery attempts before moving to DLQ (uses config default if not provided)
            max_concurrent_callbacks: Maximum number of concurrent callback executions (default: 1)
        """
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.consumer_mode=consumer_mode
        self.max_ack_pending=max_ack_pending    
        # Use configuration values with fallbacks
        self.nats_url = nats_url or nats_queue_config.url
        self.stream_name = stream_name or nats_queue_config.default_stream_name
        self.max_retries = max_retries if max_retries is not None else nats_queue_config.max_retries
        self.ack_wait = ack_wait if ack_wait is not None else nats_queue_config.ack_wait
        self.max_deliver = max_deliver if max_deliver is not None else nats_queue_config.max_deliver
        self.max_concurrent_callbacks = max_concurrent_callbacks if max_concurrent_callbacks is not None else 1



        
        # Stream and subject configuration using config methods
        self.work_subject = nats_queue_config.get_work_subject(self.stream_name)
        self.dlq_stream = nats_queue_config.get_dlq_stream_name(self.stream_name)
        self.dlq_subject = nats_queue_config.get_dlq_subject(self.stream_name)
        self.adv_stream = nats_queue_config.get_adv_stream_name(self.stream_name)
        
        # Consumer names using config methods
        self.work_consumer = nats_queue_config.get_worker_consumer_name(self.stream_name)
        self.dlq_consumer = nats_queue_config.get_dlq_consumer_name(self.stream_name)
        self.adv_consumer = nats_queue_config.get_adv_consumer_name(self.stream_name)
        
        # Connection objects
        self._nc: Optional[nats.NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._connection_lock = asyncio.Lock()
        self._is_connecting = False
        
        # Message tracking
        self.message_store: Dict[str, QueueMessage] = {}
        self.subscribers: Dict[str, Any] = {}
        self.background_tasks: set = set()
        
        # Mark as initialized
        self._initialized = True
        
        logger.info(f"NATS Queue Manager created for stream: {stream_name}")
    
    async def ensure_connection(self) -> bool:
        """
        Ensure NATS connection is established (async, integration-friendly)
        
        Returns:
            bool: True if connected, False otherwise
        """
        if self.is_connected():
            return True
        
        async with self._connection_lock:
            # Double-check after acquiring lock
            if self.is_connected():
                return True
            
            if self._is_connecting:
                # Wait for ongoing connection attempt
                while self._is_connecting:
                    await asyncio.sleep(0.1)
                return self.is_connected()
            
            self._is_connecting = True
            try:
                await self._connect()
                return self.is_connected()
            except Exception as e:
                logger.error(f"Failed to establish NATS connection: {e}")
                return False
            finally:
                self._is_connecting = False
    
    async def _connect(self):
        """Internal connection method."""
        try:
            logger.info(f"Connecting to NATS at {self.nats_url}")
            
            # Connect to NATS with timeout from config
            self._nc = await asyncio.wait_for(
                nats.connect(self.nats_url), 
                timeout=nats_queue_config.connection_timeout
            )
            logger.info("NATS connection established")
            
            # Initialize JetStream
            self._js = self._nc.jetstream()
            logger.info("JetStream context created")
            
            # Create streams and consumers
            await self._ensure_infrastructure()
            
            logger.info(f"NATS queue manager connected successfully: {self.nats_url}")
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout connecting to NATS server at {self.nats_url}. Is NATS server running?"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to connect to NATS: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def _ensure_infrastructure(self):
        """Ensure all required JetStream infrastructure exists."""
        try:
            # 1. Work stream (work queue semantics)
            await self._ensure_stream(
                self.stream_name,
                [self.work_subject],
                RetentionPolicy.WORK_QUEUE
            )
            
            # 2. DLQ stream (for failed messages)
            await self._ensure_stream(
                self.dlq_stream,
                [self.dlq_subject],
                RetentionPolicy.LIMITS
            )
            
            # 3. Advisory stream (for delivery tracking)
            adv_subjects = [
                f"$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.{self.stream_name}.{self.work_consumer}",
                f"$JS.EVENT.ADVISORY.CONSUMER.MSG_TERMINATED.{self.stream_name}.{self.work_consumer}"
            ]
            await self._ensure_stream(
                self.adv_stream,
                adv_subjects,
                RetentionPolicy.LIMITS
            )
            
            # 4. ACK Metrics stream (for tracking successful ACKs)
            ack_metric_subject = f"$JS.EVENT.METRIC.CONSUMER.ACK.{self.stream_name}.{self.work_consumer}"
            await self._ensure_stream(
                f"{self.stream_name}_METRICS",
                [ack_metric_subject],
                RetentionPolicy.LIMITS
            )
            
            # 5. Work consumer (PUSH consumer for real-time processing with ACK sampling)

            if self.consumer_mode == ConsumerMode.PULL:
                await self._ensure_consumer(
                    self.stream_name,
                    self.work_consumer,
                    ConsumerConfig(
                        durable_name=self.work_consumer,
                        deliver_policy=DeliverPolicy.ALL,
                        max_deliver=self.max_deliver,
                        ack_wait=self.ack_wait,
                        filter_subject=self.work_subject,
                        ack_policy=AckPolicy.EXPLICIT,
                    )
                )

            else:    
                # For PUSH mode, don't pre-create the consumer here
                # Let the subscribe method create it with the proper deliver_subject
                pass

            # 6. DLQ consumer (PULL consumer for manual processing)
            await self._ensure_consumer(
                self.dlq_stream,
                self.dlq_consumer,
                ConsumerConfig(
                    durable_name=self.dlq_consumer,
                    ack_policy=AckPolicy.EXPLICIT,
                    deliver_policy=DeliverPolicy.ALL,
                )
            )
            
            # 7. Advisory consumer (PULL consumer for status tracking)
            await self._ensure_consumer(
                self.adv_stream,
                self.adv_consumer,
                ConsumerConfig(
                    durable_name=self.adv_consumer,
                    ack_policy=AckPolicy.EXPLICIT,
                    deliver_policy=DeliverPolicy.ALL,
                )
            )
            
            # 8. ACK Metrics consumer (PULL consumer for counting successful ACKs)
            ack_metric_subject = f"$JS.EVENT.METRIC.CONSUMER.ACK.{self.stream_name}.{self.work_consumer}"
            await self._ensure_consumer(
                f"{self.stream_name}_METRICS",
                f"{self.work_consumer}_ack_stats",
                ConsumerConfig(
                    durable_name=f"{self.work_consumer}_ack_stats",
                    filter_subject=ack_metric_subject,
                    ack_policy=AckPolicy.EXPLICIT,
                    deliver_policy=DeliverPolicy.ALL,
                )
            )
            
            logger.info("All NATS infrastructure created successfully")
            
        except Exception as e:
            logger.error(f"Failed to ensure infrastructure: {e}")
            raise
    
    async def _ensure_stream(self, name: str, subjects: List[str], retention: RetentionPolicy):
        """Ensure a stream exists with the given configuration."""
        try:
            await self._js.stream_info(name)
            logger.debug(f"Stream {name} already exists")
        except:
            config = StreamConfig(
                name=name,
                subjects=subjects,
                retention=retention,
                storage=StorageType.FILE,
                max_msgs=100000,
                max_age=timedelta(days=7).total_seconds()
            )
            await self._js.add_stream(config)
            logger.info(f"Created stream {name}")
    
    async def _ensure_consumer(self, stream: str, consumer: str, config: ConsumerConfig):
        """Ensure a consumer exists with the given configuration."""
        try:
            await self._js.consumer_info(stream, consumer)
            logger.debug(f"Consumer {consumer} already exists")
        except:
            await self._js.add_consumer(stream, config)
            logger.info(f"Created consumer {consumer}")
    
    # ==================== FEATURE 1: PUBLISH/ENQUEUE MESSAGES ====================
    
    async def publish(self,  data: Dict[str, Any], subject: str=nats_queue_config.default_subject, message_id: Optional[str] = None) -> str:
        """
        Publish/enqueue a message to the queue (async, integration-friendly)
        
        Args:
            subject: Message subject/topic
            data: Message data
            message_id: Optional message ID (auto-generated if not provided)
            
        Returns:
            str: Message ID
        """
        # Ensure connection before publishing
        if not await self.ensure_connection():
            raise RuntimeError("Failed to establish NATS connection")
        
        if not message_id:
            message_id = str(uuid.uuid4())
        
        # Create queue message
        now = datetime.now()
        queue_message = QueueMessage(
            id=message_id,
            subject=subject,
            data=data,
            status=MessageStatus.PENDING,
            created_at=now,
            updated_at=now,
            max_retries=self.max_retries
        )
        
        # Store message locally for status tracking
        self.message_store[message_id] = queue_message
        
        try:
            # Publish to JetStream work stream
            message_payload = json.dumps(queue_message.to_dict())
            
            ack = await self._js.publish(
                self.work_subject,
                message_payload.encode(),
                headers={"Nats-Msg-Id": message_id}
            )
            
            logger.info(f"Published message {message_id} to {self.work_subject}")
            return message_id
            
        except Exception as e:
            # Update message status to failure
            queue_message.status = MessageStatus.FAILURE
            queue_message.error_message = str(e)
            queue_message.updated_at = datetime.now()
            
            logger.error(f"Failed to publish message {message_id}: {e}")
            raise
    
    def publish_sync(self, subject: str, data: Dict[str, Any], message_id: Optional[str] = None) -> str:
        """
        Synchronous wrapper for publish (for non-async applications)
        
        Args:
            subject: Message subject/topic
            data: Message data
            message_id: Optional message ID (auto-generated if not provided)
            
        Returns:
            str: Message ID
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.publish(subject, data, message_id))
    
    # ==================== FEATURE 2: SUBSCRIBE/DEQUEUE WITH CALLBACKS ====================
    
    async def subscribe(self, callback: Callable, *args, **kwargs) -> str:
        """
        Subscribe to messages and process them with callback in real time (async, integration-friendly)
        
        Args:
            callback: Callback function that processes messages and returns True for success, False for retry
                     Can be either sync or async function. First parameter should be QueueMessage,
                     followed by any additional arguments passed via *args and **kwargs
            *args: Additional positional arguments to pass to the callback function
            **kwargs: Additional keyword arguments to pass to the callback function
            
        Returns:
            str: Subscription ID
        """
        # Ensure connection before subscribing
        if not await self.ensure_connection():
            raise RuntimeError("Failed to establish NATS connection")
        
        subscription_id = str(uuid.uuid4())
        
        async def message_handler(msg):
            try:
                # Parse message
                data = json.loads(msg.data.decode())
                queue_message = QueueMessage.from_dict(data)
                
                # Update status to in-process
                queue_message.status = MessageStatus.IN_PROCESS
                queue_message.updated_at = datetime.now()
                self.message_store[queue_message.id] = queue_message
                
                md = msg.metadata
                
                logger.info(f"Processing message {queue_message.id}, delivery #{md.num_delivered}")
                
                try:
                    # Call user callback - handle both sync and async callbacks
                    if asyncio.iscoroutinefunction(callback):
                        success = await callback(queue_message, *args, **kwargs)
                    else:
                        success = callback(queue_message, *args, **kwargs)
                    
                    if success:
                        # Mark as successful and acknowledge
                        queue_message.status = MessageStatus.SUCCESS
                        queue_message.updated_at = datetime.now()
                        self.message_store[queue_message.id] = queue_message
                        
                        await msg.ack()
                        logger.info(f"Message {queue_message.id} processed successfully")
                    else:
                        # Mark as failure and handle retry logic
                        await self._handle_message_failure(msg, queue_message, "Callback returned False")
                        
                except Exception as e:
                    # Handle callback exception
                    await self._handle_message_failure(msg, queue_message, str(e))
                    
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                try:
                    await msg.nak()
                except:
                    pass
        
        # Subscribe to the work stream using PUSH consumer
        if self.consumer_mode == ConsumerMode.PUSH:
            # For PUSH mode, create a consumer config with deliver_subject
            inbox = self._nc.new_inbox()
            config = ConsumerConfig(
                durable_name=self.work_consumer,
                deliver_subject=inbox,
                ack_policy=AckPolicy.EXPLICIT,
                deliver_policy=DeliverPolicy.ALL,
                ack_wait=self.ack_wait,
                max_deliver=self.max_deliver,
                max_ack_pending=self.max_ack_pending,
                sample_freq="100%",
                filter_subject=self.work_subject,
            )
            subscription = await self._js.subscribe(
                self.work_subject,
                stream=self.stream_name,
                durable=self.work_consumer,
                cb=message_handler,
                manual_ack=True,
                config=config,
            )
        else:
            # For PULL mode, no deliver_subject needed
            subscription = await self._js.subscribe(
                self.work_subject,
                stream=self.stream_name,
                durable=self.work_consumer,
                cb=message_handler,
                manual_ack=True,
            )
        
        self.subscribers[subscription_id] = subscription
        logger.info(f"Subscribed to {self.work_subject} with ID {subscription_id}")
        
        return subscription_id
    
    async def start_background_subscriber(self, callback: Callable, *args, **kwargs) -> str:
        """
        Start a background subscriber task (ideal for FastAPI integration)
        
        Args:
            callback: Callback function that processes messages. First parameter should be QueueMessage,
                     followed by any additional arguments passed via *args and **kwargs
            *args: Additional positional arguments to pass to the callback function
            **kwargs: Additional keyword arguments to pass to the callback function
            
        Returns:
            str: Subscription ID
        """
        subscription_id = await self.subscribe(callback, *args, **kwargs)
        
        # Create a background task to keep the subscription alive
        task = asyncio.create_task(self._keep_subscription_alive(subscription_id))
        
        # Keep a reference to prevent garbage collection
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        return subscription_id
    
    async def _keep_subscription_alive(self, subscription_id: str):
        """Keep subscription alive in background."""
        try:
            while subscription_id in self.subscribers:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info(f"Background subscription {subscription_id} cancelled")
        except Exception as e:
            logger.error(f"Error in background subscription {subscription_id}: {e}")
    
    async def _handle_message_failure(self, msg, queue_message: QueueMessage, error: str):
        """Handle message processing failure with retry logic."""
        md = msg.metadata
        
        # Update message status
        queue_message.status = MessageStatus.FAILURE
        queue_message.error_message = error
        queue_message.retry_count = md.num_delivered - 1
        queue_message.updated_at = datetime.now()
        self.message_store[queue_message.id] = queue_message
        
        # Check if we've exceeded max deliveries
        if md.num_delivered >= self.max_deliver:
            # Move to DLQ and terminate
            await self._js.publish(
                self.dlq_subject,
                msg.data,
                headers={
                    "X-Orig-Stream": md.stream,
                    "X-Stream-Seq": str(md.sequence.stream),
                    "X-Error": error[:200],
                    "X-Delivery-Count": str(md.num_delivered)
                }
            )
            await msg.term()
            logger.warning(f"Message {queue_message.id} moved to DLQ after {md.num_delivered} deliveries")
        else:
            # Retry with backoff
            delay = min(1.0 * md.num_delivered, 60.0)  # Max 60 second delay
            await msg.nak(delay=delay)
            logger.info(f"Message {queue_message.id} will retry in {delay}s (attempt {md.num_delivered})")
    
    async def unsubscribe(self, subscription_id: str):
        """Unsubscribe from messages."""
        if subscription_id in self.subscribers:
            subscription = self.subscribers[subscription_id]
            await subscription.unsubscribe()
            del self.subscribers[subscription_id]
            logger.info(f"Unsubscribed from subscription {subscription_id}")
    
    # ==================== FEATURE 3: MESSAGE STATUS TRACKING ====================
    
    def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        """Get the status of a specific message."""
        message = self.message_store.get(message_id)
        return message.status if message else None
    
    async def get_message_counts(self) -> Dict[str, int]:
        """
        Get comprehensive message counts across all states
        
        Returns:
            Dict with counts for pending_or_in_process, failure, success
        """
        if not await self.ensure_connection():
            return {
                "pending_or_in_process": 0,
                "failure": 0,
                "success": 0,
                "dlq_count": 0,
                "advisory_max_deliveries": 0,
                "advisory_terminated": 0
            }
        
        try:
            wk_info = await self._js.stream_info(self.stream_name)
            # Get work consumer info
            cinfo = await self._js.consumer_info(self.stream_name, self.work_consumer)
            pending_or_inproc = cinfo.num_pending + cinfo.num_ack_pending
            
            # Get failure counts from DLQ and advisories
            dlq_info = await self._js.stream_info(self.dlq_stream)
            dlq_count = dlq_info.state.messages
            
            # Count advisory messages (max deliveries and terminated)
            adv_maxdel = await self._count_subject_pending(
                self.adv_stream,
                f"$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.{self.stream_name}.{self.work_consumer}"
            )
            adv_term = await self._count_subject_pending(
                self.adv_stream,
                f"$JS.EVENT.ADVISORY.CONSUMER.MSG_TERMINATED.{self.stream_name}.{self.work_consumer}"
            )
            
            failures = dlq_count + adv_maxdel + adv_term
            
            # Count success based on ACK metric events (reliable ACK counting)
            success = await self._count_ack_successes()
            
            return {
                "pending_or_in_process": pending_or_inproc,
                "failure": failures,
                "success": success,
                "dlq_count": dlq_count,
                "advisory_max_deliveries": adv_maxdel,
                "advisory_terminated": adv_term
            }
            
        except Exception as e:
            logger.error(f"Failed to get message counts: {e}")
            return {
                "pending_or_in_process": 0,
                "failure": 0,
                "success": 0,
                "dlq_count": 0,
                "advisory_max_deliveries": 0,
                "advisory_terminated": 0
            }
    
    async def _count_ack_successes(self) -> int:
        """
        Count successful message deliveries by reading ACK metric events.
        This provides a reliable count of messages that were actually acknowledged.
        
        Returns:
            int: Number of successfully acknowledged messages
        """
        try:
            metrics_stream = f"{self.stream_name}_METRICS"
            ack_stats_consumer = f"{self.work_consumer}_ack_stats"
            
            # Get consumer info to read the number of ACK events retained
            ci = await self._js.consumer_info(metrics_stream, ack_stats_consumer)
            
            # num_pending represents the total ACK events retained = successful deliveries
            return ci.num_pending
            
        except Exception as e:
            logger.error(f"Failed to count ACK successes: {e}")
            return 0



    async def pull_messages(self, batch_size: int, timeout: float, callback: Callable, *args, **kwargs)->bool:
        """
        Pull messages from the JetStream stream using pull-based consumer
        
        This method allows manual message fetching, giving you full control over
        when and how messages are processed, unlike the callback-based subscribe method.
        
        Args:
            consumer_name: Name of the pull consumer (create with create_pull_consumer first)
            batch_size: Number of messages to fetch in one batch
            timeout: Timeout for pull operation in seconds
            auto_ack: Whether to automatically acknowledge messages (default: False for manual control)
            
        Returns:
            List[Dict]: List of message dictionaries with keys:
                - 'message': QueueMessage object
                - 'raw_msg': Raw NATS message object (for manual ack/nak)
                - 'metadata': Message metadata (delivery count, etc.)
        """
        if not await self.ensure_connection():
            raise RuntimeError("Failed to establish NATS connection")
            
        try:
            # Create pull subscription
            pull_sub = await self._js.pull_subscribe(
                subject=self.work_subject,
                durable=self.work_consumer,
                stream=self.stream_name
            )
            
            messages = []
            
            try:
                # Pull messages with timeout
                msgs = await pull_sub.fetch(batch_size, timeout=timeout)
                
                for msg in msgs:
                    try:
                        # Parse message data
                        data = json.loads(msg.data.decode('utf-8'))
                        queue_message = QueueMessage.from_dict(data)


                
                        # Update status to in-process
                        queue_message.status = MessageStatus.IN_PROCESS
                        queue_message.updated_at = datetime.now()
                        self.message_store[queue_message.id] = queue_message
                
                        md = msg.metadata
                
                        logger.info(f"Processing message {queue_message.id}, delivery #{md.num_delivered}")
                        # Call user callback - handle both sync and async callbacks
                        if asyncio.iscoroutinefunction(callback):
                            success = await callback(queue_message, *args, **kwargs)
                        else:
                            success = callback(queue_message, *args, **kwargs)
                
                        if success:
                            # Mark as successful and acknowledge
                            queue_message.status = MessageStatus.SUCCESS
                            queue_message.updated_at = datetime.now()
                            self.message_store[queue_message.id] = queue_message
                            
                            await msg.ack()
                            logger.info(f"Message {queue_message.id} processed successfully")
                            await self.get_message_counts()
                        else:
                            # Mark as failure and handle retry logic
                            await self._handle_message_failure(msg, queue_message, "Callback returned False")
                        
                    except Exception as e:
                        # Handle callback exception
                        await self._handle_message_failure(msg, queue_message, str(e))
                        
                    logger.debug(f"Pulled message {queue_message.id}, delivery #{md.num_delivered}")
                        
                
            except NatsTimeout:
                logger.debug(f"Pull timeout after {timeout}s, no messages available")
            
            #finally:
                # Clean up subscription
            #    await pull_sub.unsubscribe()
            
            logger.info(f"Pulled {len(messages)} messages from consumer '{self.work_consumer}'")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to pull messages: {e}")
            raise

    async def ack_message(self, raw_msg, message_id: str = None):
        """
        Manually acknowledge a message pulled via pull_messages
        
        Args:
            raw_msg: Raw NATS message object from pull_messages result
            message_id: Optional message ID for status tracking
        """
        try:
            await raw_msg.ack()
            
            if message_id and message_id in self.message_store:
                queue_message = self.message_store[message_id]
                queue_message.status = MessageStatus.SUCCESS
                queue_message.updated_at = datetime.now()
                self.message_store[message_id] = queue_message
                
            logger.debug(f"Acknowledged message {message_id or 'unknown'}")
            
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id or 'unknown'}: {e}")
            raise

    async def nak_message(self, raw_msg, message_id: str = None, delay: float = None):
        """
        Manually negative acknowledge (retry) a message pulled via pull_messages
        
        Args:
            raw_msg: Raw NATS message object from pull_messages result
            message_id: Optional message ID for status tracking
            delay: Optional delay before retry (seconds)
        """
        try:
            if delay is not None:
                await raw_msg.nak(delay=delay)
            else:
                await raw_msg.nak()
            
            if message_id and message_id in self.message_store:
                queue_message = self.message_store[message_id]
                queue_message.status = MessageStatus.RETRY
                queue_message.updated_at = datetime.now()
                self.message_store[message_id] = queue_message
                
            logger.debug(f"NAK'd message {message_id or 'unknown'} with delay {delay or 'default'}")
            
        except Exception as e:
            logger.error(f"Failed to NAK message {message_id or 'unknown'}: {e}")
            raise

    async def term_message(self, raw_msg, message_id: str = None):
        """
        Terminate a message (stop redelivery) pulled via pull_messages
        
        Args:
            raw_msg: Raw NATS message object from pull_messages result
            message_id: Optional message ID for status tracking
        """
        try:
            await raw_msg.term()
            
            if message_id and message_id in self.message_store:
                queue_message = self.message_store[message_id]
                queue_message.status = MessageStatus.FAILURE
                queue_message.updated_at = datetime.now()
                self.message_store[message_id] = queue_message
                
            logger.debug(f"Terminated message {message_id or 'unknown'}")
            
        except Exception as e:
            logger.error(f"Failed to terminate message {message_id or 'unknown'}: {e}")
            raise

    async def _count_subject_pending(self, stream: str, subject: str) -> int:
        """Count pending messages for a specific subject."""
        try:
            consumer_name = f"stat_{abs(hash((stream, subject))) % 10000000}"
            
            # Create temporary consumer for counting
            try:
                await self._js.add_consumer(
                    stream,
                    ConsumerConfig(
                        durable_name=consumer_name,
                        filter_subject=subject,
                        ack_policy=AckPolicy.EXPLICIT,
                        deliver_policy=DeliverPolicy.ALL,
                    )
                )
            except:
                pass  # Consumer might already exist
            
            # Get consumer info to read pending count
            ci = await self._js.consumer_info(stream, consumer_name)
            return ci.num_pending
            
        except Exception as e:
            logger.error(f"Failed to count pending messages for {subject}: {e}")
            return 0
    
    # ==================== FEATURE 4: RETRY FAILED MESSAGES ====================
    
    async def retry_failed_messages(self, batch_size: int = 64, timeout: float = 1.0, delete_original: bool = True) -> int:
        """
        Retry all failed messages from DLQ and advisories
        
        Args:
            batch_size: Number of messages to process in each batch
            timeout: Timeout for fetching messages
            delete_original: Whether to delete original failed messages after retry
            
        Returns:
            int: Number of messages retried
        """
        if not await self.ensure_connection():
            logger.error("Cannot retry messages: NATS connection not available")
            return 0
        
        total_retried = 0
        
        try:
            # 1. Retry messages from DLQ
            dlq_retried = await self._retry_dlq_messages(batch_size, timeout)
            total_retried += dlq_retried
            
            # 2. Retry messages from advisories
            adv_retried = await self._retry_advisory_messages(batch_size, timeout, delete_original)
            total_retried += adv_retried
            
            logger.info(f"Total messages retried: {total_retried} (DLQ: {dlq_retried}, Advisory: {adv_retried})")
            
        except Exception as e:
            logger.error(f"Failed to retry messages: {e}")
        
        return total_retried
    
    async def _retry_dlq_messages(self, batch_size: int, timeout: float) -> int:
        """Retry messages from DLQ."""
        retried = 0
        
        try:
            # Create pull subscription for DLQ
            dlq_sub = await self._js.pull_subscribe(
                self.dlq_subject,
                durable=self.dlq_consumer,
                stream=self.dlq_stream
            )
            
            while True:
                try:
                    msgs = await dlq_sub.fetch(batch=batch_size, timeout=timeout)
                    if not msgs:
                        break
                    
                    for msg in msgs:
                        try:
                            # Republish to work queue
                            await self._js.publish(self.work_subject, msg.data)
                            await msg.ack()
                            retried += 1
                            logger.debug(f"Retried DLQ message")
                        except Exception as e:
                            logger.error(f"Failed to retry DLQ message: {e}")
                            
                except NatsTimeout:
                    break
                    
            await dlq_sub.unsubscribe()
            
        except Exception as e:
            logger.error(f"Failed to retry DLQ messages: {e}")
        
        return retried
    
    async def _retry_advisory_messages(self, batch_size: int, timeout: float, delete_original: bool) -> int:
        """Retry messages from advisory events."""
        retried = 0
        
        # Retry max delivery advisories
        retried += await self._retry_advisory_subject(
            f"$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.{self.stream_name}.{self.work_consumer}",
            batch_size, timeout, delete_original
        )
        
        # Retry terminated advisories
        retried += await self._retry_advisory_subject(
            f"$JS.EVENT.ADVISORY.CONSUMER.MSG_TERMINATED.{self.stream_name}.{self.work_consumer}",
            batch_size, timeout, delete_original
        )
        
        return retried
    
    async def _retry_advisory_subject(self, subject: str, batch_size: int, timeout: float, delete_original: bool) -> int:
        """Retry messages from a specific advisory subject."""
        retried = 0
        consumer_name = f"retry_{abs(hash(subject)) % 10000000}"
        
        try:
            # Create consumer for this advisory subject
            try:
                await self._js.add_consumer(
                    self.adv_stream,
                    ConsumerConfig(
                        durable_name=consumer_name,
                        filter_subject=subject,
                        ack_policy=AckPolicy.EXPLICIT,
                        deliver_policy=DeliverPolicy.ALL,
                    )
                )
            except:
                pass
            
            # Create pull subscription
            sub = await self._js.pull_subscribe(subject, durable=consumer_name, stream=self.adv_stream)
            
            while True:
                try:
                    advs = await sub.fetch(batch=batch_size, timeout=timeout)
                    if not advs:
                        break
                    
                    for adv in advs:
                        try:
                            # Parse advisory event
                            event = json.loads(adv.data.decode())
                            stream_name = event.get("stream")
                            stream_seq = event.get("stream_seq") or event.get("seq")
                            
                            if not stream_name or not stream_seq:
                                await adv.ack()
                                continue
                            
                            try:
                                # Get original message
                                original_msg = await self._js.get_msg(stream_name, int(stream_seq))
                                
                                # Republish to work queue
                                await self._js.publish(original_msg.subject, original_msg.data)
                                
                                # Delete original if requested
                                if delete_original:
                                    try:
                                        await self._js.delete_msg(stream_name, int(stream_seq))
                                    except:
                                        pass
                                
                                retried += 1
                                logger.debug(f"Retried advisory message from {stream_name}:{stream_seq}")
                                
                            except NotFoundError:
                                # Original message not found, just acknowledge advisory
                                pass
                            
                            await adv.ack()
                            
                        except Exception as e:
                            logger.error(f"Failed to process advisory message: {e}")
                            try:
                                await adv.ack()
                            except:
                                pass
                                
                except NatsTimeout:
                    break
            
            await sub.unsubscribe()
            
        except Exception as e:
            logger.error(f"Failed to retry advisory subject {subject}: {e}")
        
        return retried
    
    # ==================== FEATURE 5: PURGE MESSAGES ====================
    

    
    async def reset_streams(self):
        """Reset all streams by deleting and recreating them."""
        if not await self.ensure_connection():
            logger.error("Cannot reset streams: NATS connection not available")
            return
        
        streams = [
            (self.stream_name, self.work_consumer), 
            (self.dlq_stream, self.dlq_consumer), 
            (self.adv_stream, self.adv_consumer),
            (f"{self.stream_name}_METRICS", f"{self.work_consumer}_ack_stats")
        ]
        
        # First, delete all streams
        for (stream, _) in streams:
            try:
                await self._js.delete_stream(stream)
                logger.info(f"Deleted stream {stream}")
            except Exception as e:
                logger.error(f"Failed to delete stream {stream}: {e}")
        
        # Wait a moment for cleanup
        await asyncio.sleep(0.5)
        
        # Then recreate all infrastructure
        try:
#            await self._ensure_infrastructure()
            logger.info("Successfully recreated all streams and consumers after reset")
        except Exception as e:
            logger.error(f"Failed to recreate infrastructure after reset: {e}")
            raise

    async def purge_all_messages(self):
        """Purge all messages from all streams."""
        if not await self.ensure_connection():
            logger.error("Cannot purge messages: NATS connection not available")
            return
        
        streams_to_purge = [
            (self.stream_name, self.work_consumer), 
            (self.dlq_stream, self.dlq_consumer), 
            (self.adv_stream, self.adv_consumer),
            (f"{self.stream_name}_METRICS", f"{self.work_consumer}_ack_stats")
        ]
        
        for (stream, _) in streams_to_purge:
            try:
                await self._js.purge_stream(stream)
                logger.info(f"purged stream {stream}")
            except Exception as e:
                logger.error(f"Failed to purge stream {stream}: {e}")


    async def purge_work_queue(self):
        """Purge only the work queue."""
        if not await self.ensure_connection():
            logger.error("Cannot purge work queue: NATS connection not available")
            return
        
        try:
            await self._js.purge_stream(self.stream_name)
            logger.info(f"Purged work queue {self.stream_name}")
        except Exception as e:
            logger.error(f"Failed to purge work queue {self.stream_name}: {e}")
            raise
    
    async def purge_dlq(self):
        """Purge only the DLQ."""
        if not await self.ensure_connection():
            logger.error("Cannot purge DLQ: NATS connection not available")
            return
        
        try:
            await self._js.purge_stream(self.dlq_stream)
            logger.info(f"Purged DLQ {self.dlq_stream}")
        except Exception as e:
            logger.error(f"Failed to purge DLQ {self.dlq_stream}: {e}")
            raise
    
    async def purge_advisories(self):
        """Purge only the advisory stream."""
        if not await self.ensure_connection():
            logger.error("Cannot purge advisories: NATS connection not available")
            return
        
        try:
            await self._js.purge_stream(self.adv_stream)
            logger.info(f"Purged advisory stream {self.adv_stream}")
        except Exception as e:
            logger.error(f"Failed to purge advisory stream {self.adv_stream}: {e}")
            raise
    
    async def purge_metrics(self):
        """Purge only the metrics stream."""
        if not await self.ensure_connection():
            logger.error("Cannot purge metrics: NATS connection not available")
            return
        
        try:
            metrics_stream = f"{self.stream_name}_METRICS"
            await self._js.purge_stream(metrics_stream)
            logger.info(f"Purged metrics stream {metrics_stream}")
        except Exception as e:
            logger.error(f"Failed to purge metrics stream {metrics_stream}: {e}")
            raise
    
    # ==================== CONNECTION MANAGEMENT ====================
    
    def is_connected(self) -> bool:
        """Check if connected to NATS."""
        return (self._nc is not None and 
                not self._nc.is_closed)
    
    async def disconnect(self):
        """Disconnect from NATS server."""
        try:
            # Cancel all background tasks
            for task in list(self.background_tasks):
                task.cancel()
            
            # Unsubscribe from all active subscriptions
            for subscription_id in list(self.subscribers.keys()):
                await self.unsubscribe(subscription_id)
            
            # Close NATS connection
            if self._nc and not self._nc.is_closed:
                await self._nc.close()
                logger.info("NATS connection closed")
                
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# ==================== CONVENIENCE METHODS ====================

def get_queue_manager(stream_name: str = None, nats_url: str = None, max_concurrent_callbacks: int = 1) -> NATSQueueManager:
    """
    Get a queue manager instance (singleton pattern)
    
    Args:
        stream_name: Name for the queue stream
        nats_url: NATS server URL (uses config default from environment if not provided)
        max_concurrent_callbacks: Maximum number of concurrent callback executions (default: 1)
        
    Returns:
        NATSQueueManager: Queue manager instance
    """
    return NATSQueueManager(
        nats_url=nats_url,
        stream_name=stream_name,
        max_retries=nats_queue_config.max_retries,
        ack_wait=nats_queue_config.ack_wait,  # Use config value (600 seconds = 10 minutes)
        max_deliver=nats_queue_config.max_deliver,
        max_concurrent_callbacks=max_concurrent_callbacks
    )

queue_manager=get_queue_manager()




# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    """
    Example usage demonstrating callback vs pull subscribe comparison
    """
    import asyncio
    import random
    
    async def example_message_processor(message: QueueMessage) -> bool:
        """Example message processor that simulates work and occasional failures."""
        print(f"[CALLBACK] Processing message: {message.id} with data: {message.data}")
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Simulate occasional failures (20% failure rate for demo)
        if random.random() < 0.2:
            print(f"[CALLBACK] Simulated failure for message: {message.id}")
            return False
        
        print(f"[CALLBACK] Successfully processed message: {message.id}")
        return True
    
 
    async def main():
        """Main demo function comparing callback vs pull subscribe"""
        print("🚀 NATS JetStream: CALLBACK vs PULL SUBSCRIBE COMPARISON")
        print("=" * 70)
        
        
        try:
            # Reset streams for clean demo
            await queue_manager.reset_streams()
            await asyncio.sleep(1)
            
            
            # Final status check
            print("\n📊 Final Message Status:")
            counts = await queue_manager.get_message_counts()
            print(f"✅ Message counts: {counts}")
            

            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            print(f"Full error: {traceback.format_exc()}")
            
        finally:
            # Clean up
            await queue_manager.disconnect()
            print("🔌 Queue manager disconnected")
    
    # Run the comparison demo
    asyncio.run(main())
