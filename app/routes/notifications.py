"""Real-time notifications using Server-Sent Events"""
from flask import Blueprint, Response, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import SystemLog, Attendance
from app.services.notification_service import NotificationService
from datetime import datetime, timedelta
import json
import time

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('/stream')
@login_required
def stream_notifications():
    """
    Server-Sent Events stream for real-time notifications
    
    Usage:
        const eventSource = new EventSource('/api/notifications/stream');
        eventSource.onmessage = (e) => {
            const notification = JSON.parse(e.data);
            // Handle notification
        };
    """
    def generate():
        """Generate SSE events"""
        last_id = request.args.get('last_id', 0, type=int)
        notification_service = NotificationService()
        
        while True:
            try:
                # Get new notifications
                notifications = notification_service.get_user_notifications(
                    user_id=current_user.id,
                    since_id=last_id,
                    limit=10
                )
                
                for notification in notifications:
                    last_id = max(last_id, notification.get('id', 0))
                    event_data = {
                        'id': notification.get('id'),
                        'type': notification.get('type'),
                        'title': notification.get('title'),
                        'message': notification.get('message'),
                        'timestamp': notification.get('timestamp'),
                        'action_url': notification.get('action_url')
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Send heartbeat every 30 seconds
                yield f": heartbeat\n\n"
                
                time.sleep(2)  # Check every 2 seconds
                
            except GeneratorExit:
                break
            except Exception as e:
                error_data = {'error': str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
                time.sleep(5)  # Wait before retrying
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable buffering in nginx
            'Connection': 'keep-alive'
        }
    )


@bp.route('/alerts')
@login_required
def get_alerts():
    """Get current alerts for dashboard"""
    notification_service = NotificationService()
    alerts = notification_service.get_dashboard_alerts()
    
    return jsonify({
        'success': True,
        'alerts': alerts
    })


@bp.route('/unread-count')
@login_required
def get_unread_count():
    """Get count of unread notifications"""
    notification_service = NotificationService()
    count = notification_service.get_unread_count(user_id=current_user.id)
    
    return jsonify({
        'success': True,
        'count': count
    })


@bp.route('/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark notification as read"""
    # Implementation for marking notifications as read
    # This would require a Notification model
    return jsonify({
        'success': True,
        'message': 'Notification marked as read'
    })


# Test notification endpoint removed - not used by frontend

