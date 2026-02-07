#!/usr/bin/env python3
"""
SLATE Notification System
=========================

Comprehensive notification system with:
- Visual toast notifications
- Sound alerts for task completion and user input required
- Badge/dot indicators for pending items
- WebSocket-based real-time delivery

Notification Types:
- success: Task completed successfully (chime sound)
- error: Error occurred (alert sound)
- warning: Attention needed (warning sound)
- info: Informational update (subtle sound)
- input_required: User action needed (attention sound)
"""

import asyncio
import json
import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications with associated sounds."""
    SUCCESS = "success"          # Task completed
    ERROR = "error"              # Error occurred
    WARNING = "warning"          # Attention needed
    INFO = "info"                # Informational
    INPUT_REQUIRED = "input"     # User action required
    TASK_STARTED = "started"     # Task began
    TASK_PROGRESS = "progress"   # Task update


@dataclass
class Notification:
    """A single notification."""
    id: str
    type: NotificationType
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    sound: bool = True
    persistent: bool = False
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    duration_ms: int = 5000  # Auto-dismiss after 5s
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "sound": self.sound,
            "persistent": self.persistent,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "duration_ms": self.duration_ms,
            "data": self.data
        }


class NotificationManager:
    """
    Manages notifications and sound alerts.

    Provides methods to:
    - Send notifications via WebSocket
    - Queue notifications for batch delivery
    - Track notification history
    - Generate sound data URIs
    """

    def __init__(self):
        self.notifications: List[Notification] = []
        self.unread_count = 0
        self._notification_id = 0

    def _next_id(self) -> str:
        self._notification_id += 1
        return f"notif_{self._notification_id}"

    def create(
        self,
        type: NotificationType,
        title: str,
        message: str,
        sound: bool = True,
        persistent: bool = False,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        duration_ms: int = 5000,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            id=self._next_id(),
            type=type,
            title=title,
            message=message,
            sound=sound,
            persistent=persistent,
            action_url=action_url,
            action_label=action_label,
            duration_ms=duration_ms,
            data=data
        )
        self.notifications.append(notification)
        self.unread_count += 1
        return notification

    def task_completed(self, task_name: str, details: str = "") -> Notification:
        """Create a task completed notification."""
        return self.create(
            type=NotificationType.SUCCESS,
            title="Task Completed",
            message=f"{task_name} finished successfully. {details}".strip(),
            sound=True,
            duration_ms=4000
        )

    def input_required(self, prompt: str, action_url: str = "#") -> Notification:
        """Create an input required notification."""
        return self.create(
            type=NotificationType.INPUT_REQUIRED,
            title="Input Required",
            message=prompt,
            sound=True,
            persistent=True,
            action_url=action_url,
            action_label="Respond"
        )

    def error(self, title: str, message: str) -> Notification:
        """Create an error notification."""
        return self.create(
            type=NotificationType.ERROR,
            title=title,
            message=message,
            sound=True,
            persistent=True,
            duration_ms=10000
        )

    def info(self, title: str, message: str) -> Notification:
        """Create an info notification."""
        return self.create(
            type=NotificationType.INFO,
            title=title,
            message=message,
            sound=False,
            duration_ms=3000
        )

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self.notifications:
            if n.id == notification_id:
                self.unread_count = max(0, self.unread_count - 1)
                return True
        return False

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        return [n.to_dict() for n in self.notifications[-limit:]]

    def clear_all(self) -> None:
        """Clear all notifications."""
        self.notifications = []
        self.unread_count = 0


# Sound data - Base64 encoded short audio clips
# These are placeholder frequencies - in production would use actual audio files
NOTIFICATION_SOUNDS = {
    "success": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj2a2teleXN4k6GNY1FLbpSmxKp7YlZwgJ2dqKF+X1lqeY6knoF0b3qEkZiVinl0e4iSlJCKhHyBhomLiYWCgYaKjo2JhoOGioyMioaEhYiKi4mGhYaIioqJhoWGiImJiIaFhoeIiIiGhoaHiIiHhoaGh4eHhoaGhoeHh4aGhoaHh4eGhoaGh4eHhoaGhoeHh4aGhoaGh4aGhoaGhoeGhoaGhoeHhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaGhoaG",
    "error": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA",
    "warning": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIA=",
    "info": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAABgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBg",
    "input": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAABwoKChgoKDgYGCgoKCg4ODg4SEhISEhYWFhYaGhoaHh4eHiIiIiImJiYmKioqKi4uLi4yMjIyNjY2Njo6OjpCQkJCRkZGRkpKSkpOTk5OUlJSUlZWVlZaWlpaXl5eXmJiYmJmZmZmampqam5ubm5ycnJydnZ2dnp6enp+fn5+goKCgoaGhoaKioqKjo6Oj"
}


def get_sound_for_type(notification_type: NotificationType) -> str:
    """Get the sound data URI for a notification type."""
    type_to_sound = {
        NotificationType.SUCCESS: "success",
        NotificationType.ERROR: "error",
        NotificationType.WARNING: "warning",
        NotificationType.INFO: "info",
        NotificationType.INPUT_REQUIRED: "input",
        NotificationType.TASK_STARTED: "info",
        NotificationType.TASK_PROGRESS: "info"
    }
    sound_key = type_to_sound.get(notification_type, "info")
    return NOTIFICATION_SOUNDS.get(sound_key, "")


# Global notification manager instance
_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get or create the global notification manager."""
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager


# CSS for notification system
NOTIFICATION_CSS = '''
/* ═══════════════════════════════════════════════════════════════════════════ */
/* NOTIFICATION SYSTEM STYLES                                                   */
/* ═══════════════════════════════════════════════════════════════════════════ */

.notification-container {
    position: fixed;
    top: var(--space-lg);
    right: var(--space-lg);
    z-index: 3000;
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    max-width: 400px;
    pointer-events: none;
}

.notification-toast {
    display: flex;
    align-items: flex-start;
    gap: var(--space-md);
    padding: var(--space-md);
    background: var(--bg-elevated);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: var(--rounded-lg);
    box-shadow: var(--shadow-lg);
    pointer-events: auto;
    animation: slideIn 0.3s ease-out, fadeIn 0.3s ease-out;
    transform-origin: top right;
}

.notification-toast.removing {
    animation: slideOut 0.3s ease-in forwards;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.notification-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--rounded-md);
    font-size: 1.25rem;
    flex-shrink: 0;
}

.notification-toast.success .notification-icon {
    background: rgba(34, 197, 94, 0.2);
    color: var(--status-success);
}

.notification-toast.error .notification-icon {
    background: rgba(239, 68, 68, 0.2);
    color: var(--status-error);
}

.notification-toast.warning .notification-icon {
    background: rgba(245, 158, 11, 0.2);
    color: var(--status-warning);
}

.notification-toast.info .notification-icon {
    background: rgba(59, 130, 246, 0.2);
    color: var(--step-active);
}

.notification-toast.input .notification-icon {
    background: rgba(184, 90, 60, 0.2);
    color: var(--slate-primary);
    animation: pulse 1.5s infinite;
}

.notification-content {
    flex: 1;
    min-width: 0;
}

.notification-title {
    font-size: var(--font-sm);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
}

.notification-message {
    font-size: var(--font-sm);
    color: var(--text-secondary);
    line-height: 1.4;
}

.notification-action {
    display: inline-block;
    margin-top: var(--space-sm);
    padding: var(--space-xs) var(--space-md);
    background: var(--slate-primary);
    color: white;
    border: none;
    border-radius: var(--rounded-sm);
    font-size: var(--font-xs);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
}

.notification-action:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.notification-close {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: var(--rounded-sm);
    transition: all var(--transition-fast);
    flex-shrink: 0;
}

.notification-close:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
}

/* Notification Badge */
.notification-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    min-width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 5px;
    background: var(--status-error);
    color: white;
    border-radius: var(--rounded-full);
    font-size: 0.65rem;
    font-weight: 700;
    animation: badgePulse 2s infinite;
}

@keyframes badgePulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}

/* Progress notification variant */
.notification-toast.progress .notification-icon {
    background: rgba(59, 130, 246, 0.2);
}

.notification-progress-bar {
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    overflow: hidden;
    margin-top: var(--space-sm);
}

.notification-progress-fill {
    height: 100%;
    background: var(--step-active);
    border-radius: 2px;
    transition: width 0.3s ease;
}
'''

# JavaScript for notification system
NOTIFICATION_JS = '''
// ═══════════════════════════════════════════════════════════════════════════
// NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

const NotificationSounds = {
    success: null,
    error: null,
    warning: null,
    info: null,
    input: null
};

// Initialize audio context on first user interaction
let audioContext = null;

function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function playNotificationSound(type) {
    initAudio();
    if (!audioContext) return;

    const frequencies = {
        success: [523.25, 659.25, 783.99],  // C5, E5, G5 - pleasant chord
        error: [349.23, 293.66],             // F4, D4 - warning tones
        warning: [440, 440],                 // A4 repeated
        info: [523.25],                      // C5 single
        input: [659.25, 523.25, 659.25]      // E5, C5, E5 - attention
    };

    const freqs = frequencies[type] || frequencies.info;
    const duration = 0.15;

    freqs.forEach((freq, i) => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = freq;
        oscillator.type = "sine";

        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime + i * duration);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + (i + 1) * duration);

        oscillator.start(audioContext.currentTime + i * duration);
        oscillator.stop(audioContext.currentTime + (i + 1) * duration);
    });
}

function showNotification(notification) {
    const container = document.getElementById("notification-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "notification-toast " + notification.type;
    toast.id = notification.id;

    const icons = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ",
        input: "❓",
        started: "▶",
        progress: "⋯"
    };

    toast.innerHTML = `
        <div class="notification-icon">${icons[notification.type] || "ℹ"}</div>
        <div class="notification-content">
            <div class="notification-title">${notification.title}</div>
            <div class="notification-message">${notification.message}</div>
            ${notification.action_url ? `<button class="notification-action" onclick="window.location.href='${notification.action_url}'">${notification.action_label || "View"}</button>` : ""}
        </div>
        <button class="notification-close" onclick="dismissNotification('${notification.id}')">&times;</button>
    `;

    container.appendChild(toast);

    // Play sound
    if (notification.sound) {
        playNotificationSound(notification.type);
    }

    // Auto dismiss
    if (!notification.persistent && notification.duration_ms > 0) {
        setTimeout(() => dismissNotification(notification.id), notification.duration_ms);
    }

    // Update badge count
    updateNotificationBadge();
}

function dismissNotification(id) {
    const toast = document.getElementById(id);
    if (toast) {
        toast.classList.add("removing");
        setTimeout(() => toast.remove(), 300);
    }
    updateNotificationBadge();
}

function updateNotificationBadge() {
    const container = document.getElementById("notification-container");
    const badge = document.getElementById("notification-badge");
    if (container && badge) {
        const count = container.querySelectorAll(".notification-toast:not(.removing)").length;
        badge.textContent = count;
        badge.style.display = count > 0 ? "flex" : "none";
    }
}

// Listen for notification events via WebSocket
function handleNotificationMessage(msg) {
    if (msg.type === "notification") {
        showNotification(msg.data);
    }
}
'''


if __name__ == "__main__":
    # Demo
    manager = get_notification_manager()

    n1 = manager.task_completed("Build Process", "All 42 files compiled")
    print(f"Created: {n1.title} - {n1.message}")

    n2 = manager.input_required("Please review the pull request", "/pr/123")
    print(f"Created: {n2.title} - {n2.message}")

    n3 = manager.error("Build Failed", "TypeScript compilation errors in 3 files")
    print(f"Created: {n3.title} - {n3.message}")

    print(f"\nUnread count: {manager.unread_count}")
    print(f"Recent notifications: {len(manager.get_recent())}")
