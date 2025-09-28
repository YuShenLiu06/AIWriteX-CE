#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    config_data: Dict[str, Any]


@router.get("/")
async def get_config():
    """获取当前配置"""
    try:
        config = Config.get_instance()

        # 构建配置数据结构，基于现有配置系统
        config_data = {
            "platforms": getattr(config, "platforms", []),
            "api": {
                "api_type": getattr(config, "api_type", ""),
                "providers": getattr(config, "config", {}).get("api", {}),
            },
            "wechat": {"credentials": getattr(config, "wechat_credentials", [])},
            "template": {
                "use_template": getattr(config, "use_template", True),
                "template_category": getattr(config, "template_category", ""),
                "template": getattr(config, "template", ""),
            },
            "dimensional_creative": getattr(config, "dimensional_creative_config", {}),
            "publishing": {
                "auto_publish": getattr(config, "auto_publish", False),
                "article_format": getattr(config, "article_format", "html"),
                "format_publish": getattr(config, "format_publish", True),
            },
        }

        return {"status": "success", "data": config_data}

    except Exception as e:
        log.print_log(f"获取配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def update_config(request: ConfigUpdateRequest):
    """更新配置"""
    try:
        config = Config.get_instance()

        # 更新配置数据
        for key, value in request.config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 保存配置
        if config.save_config():
            return {"status": "success", "message": "配置更新成功"}
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")

    except Exception as e:
        log.print_log(f"更新配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensional_creative")
async def get_dimensional_creative_config():
    """获取维度化创意配置"""
    try:
        config = Config.get_instance()
        dimensional_config = getattr(config, "dimensional_creative_config", {})

        return {"status": "success", "data": dimensional_config}

    except Exception as e:
        log.print_log(f"获取维度化创意配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dimensional_creative")
async def update_dimensional_creative_config(config_data: Dict[str, Any]):
    """更新维度化创意配置"""
    try:
        config = Config.get_instance()

        # 更新维度化创意配置
        current_config = getattr(config, "dimensional_creative_config", {})
        current_config.update(config_data)

        # 保存配置
        if config.save_config():
            return {"status": "success", "message": "维度化创意配置更新成功"}
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")

    except Exception as e:
        log.print_log(f"更新维度化创意配置失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))
