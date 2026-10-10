"""
Human-in-the-Loop

Manages human approval gates in agent workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging
import uuid

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(str, Enum):
    """Priority of approval requests."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ApprovalRequest:
    """
    A request for human approval.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Source
    run_id: str = ""
    workflow_name: str = ""
    node_id: str = ""
    
    # Content
    title: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    # What's being approved
    action_type: str = ""  # e.g., "deploy", "pr_merge", "ticket_create"
    action_details: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    
    # Assignment
    requested_by: str = ""
    assignees: List[str] = field(default_factory=list)  # Who can approve
    approved_by: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    
    # Response
    response_comments: str = ""
    
    # Tenant
    tenant_id: str = ""
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "node_id": self.node_id,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "action_type": self.action_type,
            "action_details": self.action_details,
            "status": self.status.value,
            "priority": self.priority.value,
            "requested_by": self.requested_by,
            "assignees": self.assignees,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "response_comments": self.response_comments,
        }


class HumanApproval:
    """
    Manages human approval requests.
    
    Features:
    - Create approval requests
    - Track pending approvals
    - Notify assignees
    - Handle expiration
    """
    
    def __init__(
        self,
        notification_service: Optional[Any] = None,
        default_expiry_hours: int = 24,
    ):
        self.notification_service = notification_service
        self.default_expiry_hours = default_expiry_hours
        
        # Active requests
        self._requests: Dict[str, ApprovalRequest] = {}
        
        # Callbacks
        self._on_requested: List[Callable] = []
        self._on_approved: List[Callable] = []
        self._on_rejected: List[Callable] = []
        self._on_expired: List[Callable] = []
    
    async def create_request(
        self,
        run_id: str,
        workflow_name: str,
        node_id: str,
        title: str,
        description: str,
        action_type: str,
        action_details: Dict[str, Any],
        requested_by: str,
        tenant_id: str,
        assignees: Optional[List[str]] = None,
        priority: ApprovalPriority = ApprovalPriority.NORMAL,
        expiry_hours: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            run_id: Workflow run ID
            workflow_name: Workflow name
            node_id: Node requiring approval
            title: Request title
            description: Detailed description
            action_type: Type of action being approved
            action_details: Details of the action
            requested_by: User who triggered the workflow
            tenant_id: Tenant ID
            assignees: Users who can approve
            priority: Request priority
            expiry_hours: Hours until expiration
            context: Additional context
            
        Returns:
            ApprovalRequest
        """
        hours = expiry_hours or self.default_expiry_hours
        
        request = ApprovalRequest(
            run_id=run_id,
            workflow_name=workflow_name,
            node_id=node_id,
            title=title,
            description=description,
            context=context or {},
            action_type=action_type,
            action_details=action_details,
            requested_by=requested_by,
            assignees=assignees or [],
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(hours=hours),
            tenant_id=tenant_id,
        )
        
        self._requests[request.id] = request
        
        # Notify callbacks
        for callback in self._on_requested:
            try:
                await callback(request)
            except Exception as e:
                logger.warning(f"Request callback error: {e}")
        
        # Send notifications
        await self._notify_assignees(request)
        
        logger.info(f"Created approval request {request.id} for {workflow_name}/{node_id}")
        return request
    
    async def approve(
        self,
        request_id: str,
        approved_by: str,
        comments: str = "",
    ) -> bool:
        """
        Approve a request.
        
        Args:
            request_id: Request ID
            approved_by: User approving
            comments: Optional comments
            
        Returns:
            True if approved successfully
        """
        request = self._requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        if request.is_expired:
            request.status = ApprovalStatus.EXPIRED
            return False
        
        # Check if user can approve
        if request.assignees and approved_by not in request.assignees:
            logger.warning(f"User {approved_by} not authorized to approve {request_id}")
            return False
        
        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.response_comments = comments
        request.responded_at = datetime.utcnow()
        
        # Notify callbacks
        for callback in self._on_approved:
            try:
                await callback(request)
            except Exception as e:
                logger.warning(f"Approval callback error: {e}")
        
        logger.info(f"Approval {request_id} approved by {approved_by}")
        return True
    
    async def reject(
        self,
        request_id: str,
        rejected_by: str,
        comments: str = "",
    ) -> bool:
        """
        Reject a request.
        
        Args:
            request_id: Request ID
            rejected_by: User rejecting
            comments: Rejection reason
            
        Returns:
            True if rejected successfully
        """
        request = self._requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        # Check if user can reject
        if request.assignees and rejected_by not in request.assignees:
            logger.warning(f"User {rejected_by} not authorized to reject {request_id}")
            return False
        
        request.status = ApprovalStatus.REJECTED
        request.approved_by = rejected_by  # Store who responded
        request.response_comments = comments
        request.responded_at = datetime.utcnow()
        
        # Notify callbacks
        for callback in self._on_rejected:
            try:
                await callback(request)
            except Exception as e:
                logger.warning(f"Rejection callback error: {e}")
        
        logger.info(f"Approval {request_id} rejected by {rejected_by}")
        return True
    
    async def cancel(self, request_id: str, reason: str = "") -> bool:
        """Cancel a pending request."""
        request = self._requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.CANCELLED
        request.response_comments = reason
        request.responded_at = datetime.utcnow()
        
        return True
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._requests.get(request_id)
    
    def get_pending_requests(
        self,
        tenant_id: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[ApprovalPriority] = None,
    ) -> List[ApprovalRequest]:
        """Get pending requests with optional filtering."""
        requests = [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING and not r.is_expired
        ]
        
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]
        
        if assignee:
            requests = [
                r for r in requests
                if not r.assignees or assignee in r.assignees
            ]
        
        if priority:
            requests = [r for r in requests if r.priority == priority]
        
        # Sort by priority and creation time
        priority_order = {
            ApprovalPriority.URGENT: 0,
            ApprovalPriority.HIGH: 1,
            ApprovalPriority.NORMAL: 2,
            ApprovalPriority.LOW: 3,
        }
        requests.sort(key=lambda r: (priority_order[r.priority], r.created_at))
        
        return requests
    
    def get_requests_for_run(self, run_id: str) -> List[ApprovalRequest]:
        """Get all requests for a workflow run."""
        return [r for r in self._requests.values() if r.run_id == run_id]
    
    async def check_expirations(self) -> List[ApprovalRequest]:
        """Check for and mark expired requests."""
        expired = []
        
        for request in self._requests.values():
            if request.status == ApprovalStatus.PENDING and request.is_expired:
                request.status = ApprovalStatus.EXPIRED
                request.responded_at = datetime.utcnow()
                expired.append(request)
                
                for callback in self._on_expired:
                    try:
                        await callback(request)
                    except Exception as e:
                        logger.warning(f"Expiration callback error: {e}")
        
        return expired
    
    async def _notify_assignees(self, request: ApprovalRequest) -> None:
        """Send notifications to assignees."""
        if not self.notification_service:
            return
        
        try:
            # This would integrate with the notification service
            # await self.notification_service.send(
            #     recipients=request.assignees,
            #     title=f"Approval Required: {request.title}",
            #     body=request.description,
            #     action_url=f"/approvals/{request.id}",
            #     priority=request.priority.value,
            # )
            pass
        except Exception as e:
            logger.error(f"Failed to notify assignees: {e}")
    
    def on_requested(self, callback: Callable) -> None:
        """Register callback for new requests."""
        self._on_requested.append(callback)
    
    def on_approved(self, callback: Callable) -> None:
        """Register callback for approvals."""
        self._on_approved.append(callback)
    
    def on_rejected(self, callback: Callable) -> None:
        """Register callback for rejections."""
        self._on_rejected.append(callback)
    
    def on_expired(self, callback: Callable) -> None:
        """Register callback for expirations."""
        self._on_expired.append(callback)
