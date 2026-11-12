from typing import Any, Coroutine, Union

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware


class StructlogMiddleware(TaskiqMiddleware):
    def pre_execute(
        self,
        message: TaskiqMessage,
    ) -> "Union[TaskiqMessage, Coroutine[Any, Any, TaskiqMessage]]":
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(taskiq_task_id=message.task_id, taskiq_task_name=message.task_name)

        return message
