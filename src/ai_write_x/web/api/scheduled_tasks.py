"""定时任务 REST API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from src.ai_write_x.utils import log
from ..state import get_app_state
from ..auth import verify_auth

router = APIRouter(
    prefix="/api/scheduled-tasks",
    tags=["scheduled-tasks"],
    dependencies=[Depends(verify_auth)]
)


class CreateTaskRequest(BaseModel):
    name: str
    topic: str
    schedule_type: str = "fixed_time"
    time_of_day: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: bool = True
    auto_publish: bool = False
    max_retries: int = 3
    # 生成配置扩展字段
    reference_urls: Optional[str] = None
    reference_ratio: Optional[int] = Field(default=None, ge=0, le=100)
    template_category: Optional[str] = None
    template_name: Optional[str] = None
    platform: Optional[str] = None

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("任务话题不能为空")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("任务名称不能为空")
        return v.strip()


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    topic: Optional[str] = None
    schedule_type: Optional[str] = None
    time_of_day: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    auto_publish: Optional[bool] = None
    max_retries: Optional[int] = None
    # 生成配置扩展字段
    reference_urls: Optional[str] = None
    reference_ratio: Optional[int] = Field(default=None, ge=0, le=100)
    template_category: Optional[str] = None
    template_name: Optional[str] = None
    platform: Optional[str] = None

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("任务话题不能为空")
        return v.strip() if v else v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("任务名称不能为空")
        return v.strip() if v else v


class ToggleRequest(BaseModel):
    enabled: bool


def _get_service(request: Request):
    return get_app_state().scheduled_task_service


def _get_scheduler(request: Request):
    return get_app_state().scheduled_task_scheduler


def _get_executor(request: Request):
    return get_app_state().scheduled_task_executor


@router.get("")
async def list_tasks(request: Request):
    service = _get_service(request)
    tasks = service.list_tasks()
    return {"status": "success", "data": {"tasks": [t.to_dict() for t in tasks]}}


@router.post("")
async def create_task(request: Request, body: CreateTaskRequest):
    service = _get_service(request)
    scheduler = _get_scheduler(request)
    try:
        task = service.create_task(body.model_dump())
        scheduler.register_task(task)
        return {"status": "success", "message": "定时任务创建成功", "data": {"task": task.to_dict()}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runtime/status")
async def runtime_status(request: Request):
    scheduler = _get_scheduler(request)
    status = scheduler.get_runtime_status()
    return {"status": "success", "data": status}


@router.get("/{task_id}")
async def get_task(request: Request, task_id: str):
    service = _get_service(request)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"status": "success", "data": {"task": task.to_dict()}}


@router.put("/{task_id}")
async def update_task(request: Request, task_id: str, body: UpdateTaskRequest):
    service = _get_service(request)
    scheduler = _get_scheduler(request)
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        task = service.update_task(task_id, updates)
        scheduler.refresh_task(task)
        return {"status": "success", "message": "定时任务已更新", "data": {"task": task.to_dict()}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(request: Request, task_id: str):
    service = _get_service(request)
    scheduler = _get_scheduler(request)
    deleted = service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务不存在")
    scheduler.unregister_task(task_id)
    return {"status": "success", "message": "定时任务删除成功"}


@router.post("/{task_id}/toggle")
async def toggle_task(request: Request, task_id: str, body: ToggleRequest):
    service = _get_service(request)
    scheduler = _get_scheduler(request)
    try:
        task = service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if body.enabled != task.enabled:
            task = service.toggle_task(task_id)
        scheduler.register_task(task)
        return {"status": "success", "message": f"任务已{'启用' if task.enabled else '停用'}", "data": {"task": task.to_dict()}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/run-now")
async def run_now(request: Request, task_id: str):
    import threading

    service = _get_service(request)
    executor = _get_executor(request)

    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if executor.is_running:
        raise HTTPException(status_code=409, detail="当前已有任务正在运行，请稍后再试")

    def _run():
        if executor.acquire_execution():
            try:
                executor.execute_task(task)
            finally:
                executor.release_execution()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    log.print_log(f"[定时任务] 立即执行: {task.name} ({task_id})", "info")
    return {"status": "success", "message": f"任务 '{task.name}' 已开始执行"}


@router.get("/{task_id}/records")
async def get_records(request: Request, task_id: str):
    service = _get_service(request)
    records = service.get_records(task_id)
    return {"status": "success", "data": {"records": [r.to_dict() for r in records]}}
