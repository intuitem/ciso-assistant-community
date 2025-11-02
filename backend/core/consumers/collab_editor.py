import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


class CollabEditorConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for collaborative text editing.
    Handles real-time synchronization of text content, cursor positions,
    and user presence across multiple clients.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.room_name = "collab_editor"
        self.room_group_name = f"collab_{self.room_name}"

        # Get user from scope (set by authentication middleware)
        self.user = self.scope.get("user")

        # Debug logging
        logger.info(
            "WebSocket connection attempt",
            user_authenticated=getattr(self.user, "is_authenticated", False),
            user_type=type(self.user).__name__,
        )

        # Reject anonymous users
        if not self.user or not getattr(self.user, "is_authenticated", False):
            logger.warning("Anonymous user attempted to connect to collab editor")
            await self.close(code=4001)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        logger.info(
            "User connected to collab editor",
            user_id=str(self.user.id),
            user_email=self.user.email,
            channel_name=self.channel_name,
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, "room_group_name") and hasattr(self, "user"):
            # Broadcast leave message to room
            user_id = (
                str(self.user.id) if self.user and hasattr(self.user, "id") else None
            )
            user_email = getattr(self.user, "email", None) if self.user else None

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_leave",
                    "user_id": user_id,
                    "user_email": user_email,
                },
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            logger.info(
                "User disconnected from collab editor",
                user_id=str(self.user.id) if self.user else None,
                close_code=close_code,
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket client and broadcast to room.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            # Get user info
            user_data = await self.get_user_data()

            # Add user info and sender channel to message
            data["user_id"] = user_data["user_id"]
            data["user_email"] = user_data["user_email"]
            data["user_name"] = user_data["user_name"]
            data["sender_channel"] = self.channel_name  # Add sender's channel name

            # Broadcast to room group
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "broadcast_message", "message": data}
            )

        except json.JSONDecodeError:
            logger.error("Invalid JSON received", text_data=text_data)
        except Exception as e:
            logger.error("Error processing message", error=str(e), text_data=text_data)

    async def broadcast_message(self, event):
        """
        Receive message from room group and send to WebSocket client.
        """
        message = event["message"]

        # Don't send message back to sender
        sender_channel = message.get("sender_channel")
        if sender_channel != self.channel_name:
            # Remove sender_channel before sending to client
            message_to_send = {
                k: v for k, v in message.items() if k != "sender_channel"
            }
            await self.send(text_data=json.dumps(message_to_send))

    async def user_leave(self, event):
        """
        Broadcast user leave message to all clients.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "leave",
                    "user_id": event["user_id"],
                    "user_email": event["user_email"],
                }
            )
        )

    @database_sync_to_async
    def get_user_data(self):
        """
        Get user data from database.
        """
        if not self.user or not self.user.is_authenticated:
            return {
                "user_id": None,
                "user_email": "anonymous",
                "user_name": "Anonymous",
            }

        # Get display name
        if self.user.first_name and self.user.last_name:
            display_name = f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            display_name = self.user.first_name
        elif self.user.email:
            display_name = self.user.email.split("@")[0]
        else:
            display_name = "Anonymous User"

        return {
            "user_id": str(self.user.id),
            "user_email": self.user.email,
            "user_name": display_name,
        }
