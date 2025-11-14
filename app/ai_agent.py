from typing import Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import User, Task, Message, Feedback
from app.utils.date_parser import parse_deadline

class ChatSession:
    """Manages conversation sessions for each user"""
    def __init__(self):
        self.sessions: Dict[int, Dict] = {}
    
    def get_session(self, user_id: int) -> Dict:
        if user_id not in self.sessions:
            self.sessions[user_id] = {"intent": None, "step": None, "data": {}}
        return self.sessions[user_id]
    
    def update_session(self, user_id: int, updates: Dict):
        session = self.get_session(user_id)
        session.update(updates)
    
    def clear_session(self, user_id: int):
        if user_id in self.sessions:
            self.sessions[user_id] = {"intent": None, "step": None, "data": {}}

session_manager = ChatSession()

class AIAgent:
    """Main AI Agent for handling manager and employee conversations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_message(self, user_id: int, message: str) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Main entry point for processing messages"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "User not found.", None, None
        
        if user.role == "manager":
            return self._process_manager_message(user, message)
        else:
            return self._process_employee_message(user, message)
    
    def _process_manager_message(self, user: User, message: str) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Process messages from managers"""
        session = session_manager.get_session(user.id)
        lower_msg = message.lower()
        
        if session.get("intent") is None:
            return self._detect_manager_intent(user, message, lower_msg)
        
        intent = session.get("intent")
        
        if intent == "create_task":
            return self._handle_create_task(user, message, session)
        elif intent == "show_tasks":
            return self._handle_show_tasks_filter(user, message, session)
        elif intent == "modify_task":
            return self._handle_modify_task(user, message, session)
        elif intent == "delete_task":
            return self._handle_delete_task(user, message, session)
        elif intent == "check_progress":
            return self._handle_check_progress_detail(user, message, session)
        elif intent == "send_feedback":
            return self._handle_send_feedback(user, message, session)
        elif intent == "notify_team":
            return self._handle_notify_team(user, message, session)
        
        return self._get_manager_help(), None, None
    
    def _detect_manager_intent(self, user: User, message: str, lower_msg: str) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Detect what the manager wants to do"""
        
        if any(kw in lower_msg for kw in ["give a task", "assign task", "create task", "new task", "add task"]):
            session_manager.update_session(user.id, {"intent": "create_task", "step": "ask_employee", "data": {}})
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            
            if not employees:
                session_manager.clear_session(user.id)
                return "No employees found. Please add employees first.", None, None
            
            employee_list = "\n".join([f"• {e.full_name}" for e in employees])
            return f"Who should I assign this task to?\n\nAvailable employees:\n{employee_list}", None, None
        
        elif any(kw in lower_msg for kw in ["show tasks", "view tasks", "list tasks", "all tasks", "my tasks"]):
            session_manager.update_session(user.id, {"intent": "show_tasks", "step": "ask_filter", "data": {}})
            return (
                "Do you want to see:\n"
                "(1) All tasks\n"
                "(2) Tasks for a specific employee\n"
                "(3) Tasks by deadline date\n\n"
                "Type 1, 2, or 3:"
            ), None, None
        
        elif any(kw in lower_msg for kw in ["modify task", "edit task", "change task", "update task", "change deadline"]):
            tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").all()
            
            if not tasks:
                session_manager.clear_session(user.id)
                return "You don't have any tasks to modify.", None, None
            
            session_manager.update_session(user.id, {"intent": "modify_task", "step": "select_task", "data": {}})
            response = "Which task would you like to modify?\n\n"
            for i, task in enumerate(tasks, 1):
                response += f"{i}. {task.title}\n"
            return response, None, None
        
        elif any(kw in lower_msg for kw in ["delete task", "remove task", "cancel task"]):
            tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").all()
            
            if not tasks:
                session_manager.clear_session(user.id)
                return "You don't have any tasks to delete.", None, None
            
            session_manager.update_session(user.id, {"intent": "delete_task", "step": "select_task", "data": {}})
            response = "Which task would you like to delete?\n\n"
            for i, task in enumerate(tasks, 1):
                response += f"{i}. {task.title}\n"
            return response, None, None
        
        elif any(kw in lower_msg for kw in ["check progress", "task progress", "how are tasks", "status update", "progress for"]):
            session_manager.update_session(user.id, {"intent": "check_progress", "step": "ask_scope", "data": {}})
            return (
                "Do you want:\n"
                "(1) Overall team progress\n"
                "(2) Progress for a specific employee\n\n"
                "Type 1 or 2:"
            ), None, None
        
        elif any(kw in lower_msg for kw in ["send feedback", "give feedback", "feedback to"]):
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            
            if not employees:
                session_manager.clear_session(user.id)
                return "No employees to send feedback to.", None, None
            
            session_manager.update_session(user.id, {"intent": "send_feedback", "step": "select_employee", "data": {}})
            response = "Who would you like to send feedback to?\n\n"
            for emp in employees:
                response += f"• {emp.full_name}\n"
            return response, None, None
        
        elif any(kw in lower_msg for kw in ["notify team", "create event", "announce", "broadcast", "send announcement"]):
            session_manager.update_session(user.id, {"intent": "notify_team", "step": "ask_recipients", "data": {}})
            return (
                "Who should receive this notification?\n\n"
                "(1) All employees\n"
                "(2) Specific employee\n\n"
                "Type 1 or 2:"
            ), None, None
        
        else:
            return self._get_manager_help(), None, None
    
    def _handle_create_task(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle task creation conversation flow"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "ask_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if employee:
                session_manager.update_session(user.id, {
                    "step": "ask_title",
                    "data": {**data, "employee_id": employee.id, "employee_name": employee.full_name}
                })
                return f"Great! Assigning to {employee.full_name}.\n\nWhat's the task title?", None, None
            else:
                return f"I couldn't find '{message}'. Please type the employee's name again.", None, None
        
        elif step == "ask_title":
            data["title"] = message
            session_manager.update_session(user.id, {"step": "ask_description", "data": data})
            return "Perfect! Now describe the task in detail:", None, None
        
        elif step == "ask_description":
            data["description"] = message
            session_manager.update_session(user.id, {"step": "ask_file", "data": data})
            return "Would you like to attach a file to this task?\n\nType 'yes' to attach a file, or 'no' to skip.", None, None
        
        elif step == "ask_file":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "wait_for_file", "data": data})
                return "Please upload the file now (click the 📎 button and select your file).", None, None
            else:
                session_manager.update_session(user.id, {"step": "ask_deadline", "data": data})
                return "When's the deadline?\n\n(Examples: 'tomorrow', 'next Monday', 'this Friday', 'in 5 days', '2025-11-15')", None, None
        
        elif step == "wait_for_file":
            if message.lower() in ["skip", "no", "cancel"]:
                session_manager.update_session(user.id, {"step": "ask_deadline", "data": data})
                return "No file attached.\n\nWhen's the deadline?\n\n(Examples: 'tomorrow', 'next Monday', 'this Friday', 'in 5 days')", None, None
            elif data.get("file_path"):
                session_manager.update_session(user.id, {"step": "ask_deadline", "data": data})
                return f"File received: {data.get('filename')}\n\nWhen's the deadline?\n\n(Examples: 'tomorrow', 'next Monday', 'this Friday', 'in 5 days')", None, None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to continue without a file.", None, None
        
        elif step == "ask_deadline":
            try:
                deadline = parse_deadline(message)
                if deadline <= datetime.now():
                    return "Deadline must be in the future. Please try again.", None, None
                
                data["deadline"] = deadline
                session_manager.update_session(user.id, {"step": "confirm", "data": data})
                
                file_info = f"\n📎 File: {data.get('filename')}" if data.get('file_path') else "\n(No file attached)"
                
                return (
                    f"Confirm Task Creation:\n\n"
                    f"📋 Task: {data['title']}\n"
                    f"👤 Assigned to: {data['employee_name']}\n"
                    f"📅 Deadline: {deadline.strftime('%B %d, %Y (%A)')}\n"
                    f"📝 Description: {data['description']}{file_info}\n\n"
                    f"Type 'yes' to create or 'no' to cancel."
                ), None, None
            except Exception as e:
                return f"Invalid date format. Try: 'tomorrow', 'next Monday', 'this Friday', 'in 5 days', or '2025-11-15'.", None, None
        
        elif step == "confirm":
            if message.lower() in ["yes", "y", "confirm", "ok"]:
                task = Task(
                    title=data["title"],
                    description=data["description"],
                    assigned_to=data["employee_id"],
                    created_by=user.id,
                    deadline=data["deadline"],
                    status="pending",
                    file_path=data.get("file_path")
                )
                self.db.add(task)
                self.db.commit()
                self.db.refresh(task)
                
                # Create notification with ORIGINAL filename preserved
                if data.get('file_path') and data.get('filename'):
                    file_note = f"\n\n📎 {data.get('filename')}"
                else:
                    file_note = ""
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"📋 New Task Assigned!\n\n{task.title}\n\nDeadline: {task.deadline.strftime('%B %d, %Y')}\n\n{task.description}{file_note}",
                    file_path=data.get("file_path")
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                
                file_msg = f"\n📎 File attached: {data.get('filename')}" if data.get('file_path') else ""
                return (
                    f"🎉 Task Created Successfully!\n\n"
                    f"✅ Task: {task.title}\n"
                    f"👤 Assigned to: {data['employee_name']}\n"
                    f"📅 Due: {task.deadline.strftime('%B %d, %Y (%A)')}{file_msg}\n\n"
                    f"I've notified them!",
                    "task_created",
                    {"task_id": task.id}
                )
            else:
                session_manager.clear_session(user.id)
                return "Task creation cancelled.", None, None
        
        return "Something went wrong. Let's start over.", None, None
    
    def _handle_show_tasks_filter(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle task filtering"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "ask_filter":
            if "1" in message or "all" in message.lower():
                tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").order_by(Task.deadline).all()
                session_manager.clear_session(user.id)
                
                if not tasks:
                    return "You haven't assigned any tasks yet.", None, None
                
                response = f"📋 Your Assigned Tasks ({len(tasks)}):\n\n"
                for i, task in enumerate(tasks, 1):
                    employee = self.db.query(User).filter(User.id == task.assigned_to).first()
                    status_emoji = {"completed": "✅", "late": "🔴", "in_progress": "🟡", "pending": "⏳"}.get(task.status, "❓")
                    days_until = (task.deadline - datetime.now()).days
                    file_marker = " 📎" if task.file_path else ""
                    
                    response += f"{i}. {status_emoji} {task.title}{file_marker}\n"
                    response += f"   👤 {employee.full_name}\n"
                    response += f"   📅 {task.deadline.strftime('%b %d, %Y')} ({days_until} days)\n"
                    response += f"   📊 {task.status.replace('_', ' ').title()}\n\n"
                
                return response, "show_tasks", {"tasks": [t.id for t in tasks]}
            
            elif "2" in message:
                session_manager.update_session(user.id, {"step": "filter_by_employee", "data": data})
                employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                response = "Which employee?\n\n"
                for emp in employees:
                    response += f"• {emp.full_name}\n"
                return response, None, None
            
            elif "3" in message:
                session_manager.update_session(user.id, {"step": "filter_by_date", "data": data})
                return "Which date? (Examples: 'next Monday', 'this Friday', '2025-11-15')", None, None
            
            else:
                return "Please choose 1, 2, or 3.", None, None
        
        elif step == "filter_by_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if not employee:
                return f"Couldn't find '{message}'. Please try again.", None, None
            
            tasks = self.db.query(Task).filter(
                Task.created_by == user.id,
                Task.assigned_to == employee.id,
                Task.status != "deleted"
            ).order_by(Task.deadline).all()
            
            session_manager.clear_session(user.id)
            
            if not tasks:
                return f"No tasks found for {employee.full_name}.", None, None
            
            response = f"📋 Tasks for {employee.full_name} ({len(tasks)}):\n\n"
            for i, task in enumerate(tasks, 1):
                status_emoji = {"completed": "✅", "late": "🔴", "in_progress": "🟡", "pending": "⏳"}.get(task.status, "❓")
                file_marker = " 📎" if task.file_path else ""
                response += f"{i}. {status_emoji} {task.title}{file_marker}\n"
                response += f"   📅 {task.deadline.strftime('%b %d, %Y')}\n"
                response += f"   📊 {task.status.replace('_', ' ').title()}\n\n"
            
            return response, "show_tasks_filtered", {"employee_id": employee.id}
        
        elif step == "filter_by_date":
            try:
                deadline = parse_deadline(message)
                tasks = self.db.query(Task).filter(
                    Task.created_by == user.id,
                    Task.status != "deleted"
                ).all()
                
                # Filter tasks by date (compare date only, not time)
                matching_tasks = [t for t in tasks if t.deadline.date() == deadline.date()]
                
                session_manager.clear_session(user.id)
                
                if not matching_tasks:
                    return f"No tasks found for {deadline.strftime('%B %d, %Y')}.", None, None
                
                response = f"📋 Tasks due on {deadline.strftime('%B %d, %Y')} ({len(matching_tasks)}):\n\n"
                for i, task in enumerate(matching_tasks, 1):
                    employee = self.db.query(User).filter(User.id == task.assigned_to).first()
                    status_emoji = {"completed": "✅", "late": "🔴", "in_progress": "🟡", "pending": "⏳"}.get(task.status, "❓")
                    file_marker = " 📎" if task.file_path else ""
                    response += f"{i}. {status_emoji} {task.title}{file_marker}\n"
                    response += f"   👤 {employee.full_name}\n"
                    response += f"   📊 {task.status.replace('_', ' ').title()}\n\n"
                
                return response, "show_tasks_filtered", None
            except:
                return "Invalid date. Try: 'next Monday', 'this Friday', or '2025-11-15'.", None, None
        
        return "Something went wrong.", None, None
    
    def _handle_modify_task(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle task modification"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "select_task":
            tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").all()
            
            task = None
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
            else:
                task = next((t for t in tasks if message.lower() in t.title.lower()), None)
            
            if task:
                session_manager.update_session(user.id, {
                    "step": "select_field",
                    "data": {**data, "task_id": task.id, "task_title": task.title, "employee_id": task.assigned_to}
                })
                return (
                    f"What would you like to change about '{task.title}'?\n\n"
                    f"(1) Title\n"
                    f"(2) Description\n"
                    f"(3) Deadline\n"
                    f"(4) Assigned employee\n"
                    f"(5) Attached file\n\n"
                    f"Type 1, 2, 3, 4, or 5:"
                ), None, None
            else:
                return "Task not found. Please try again.", None, None
        
        elif step == "select_field":
            if "1" in message or "title" in message.lower():
                session_manager.update_session(user.id, {"step": "modify_title", "data": data})
                return "What's the new title?", None, None
            elif "2" in message or "description" in message.lower():
                session_manager.update_session(user.id, {"step": "modify_description", "data": data})
                return "What's the new description?", None, None
            elif "3" in message or "deadline" in message.lower():
                session_manager.update_session(user.id, {"step": "modify_deadline", "data": data})
                return "What's the new deadline?\n\n(Examples: 'next Monday', 'this Friday', 'in 5 days', '2025-11-15')", None, None
            elif "4" in message or "employee" in message.lower():
                employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                session_manager.update_session(user.id, {"step": "modify_employee", "data": data})
                response = "Who should the task be assigned to?\n\n"
                for emp in employees:
                    response += f"• {emp.full_name}\n"
                return response, None, None
            elif "5" in message or "file" in message.lower():
                session_manager.update_session(user.id, {"step": "modify_file", "data": data})
                return "Please upload the new file now (click the 📎 button).", None, None
            else:
                return "Please choose 1, 2, 3, 4, or 5.", None, None
        
        elif step == "modify_title":
            task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
            employee = self.db.query(User).filter(User.id == data["employee_id"]).first()
            old_title = task.title
            task.title = message
            self.db.commit()
            
            notification = Message(
                sender_id=None,
                receiver_id=data["employee_id"],
                content=f"ℹ️ Task title updated!\n\nOld: {old_title}\nNew: {message}"
            )
            self.db.add(notification)
            self.db.commit()
            
            session_manager.clear_session(user.id)
            return f"✅ Task title updated! {employee.full_name} has been notified.", "task_modified", None
        
        elif step == "modify_description":
            task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
            employee = self.db.query(User).filter(User.id == data["employee_id"]).first()
            task.description = message
            self.db.commit()
            
            notification = Message(
                sender_id=None,
                receiver_id=data["employee_id"],
                content=f"ℹ️ Task description updated!\n\nTask: {task.title}\n\nNew description: {message}"
            )
            self.db.add(notification)
            self.db.commit()
            
            session_manager.clear_session(user.id)
            return f"✅ Task description updated! {employee.full_name} has been notified.", "task_modified", None
        
        elif step == "modify_deadline":
            try:
                new_deadline = parse_deadline(message)
                if new_deadline <= datetime.now():
                    return "Deadline must be in the future. Please try again.", None, None
                
                task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
                employee = self.db.query(User).filter(User.id == data["employee_id"]).first()
                old_deadline = task.deadline
                task.deadline = new_deadline
                self.db.commit()
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"⚠️ Task deadline updated!\n\n{task.title}\n\nNew deadline: {new_deadline.strftime('%B %d, %Y (%A)')}"
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return (
                    f"✅ Task deadline updated!\n\n"
                    f"Old: {old_deadline.strftime('%B %d, %Y (%A)')}\n"
                    f"New: {new_deadline.strftime('%B %d, %Y (%A)')}\n\n"
                    f"{employee.full_name} has been notified."
                ), "task_modified", None
            except:
                return "Invalid date format. Try: 'next Monday', 'this Friday', 'in 5 days', or '2025-11-15'.", None, None
        
        elif step == "modify_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            new_employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if not new_employee:
                return f"Couldn't find '{message}'. Please try again.", None, None
            
            task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
            old_employee = self.db.query(User).filter(User.id == task.assigned_to).first()
            
            notification_old = Message(
                sender_id=None,
                receiver_id=old_employee.id,
                content=f"ℹ️ Task '{task.title}' has been reassigned to {new_employee.full_name}."
            )
            self.db.add(notification_old)
            
            task.assigned_to = new_employee.id
            self.db.commit()
            
            # Include original filename in notification
            if task.file_path:
                # Extract filename from URL or use generic
                url_parts = task.file_path.split('/')
                filename = url_parts[-1].split('?')[0] if url_parts else 'attached_file'
                file_note = f"\n\n📎 {filename}"
            else:
                file_note = ""
            
            notification_new = Message(
                sender_id=None,
                receiver_id=new_employee.id,
                content=f"📋 New task assigned to you!\n\n{task.title}\n\nDeadline: {task.deadline.strftime('%B %d, %Y')}\n\n{task.description}{file_note}",
                file_path=task.file_path
            )
            self.db.add(notification_new)
            self.db.commit()
            
            session_manager.clear_session(user.id)
            return (
                f"✅ Task reassigned!\n\n"
                f"From: {old_employee.full_name}\n"
                f"To: {new_employee.full_name}\n\n"
                f"Both employees have been notified."
            ), "task_modified", None
        
        elif step == "modify_file":
            if message.lower() in ["skip", "no", "cancel"]:
                session_manager.clear_session(user.id)
                return "File modification cancelled.", None, None
            elif data.get("file_path"):
                task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
                employee = self.db.query(User).filter(User.id == data["employee_id"]).first()
                
                task.file_path = data.get("file_path")
                self.db.commit()
                
                # Include ORIGINAL filename in message
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"📎 Task file updated!\n\nTask: {task.title}\n\n📎 {data.get('filename')}",
                    file_path=data.get("file_path")
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Task file updated to '{data.get('filename')}'! {employee.full_name} has been notified.", "task_modified", None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to cancel.", None, None
        
        return "Something went wrong.", None, None
    
    def _handle_delete_task(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle task deletion"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "select_task":
            tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").all()
            
            task = None
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
            
            if task:
                session_manager.update_session(user.id, {
                    "step": "confirm",
                    "data": {"task_id": task.id, "task_title": task.title, "employee_id": task.assigned_to}
                })
                return f"Are you sure you want to delete '{task.title}'?\n\nThis cannot be undone.\n\nType 'yes' to confirm or 'no' to cancel.", None, None
            else:
                return "Invalid selection. Please try again.", None, None
        
        elif step == "confirm":
            if message.lower() in ["yes", "y", "confirm"]:
                task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
                task.status = "deleted"
                self.db.commit()
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"ℹ️ The task '{data['task_title']}' has been removed by your manager."
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Task '{data['task_title']}' has been deleted and employee notified.", "task_deleted", {"task_id": task.id}
            else:
                session_manager.clear_session(user.id)
                return "Deletion cancelled.", None, None
        
        return "Something went wrong.", None, None
    
    def _handle_check_progress_detail(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle detailed progress checking"""
        step = session.get("step")
        
        if step == "ask_scope":
            if "1" in message or "overall" in message.lower() or "team" in message.lower():
                tasks = self.db.query(Task).filter(Task.created_by == user.id, Task.status != "deleted").all()
                session_manager.clear_session(user.id)
                
                if not tasks:
                    return "No tasks to track yet!", None, None
                
                completed = len([t for t in tasks if t.status == "completed"])
                pending = len([t for t in tasks if t.status == "pending"])
                in_progress = len([t for t in tasks if t.status == "in_progress"])
                late = len([t for t in tasks if t.status == "late" or (t.deadline < datetime.now() and t.status != "completed")])
                
                response = f"📊 Team Progress Overview\n\n"
                response += f"✅ Completed: {completed}\n"
                response += f"🟡 In Progress: {in_progress}\n"
                response += f"⏳ Pending: {pending}\n"
                response += f"🔴 Late: {late}\n\n"
                response += f"Total Tasks: {len(tasks)}\n"
                response += f"Completion Rate: {int(completed/len(tasks)*100) if tasks else 0}%"
                
                return response, "check_progress", {"completed": completed, "total": len(tasks)}
            
            elif "2" in message:
                employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                session_manager.update_session(user.id, {"step": "select_employee", "data": {}})
                response = "Which employee?\n\n"
                for emp in employees:
                    response += f"• {emp.full_name}\n"
                return response, None, None
            else:
                return "Please choose 1 or 2.", None, None
        
        elif step == "select_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if not employee:
                return f"Couldn't find '{message}'. Please try again.", None, None
            
            tasks = self.db.query(Task).filter(
                Task.created_by == user.id,
                Task.assigned_to == employee.id,
                Task.status != "deleted"
            ).all()
            
            session_manager.clear_session(user.id)
            
            if not tasks:
                return f"No tasks found for {employee.full_name}.", None, None
            
            completed = len([t for t in tasks if t.status == "completed"])
            pending = len([t for t in tasks if t.status == "pending"])
            in_progress = len([t for t in tasks if t.status == "in_progress"])
            
            response = f"📊 Progress for {employee.full_name}\n\n"
            response += f"Total tasks: {len(tasks)}\n"
            response += f"✅ Completed: {completed}\n"
            response += f"🟡 In Progress: {in_progress}\n"
            response += f"⏳ Pending: {pending}\n"
            response += f"Completion Rate: {int(completed/len(tasks)*100) if tasks else 0}%"
            
            return response, "check_progress_employee", {"employee_id": employee.id}
        
        return "Something went wrong.", None, None
    
    def _handle_send_feedback(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Send feedback to employee"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "select_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if employee:
                tasks = self.db.query(Task).filter(
                    Task.created_by == user.id,
                    Task.assigned_to == employee.id,
                    Task.status != "deleted"
                ).all()
                
                if tasks:
                    session_manager.update_session(user.id, {
                        "step": "select_task",
                        "data": {**data, "employee_id": employee.id, "employee_name": employee.full_name, "tasks": [t.id for t in tasks]}
                    })
                    response = f"On which task would you like to give feedback to {employee.full_name}?\n\n"
                    for i, task in enumerate(tasks, 1):
                        response += f"{i}. {task.title}\n"
                    response += f"\nOr type 'general' for general feedback."
                    return response, None, None
                else:
                    session_manager.update_session(user.id, {
                        "step": "ask_feedback",
                        "data": {**data, "employee_id": employee.id, "employee_name": employee.full_name, "task_id": None}
                    })
                    return f"What feedback would you like to give to {employee.full_name}?", None, None
            else:
                return f"Couldn't find '{message}'. Please try again.", None, None
        
        elif step == "select_task":
            if "general" in message.lower():
                session_manager.update_session(user.id, {"step": "ask_feedback", "data": {**data, "task_id": None}})
                return f"What general feedback would you like to give to {data['employee_name']}?", None, None
            
            tasks = self.db.query(Task).filter(Task.id.in_(data["tasks"])).all()
            task = None
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
            
            if task:
                session_manager.update_session(user.id, {"step": "ask_feedback", "data": {**data, "task_id": task.id, "task_title": task.title}})
                return f"What feedback would you like to give about '{task.title}'?", None, None
            else:
                return "Invalid selection. Please try again.", None, None
        
        elif step == "ask_feedback":
            session_manager.update_session(user.id, {"step": "ask_file", "data": {**data, "feedback_text": message}})
            return "Would you like to attach a file?\n\nType 'yes' to attach, or 'no' to send without a file.", None, None
        
        elif step == "ask_file":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "wait_for_file", "data": data})
                return "Please upload the file now (click the 📎 button).", None, None
            else:
                feedback_text = data.get("feedback_text")
                feedback = Feedback(
                    from_user_id=user.id,
                    to_user_id=data["employee_id"],
                    task_id=data.get("task_id"),
                    content=feedback_text,
                    timestamp=datetime.utcnow()
                )
                self.db.add(feedback)
                
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"💬 New Feedback from {user.full_name}{task_context}:\n\n{feedback_text}"
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Feedback sent to {data['employee_name']}!", "feedback_sent", None
        
        elif step == "wait_for_file":
            if message.lower() in ["skip", "no", "cancel"]:
                feedback_text = data.get("feedback_text")
                feedback = Feedback(
                    from_user_id=user.id,
                    to_user_id=data["employee_id"],
                    task_id=data.get("task_id"),
                    content=feedback_text,
                    timestamp=datetime.utcnow()
                )
                self.db.add(feedback)
                
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"💬 New Feedback from {user.full_name}{task_context}:\n\n{feedback_text}"
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Feedback sent to {data['employee_name']}!", "feedback_sent", None
            elif data.get("file_path"):
                feedback_text = data.get("feedback_text")
                
                feedback = Feedback(
                    from_user_id=user.id,
                    to_user_id=data["employee_id"],
                    task_id=data.get("task_id"),
                    content=feedback_text,
                    timestamp=datetime.utcnow(),
                    file_path=data.get("file_path")
                )
                self.db.add(feedback)
                
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                notification = Message(
                    sender_id=None,
                    receiver_id=data["employee_id"],
                    content=f"💬 New Feedback from {user.full_name}{task_context}:\n\n{feedback_text}\n\n📎 {data.get('filename')}",
                    file_path=data.get("file_path")
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Feedback with file sent to {data['employee_name']}!", "feedback_sent", None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to send without a file.", None, None
        
        return "Something went wrong.", None, None
    
    def _handle_notify_team(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle team notifications"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "ask_recipients":
            if "1" in message or "all" in message.lower():
                session_manager.update_session(user.id, {"step": "ask_message", "data": {**data, "recipient_type": "all"}})
                return "What's the announcement message?", None, None
            elif "2" in message:
                employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                session_manager.update_session(user.id, {"step": "select_employee", "data": data})
                response = "Which employee?\n\n"
                for emp in employees:
                    response += f"• {emp.full_name}\n"
                return response, None, None
            else:
                return "Please choose 1 or 2.", None, None
        
        elif step == "select_employee":
            employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
            employee = next((e for e in employees if message.lower() in e.full_name.lower()), None)
            
            if employee:
                session_manager.update_session(user.id, {"step": "ask_message", "data": {**data, "recipient_type": "single", "employee_id": employee.id, "employee_name": employee.full_name}})
                return f"What message would you like to send to {employee.full_name}?", None, None
            else:
                return f"Couldn't find '{message}'. Please try again.", None, None
        
        elif step == "ask_message":
            session_manager.update_session(user.id, {"step": "ask_file", "data": {**data, "message_text": message}})
            return "Would you like to attach a file?\n\nType 'yes' to attach, or 'no' to send without a file.", None, None
        
        elif step == "ask_file":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "wait_for_file", "data": data})
                return "Please upload the file now (click the 📎 button).", None, None
            else:
                message_text = data.get("message_text")
                
                if data["recipient_type"] == "all":
                    employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                    
                    for emp in employees:
                        notification = Message(
                            sender_id=None,
                            receiver_id=emp.id,
                            content=f"📢 Announcement from {user.full_name}:\n\n{message_text}"
                        )
                        self.db.add(notification)
                    
                    self.db.commit()
                    session_manager.clear_session(user.id)
                    return f"✅ Announcement sent to {len(employees)} employee(s)!", "announcement_sent", {"count": len(employees)}
                
                else:
                    notification = Message(
                        sender_id=None,
                        receiver_id=data["employee_id"],
                        content=f"💬 Message from {user.full_name}:\n\n{message_text}"
                    )
                    self.db.add(notification)
                    self.db.commit()
                    
                    session_manager.clear_session(user.id)
                    return f"✅ Message sent to {data['employee_name']}!", "message_sent", None
        
        elif step == "wait_for_file":
            if message.lower() in ["skip", "no", "cancel"]:
                message_text = data.get("message_text")
                
                if data["recipient_type"] == "all":
                    employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                    
                    for emp in employees:
                        notification = Message(
                            sender_id=None,
                            receiver_id=emp.id,
                            content=f"📢 Announcement from {user.full_name}:\n\n{message_text}"
                        )
                        self.db.add(notification)
                    
                    self.db.commit()
                    session_manager.clear_session(user.id)
                    return f"✅ Announcement sent to {len(employees)} employee(s)!", "announcement_sent", {"count": len(employees)}
                else:
                    notification = Message(
                        sender_id=None,
                        receiver_id=data["employee_id"],
                        content=f"💬 Message from {user.full_name}:\n\n{message_text}"
                    )
                    self.db.add(notification)
                    self.db.commit()
                    
                    session_manager.clear_session(user.id)
                    return f"✅ Message sent to {data['employee_name']}!", "message_sent", None
            elif data.get("file_path"):
                message_text = data.get("message_text")
                
                if data["recipient_type"] == "all":
                    employees = self.db.query(User).filter(User.role == "employee", User.is_active == True).all()
                    
                    for emp in employees:
                        notification = Message(
                            sender_id=None,
                            receiver_id=emp.id,
                            content=f"📢 Announcement from {user.full_name}:\n\n{message_text}\n\n📎 {data.get('filename')}",
                            file_path=data.get("file_path")
                        )
                        self.db.add(notification)
                    
                    self.db.commit()
                    session_manager.clear_session(user.id)
                    return f"✅ Announcement with file sent to {len(employees)} employee(s)!", "announcement_sent", {"count": len(employees)}
                
                else:
                    notification = Message(
                        sender_id=None,
                        receiver_id=data["employee_id"],
                        content=f"💬 Message from {user.full_name}:\n\n{message_text}\n\n📎 {data.get('filename')}",
                        file_path=data.get("file_path")
                    )
                    self.db.add(notification)
                    self.db.commit()
                    
                    session_manager.clear_session(user.id)
                    return f"✅ Message with file sent to {data['employee_name']}!", "message_sent", None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to send without a file.", None, None
        
        return "Something went wrong.", None, None
    
    def _process_employee_message(self, user: User, message: str) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Process messages from employees"""
        session = session_manager.get_session(user.id)
        lower_msg = message.lower()
        
        if session.get("intent") is None:
            return self._detect_employee_intent(user, message, lower_msg)
        
        intent = session.get("intent")
        
        if intent == "complete_task":
            return self._handle_complete_task(user, message, session)
        elif intent == "view_feedback":
            return self._handle_view_feedback(user, message, session)
        elif intent == "ask_question":
            return self._handle_ask_question(user, message, session)
        
        return self._get_employee_help(), None, None
    
    def _detect_employee_intent(self, user: User, message: str, lower_msg: str) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Detect what the employee wants"""
        
        if any(kw in lower_msg for kw in ["my tasks", "show tasks", "what tasks", "list tasks", "tasks"]):
            tasks = self.db.query(Task).filter(
                Task.assigned_to == user.id,
                Task.status != "deleted"
            ).order_by(Task.deadline).all()
            
            if not tasks:
                return "🎉 You don't have any assigned tasks right now!", None, None
            
            response = f"📋 Your Tasks ({len(tasks)}):\n\n"
            for i, task in enumerate(tasks, 1):
                manager = self.db.query(User).filter(User.id == task.created_by).first()
                status_emoji = {"completed": "✅", "late": "🔴", "in_progress": "🟡", "pending": "⏳"}.get(task.status, "❓")
                days_until = (task.deadline - datetime.now()).days
                due_text = f"{days_until} days" if days_until > 0 else "Today!" if days_until == 0 else f"Overdue by {abs(days_until)} days"
                file_info = " 📎" if task.file_path else ""
                
                response += f"{i}. {status_emoji} {task.title}{file_info}\n"
                response += f"   📝 {task.description[:60]}\n"
                response += f"   📅 Due: {task.deadline.strftime('%b %d')} ({due_text})\n"
                response += f"   👤 From: {manager.full_name}\n\n"
            
            return response, "my_tasks", {"tasks": [t.id for t in tasks]}
        
        elif any(kw in lower_msg for kw in ["complete", "finished", "done", "submit"]):
            active_tasks = self.db.query(Task).filter(
                Task.assigned_to == user.id,
                Task.status.in_(["pending", "in_progress"])
            ).all()
            
            if not active_tasks:
                return "You don't have any active tasks to complete. Great job! 🎉", None, None
            
            if len(active_tasks) == 1:
                task = active_tasks[0]
                session_manager.update_session(user.id, {
                    "intent": "complete_task",
                    "step": "show_task_details",
                    "data": {
                        "task_id": task.id,
                        "task_title": task.title,
                        "manager_id": task.created_by
                    }
                })
                
                file_info = f"\n📎 File attached to task" if task.file_path else ""
                
                return (
                    f"📋 Task Details:\n\n"
                    f"Title: {task.title}\n"
                    f"Description: {task.description}\n"
                    f"Deadline: {task.deadline.strftime('%B %d, %Y')}{file_info}\n\n"
                    f"Do you want to submit this task?\n\nType 'yes' to continue or 'no' to cancel."
                ), None, None
            else:
                session_manager.update_session(user.id, {"intent": "complete_task", "step": "select_task", "data": {}})
                response = "Which task did you complete?\n\n"
                for i, task in enumerate(active_tasks, 1):
                    response += f"{i}. {task.title}\n"
                return response, None, None
        
        elif any(kw in lower_msg for kw in ["deadline", "when is", "due date", "next deadline"]):
            tasks = self.db.query(Task).filter(
                Task.assigned_to == user.id,
                Task.status.in_(["pending", "in_progress"])
            ).order_by(Task.deadline).all()
            
            if not tasks:
                return "You don't have any pending tasks with deadlines! 🎉", None, None
            
            next_task = tasks[0]
            days_until = (next_task.deadline - datetime.now()).days
            
            return (
                f"⏰ Your Next Deadline:\n\n"
                f"📋 Task: {next_task.title}\n"
                f"📅 Due: {next_task.deadline.strftime('%B %d, %Y (%A)')}\n"
                f"⏱️ Time left: {days_until} days\n\n"
                f"{'🔴 This is urgent!' if days_until <= 2 else '🟡 Coming up soon!' if days_until <= 5 else '✅ You have time!'}"
            ), "next_deadline", {"task_id": next_task.id}
        
        elif any(kw in lower_msg for kw in ["feedback", "my feedback", "show feedback"]):
            feedback_list = self.db.query(Feedback).filter(
                Feedback.to_user_id == user.id
            ).order_by(Feedback.timestamp.desc()).limit(5).all()
            
            if not feedback_list:
                return "You don't have any feedback yet.", None, None
            
            response = f"💬 Recent Feedback ({len(feedback_list)}):\n\n"
            for fb in feedback_list:
                manager = self.db.query(User).filter(User.id == fb.from_user_id).first()
                file_info = " 📎" if fb.file_path else ""
                response += f"👤 From {manager.full_name}{file_info}\n"
                response += f"📅 {fb.timestamp.strftime('%b %d, %Y')}\n"
                response += f"💬 {fb.content}\n\n"
            
            return response, "view_feedback", None
        
        elif any(kw in lower_msg for kw in ["question", "ask", "i have a question", "can i ask"]):
            session_manager.update_session(user.id, {"intent": "ask_question", "step": "select_manager", "data": {}})
            managers = self.db.query(User).filter(User.role == "manager", User.is_active == True).all()
            
            if not managers:
                session_manager.clear_session(user.id)
                return "No managers available at the moment.", None, None
            
            response = "Who would you like to ask?\n\n"
            for mgr in managers:
                response += f"• {mgr.full_name}\n"
            return response, None, None
        
        elif any(kw in lower_msg for kw in ["help", "how do i"]):
            return self._get_employee_help(), None, None
        
        else:
            return self._get_employee_help(), None, None
    
    def _handle_complete_task(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle task completion"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "select_task":
            active_tasks = self.db.query(Task).filter(
                Task.assigned_to == user.id,
                Task.status.in_(["pending", "in_progress"])
            ).all()
            
            task = None
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(active_tasks):
                    task = active_tasks[idx]
            else:
                task = next((t for t in active_tasks if message.lower() in t.title.lower()), None)
            
            if task:
                session_manager.update_session(user.id, {
                    "step": "show_task_details",
                    "data": {
                        "task_id": task.id,
                        "task_title": task.title,
                        "manager_id": task.created_by
                    }
                })
                
                file_info = f"\n📎 File attached to task" if task.file_path else ""
                
                return (
                    f"📋 Task Details:\n\n"
                    f"Title: {task.title}\n"
                    f"Description: {task.description}\n"
                    f"Deadline: {task.deadline.strftime('%B %d, %Y')}{file_info}\n\n"
                    f"Do you want to submit this task?\n\nType 'yes' to continue or 'no' to cancel."
                ), None, None
            else:
                return "Task not found. Please try again.", None, None
        
        elif step == "show_task_details":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "ask_completion_note", "data": data})
                return "Please write a completion note or summary of what you did:", None, None
            else:
                session_manager.clear_session(user.id)
                return "Task submission cancelled.", None, None
        
        elif step == "ask_completion_note":
            data["completion_note"] = message
            session_manager.update_session(user.id, {"step": "ask_file", "data": data})
            return "Would you like to attach a completion file?\n\nType 'yes' to attach, or 'no' to submit without a file.", None, None
        
        elif step == "ask_file":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "wait_for_file", "data": data})
                return "Please upload your completion file now (click the 📎 button).", None, None
            else:
                session_manager.update_session(user.id, {"step": "final_confirm", "data": data})
                return f"Ready to submit '{data['task_title']}'?\n\nType 'yes' to confirm.", None, None
        
        elif step == "wait_for_file":
            if message.lower() in ["skip", "no", "cancel"]:
                session_manager.update_session(user.id, {"step": "final_confirm", "data": data})
                return f"Ready to submit '{data['task_title']}'?\n\nType 'yes' to confirm.", None, None
            elif data.get("file_path"):
                session_manager.update_session(user.id, {"step": "final_confirm", "data": data})
                return f"File received: {data.get('filename')}\n\nReady to submit '{data['task_title']}'?\n\nType 'yes' to confirm.", None, None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to continue without a file.", None, None
        
        elif step == "final_confirm":
            if message.lower() in ["yes", "y", "confirm", "ok"]:
                task = self.db.query(Task).filter(Task.id == data["task_id"]).first()
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                self.db.commit()
                
                completion_note = data.get("completion_note", "")
                
                # Include ORIGINAL filename in notification
                if data.get("file_path") and data.get("filename"):
                    file_note = f"\n\n📎 {data.get('filename')}"
                else:
                    file_note = ""
                
                manager = self.db.query(User).filter(User.id == data["manager_id"]).first()
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["manager_id"],
                    content=(
                        f"✅ Task Completed!\n\n"
                        f"{user.full_name} finished: {task.title}\n\n"
                        f"Completed on: {datetime.now().strftime('%B %d, %Y')}\n\n"
                        f"Note: {completion_note}{file_note}"
                    ),
                    file_path=data.get("file_path")
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                
                file_msg = f"\n📎 File submitted: {data.get('filename')}" if data.get('file_path') else ""
                return (
                    f"🎉 Awesome! Task completed!\n\n"
                    f"✅ {data['task_title']}{file_msg}\n\n"
                    f"Your manager {manager.full_name} has been notified. Great work!",
                    "task_completed",
                    {"task_id": task.id}
                )
            else:
                session_manager.clear_session(user.id)
                return "Task submission cancelled.", None, None
        
        return "Something went wrong.", None, None
    
    def _handle_view_feedback(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """View feedback"""
        session_manager.clear_session(user.id)
        return "Use 'my feedback' to see your feedback again.", None, None
    
    def _handle_ask_question(self, user: User, message: str, session: Dict) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Handle employee questions to manager"""
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "select_manager":
            managers = self.db.query(User).filter(User.role == "manager", User.is_active == True).all()
            manager = next((m for m in managers if message.lower() in m.full_name.lower()), None)
            
            if manager:
                tasks = self.db.query(Task).filter(
                    Task.created_by == manager.id,
                    Task.assigned_to == user.id,
                    Task.status != "deleted"
                ).all()
                
                if tasks:
                    session_manager.update_session(user.id, {
                        "step": "select_task",
                        "data": {**data, "manager_id": manager.id, "manager_name": manager.full_name, "tasks": [t.id for t in tasks]}
                    })
                    response = f"About which task would you like to ask {manager.full_name}?\n\n"
                    for i, task in enumerate(tasks, 1):
                        response += f"{i}. {task.title}\n"
                    response += f"\nOr type 'general' for a general question."
                    return response, None, None
                else:
                    session_manager.update_session(user.id, {
                        "step": "ask_question",
                        "data": {**data, "manager_id": manager.id, "manager_name": manager.full_name, "task_id": None}
                    })
                    return f"What would you like to ask {manager.full_name}?", None, None
            else:
                return f"Couldn't find '{message}'. Please try again.", None, None
        
        elif step == "select_task":
            if "general" in message.lower():
                session_manager.update_session(user.id, {"step": "ask_question", "data": {**data, "task_id": None}})
                return f"What would you like to ask {data['manager_name']}?", None, None
            
            tasks = self.db.query(Task).filter(Task.id.in_(data["tasks"])).all()
            task = None
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
            
            if task:
                session_manager.update_session(user.id, {"step": "ask_question", "data": {**data, "task_id": task.id, "task_title": task.title}})
                return f"What's your question about '{task.title}'?", None, None
            else:
                return "Invalid selection. Please try again.", None, None
        
        elif step == "ask_question":
            session_manager.update_session(user.id, {"step": "ask_file", "data": {**data, "question_text": message}})
            return "Would you like to attach a file?\n\nType 'yes' to attach, or 'no' to send without a file.", None, None
        
        elif step == "ask_file":
            if message.lower() in ["yes", "y"]:
                session_manager.update_session(user.id, {"step": "wait_for_file", "data": data})
                return "Please upload the file now (click the 📎 button).", None, None
            else:
                question_text = data.get("question_text")
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["manager_id"],
                    content=f"❓ Question from {user.full_name}{task_context}:\n\n{question_text}"
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Question sent to {data['manager_name']}!\n\nThey'll respond as soon as possible.", "question_sent", None
        
        elif step == "wait_for_file":
            if message.lower() in ["skip", "no", "cancel"]:
                question_text = data.get("question_text")
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["manager_id"],
                    content=f"❓ Question from {user.full_name}{task_context}:\n\n{question_text}"
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Question sent to {data['manager_name']}!", "question_sent", None
            elif data.get("file_path"):
                question_text = data.get("question_text")
                task_context = f" about '{data.get('task_title')}'" if data.get("task_id") else ""
                
                notification = Message(
                    sender_id=None,
                    receiver_id=data["manager_id"],
                    content=f"❓ Question from {user.full_name}{task_context}:\n\n{question_text}\n\n📎 {data.get('filename')}",
                    file_path=data.get("file_path")
                )
                self.db.add(notification)
                self.db.commit()
                
                session_manager.clear_session(user.id)
                return f"✅ Question with file sent to {data['manager_name']}!", "question_sent", None
            else:
                return "Please upload a file using the 📎 button, or type 'skip' to send without a file.", None, None
        
        return "Something went wrong.", None, None
    
    def _get_manager_help(self) -> str:
        return (
            "👋 Hi! I'm your AI Management Assistant!\n\n"
            "As a Manager, you can:\n\n"
            "📋 Task Management:\n"
            "• 'Give a task' - Assign new work\n"
            "• 'Show tasks' - View all tasks\n"
            "• 'Modify task' - Change task details\n"
            "• 'Delete task' - Remove a task\n"
            "• 'Check progress' - See task statistics\n\n"
            "💬 Team Communication:\n"
            "• 'Send feedback' - Give feedback to employees\n"
            "• 'Notify team' - Send announcements\n\n"
            "What would you like to do?"
        )
    
    def _get_employee_help(self) -> str:
        return (
            "👋 Hi! I'm your AI Assistant!\n\n"
            "As an Employee, you can:\n\n"
            "📋 Your Tasks:\n"
            "• 'My tasks' - View your assignments\n"
            "• 'Complete task' - Mark task as done\n"
            "• 'Next deadline' - Check upcoming deadlines\n\n"
            "💬 Communication:\n"
            "• 'My feedback' - View manager feedback\n"
            "• 'Question' - Ask your manager something\n\n"
            "What can I help you with?"
        )