import copy  # noqa 841
import asyncio  # noqa 841
import shutil  # noqa 841
from collections import deque  # noqa 841
import threading  # noqa 841
import queue  # noqa 841
import os  # noqa 841
import webbrowser  # noqa 841
import ctypes  # noqa 841
import sys  # noqa 841
import PySimpleGUI as sg  # noqa 841
import warnings  # noqa 841
import yaml  # noqa 841
import re  # noqa 841
import random  # noqa 841
from bs4 import BeautifulSoup  # noqa 841
import requests  # noqa 841
import time  # noqa 841
from typing import Optional, List, Dict  # noqa 841
from dataclasses import dataclass  # noqa 841
from enum import Enum  # noqa 841
from datetime import datetime, timedelta  # noqa 841
from io import BytesIO  # noqa 841
from http import HTTPStatus  # noqa 841
from urllib.parse import urlparse, unquote  # noqa 841
from pathlib import PurePosixPath  # noqa 841
from dashscope import ImageSynthesis  # noqa 841
import mimetypes  # noqa 841
import json  # noqa 841
import logging  # noqa 841
from enum import Enum  # noqa 841
import unicodedata  # noqa 841
from urllib.parse import quote  # noqa 841
from dateutil.relativedelta import relativedelta  # noqa 841
import html  # noqa 841
import concurrent.futures  # noqa 841
import markdown  # noqa 841
from PIL import Image  # noqa 841
import tempfile  # noqa 841
import subprocess  # noqa 841

import hashlib  # noqa 841
from peewee import CharField, DoubleField, IntegerField, Model, TextField, Case  # noqa 841
from playhouse.sqlite_ext import SqliteExtDatabase  # noqa 841

from aiforge import AIForgeEngine  # noqa 841
from aiforge.utils.field_mapper import map_result_to_format  # noqa 841

from crewai.tools import BaseTool  # noqa 841
from crewai_tools import SeleniumScrapingTool  # noqa 841
from typing import Type  # noqa 841
from pydantic import BaseModel, Field  # noqa 841
import glob  # noqa 841
from crewai import Agent, Crew, Process, Task  # noqa 841
from crewai.project import CrewBase, agent, crew, task  # noqa 841

import importlib.util  # noqa 841
from pathlib import Path  # noqa 841
import tomlkit  # noqa 841

from rich.console import Console  # noqa 841


import src.ai_write_x.gui.MainGUI as MainGUI  # noqa 402

import platform


def is_admin():
    """检查是否具有管理员权限（跨平台）"""
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin()
        elif platform.system() == "Darwin":  # macOS
            # macOS 通常不需要管理员权限来运行GUI应用
            return True
        elif platform.system() == "Linux":
            # Linux 检查是否为 root 用户
            return os.getuid() == 0
        else:
            # 其他系统默认返回 True
            return True
    except Exception as e:  # noqa841
        return False


def run():
    MainGUI.gui_start()


def admin_run():
    """以管理员权限运行（跨平台）"""
    if platform.system() == "Windows":
        if is_admin():
            run()
        else:
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, __file__, None, 0
                )
            except Exception:
                # 如果权限提升失败，直接运行
                run()
    else:
        # macOS 和 Linux 直接运行，不需要权限提升
        run()


if __name__ == "__main__":

    if len(sys.argv) > 1:  # 第一个是文件名，如果多于1个，说明其他模式启动
        if sys.argv[1] == "-d":
            run()
        else:
            admin_run()
    else:
        admin_run()
