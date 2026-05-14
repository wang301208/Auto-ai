"""
哨兵代理 (Sentry Agent)

负责监控系统状态，检测问题并发布工单。
"""

import json
import logging
import time
import threading
from datetime import UTC, datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..core.event_bus import EventBus, EventTypes

logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    """日志文件监控处理器"""
    
    def __init__(self, event_bus: EventBus, log_patterns: List[str]):
        self.event_bus = event_bus
        self.log_patterns = log_patterns
        self.last_processed = {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # 检查是否是日志文件
        if not any(pattern in file_path.name for pattern in self.log_patterns):
            return
        
        # 避免重复处理
        if file_path in self.last_processed:
            if time.time() - self.last_processed[file_path] < 1:
                return
        
        self.last_processed[file_path] = time.time()
        
        try:
            self._analyze_log_file(file_path)
        except Exception as e:
            logger.error(f"Failed to analyze log file {file_path}: {e}")
    
    def _analyze_log_file(self, file_path: Path):
        """分析日志文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 分析最近的日志行
            recent_lines = lines[-10:]  # 最近10行
            
            for line in recent_lines:
                if self._is_error_line(line):
                    self._report_error(file_path, line)
                    
        except Exception as e:
            logger.error(f"Failed to read log file {file_path}: {e}")
    
    def _is_error_line(self, line: str) -> bool:
        """检查是否是错误行"""
        error_indicators = [
            "ERROR", "CRITICAL", "FATAL", "Exception", "Traceback",
            "failed", "failure", "timeout", "connection refused"
        ]
        
        line_lower = line.lower()
        return any(indicator.lower() in line_lower for indicator in error_indicators)
    
    def _report_error(self, file_path: Path, error_line: str):
        """报告错误"""
        payload = {
            "issue_type": "log_error",
            "plugin": str(file_path),
            "description": f"Error detected in log file: {file_path.name}",
            "error_log": error_line.strip(),
            "metadata": {
                "file": str(file_path),
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        
        self.event_bus.publish(
            EventTypes.ISSUE_DETECTED,
            payload,
            "sentry_agent"
        )


class SentryAgent:
    """哨兵代理"""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """初始化哨兵代理"""
        self.event_bus = event_bus
        self.config = config
        self.running = False
        self.observer = None
        
        # 监控配置
        self.api_endpoints = config.get("api_endpoints", [])
        self.log_directories = config.get("log_directories", [])
        self.log_patterns = config.get("log_patterns", ["*.log", "*.txt"])
        self.github_repos = config.get("github_repos", [])
        
        # 监控间隔
        self.api_check_interval = config.get("api_check_interval", 60)  # 秒
        self.github_check_interval = config.get("github_check_interval", 3600)  # 秒
        
        # 状态跟踪
        self.last_api_check = {}
        self.last_github_check = {}
        
        logger.info("Sentry agent initialized")
    
    def start(self):
        """启动哨兵代理"""
        if self.running:
            logger.warning("Sentry agent is already running")
            return
        
        self.running = True
        
        # 启动文件监控
        self._start_file_monitoring()
        
        # 启动API监控线程
        self._start_api_monitoring()
        
        # 启动GitHub监控线程
        self._start_github_monitoring()
        
        logger.info("Sentry agent started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "sentry", "timestamp": datetime.now(UTC).isoformat()},
            "sentry_agent"
        )
    
    def stop(self):
        """停止哨兵代理"""
        if not self.running:
            return
        
        self.running = False
        
        # 停止文件监控
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        logger.info("Sentry agent stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "sentry", "timestamp": datetime.now(UTC).isoformat()},
            "sentry_agent"
        )
    
    def _start_file_monitoring(self):
        """启动文件监控"""
        if not self.log_directories:
            logger.info("No log directories configured for monitoring")
            return
        
        self.observer = Observer()
        
        for log_dir in self.log_directories:
            log_path = Path(log_dir)
            if log_path.exists():
                handler = LogFileHandler(self.event_bus, self.log_patterns)
                self.observer.schedule(handler, str(log_path), recursive=True)
                logger.info(f"Monitoring log directory: {log_path}")
            else:
                logger.warning(f"Log directory does not exist: {log_path}")
        
        self.observer.start()
    
    def _start_api_monitoring(self):
        """启动API监控"""
        def api_monitor():
            while self.running:
                try:
                    self._check_api_endpoints()
                    time.sleep(self.api_check_interval)
                except Exception as e:
                    logger.error(f"API monitoring error: {e}")
                    time.sleep(10)  # 短暂等待后重试
        
        thread = threading.Thread(target=api_monitor, daemon=True)
        thread.start()
    
    def _start_github_monitoring(self):
        """启动GitHub监控"""
        def github_monitor():
            while self.running:
                try:
                    self._check_github_repos()
                    time.sleep(self.github_check_interval)
                except Exception as e:
                    logger.error(f"GitHub monitoring error: {e}")
                    time.sleep(60)  # 短暂等待后重试
        
        thread = threading.Thread(target=github_monitor, daemon=True)
        thread.start()
    
    def _check_api_endpoints(self):
        """检查API端点"""
        for endpoint in self.api_endpoints:
            try:
                url = endpoint.get("url")
                timeout = endpoint.get("timeout", 10)
                expected_status = endpoint.get("expected_status", 200)
                
                response = requests.get(url, timeout=timeout)
                
                if response.status_code != expected_status:
                    self._report_api_issue(endpoint, response)
                    
            except requests.exceptions.RequestException as e:
                self._report_api_issue(endpoint, None, str(e))
    
    def _report_api_issue(self, endpoint: Dict[str, Any], response: Optional[requests.Response], error: Optional[str] = None):
        """报告API问题"""
        payload = {
            "issue_type": "api_error",
            "plugin": endpoint.get("name", endpoint.get("url", "unknown")),
            "description": f"API endpoint issue: {endpoint.get('url')}",
            "error_log": error or f"Status code: {response.status_code if response else 'N/A'}",
            "metadata": {
                "url": endpoint.get("url"),
                "expected_status": endpoint.get("expected_status", 200),
                "actual_status": response.status_code if response else None,
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        
        self.event_bus.publish(
            EventTypes.ISSUE_DETECTED,
            payload,
            "sentry_agent"
        )
    
    def _check_github_repos(self):
        """检查GitHub仓库更新"""
        for repo in self.github_repos:
            try:
                owner = repo.get("owner")
                repo_name = repo.get("repo")
                current_version = repo.get("current_version", "unknown")
                
                # 获取最新发布版本
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/releases/latest"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = latest_release.get("tag_name", "unknown")
                    
                    if latest_version != current_version:
                        self._report_github_update(repo, current_version, latest_version)
                        
            except Exception as e:
                logger.error(f"Failed to check GitHub repo {repo.get('repo')}: {e}")
    
    def _report_github_update(self, repo: Dict[str, Any], current_version: str, latest_version: str):
        """报告GitHub更新"""
        payload = {
            "issue_type": "dependency_update",
            "plugin": repo.get("name", repo.get("repo", "unknown")),
            "description": f"New version available for {repo.get('repo')}",
            "error_log": f"Current: {current_version}, Latest: {latest_version}",
            "metadata": {
                "repo": repo.get("repo"),
                "owner": repo.get("owner"),
                "current_version": current_version,
                "latest_version": latest_version,
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        
        self.event_bus.publish(
            EventTypes.ISSUE_DETECTED,
            payload,
            "sentry_agent"
        )
    
    def manual_trigger_check(self, check_type: str, **kwargs):
        """手动触发检查"""
        if check_type == "api":
            self._check_api_endpoints()
        elif check_type == "github":
            self._check_github_repos()
        elif check_type == "logs":
            # 手动检查日志文件
            for log_dir in self.log_directories:
                log_path = Path(log_dir)
                if log_path.exists():
                    for log_file in log_path.rglob("*"):
                        if log_file.is_file() and any(pattern in log_file.name for pattern in self.log_patterns):
                            handler = LogFileHandler(self.event_bus, self.log_patterns)
                            handler._analyze_log_file(log_file)
        else:
            logger.warning(f"Unknown check type: {check_type}")


# 默认配置
DEFAULT_SENTRY_CONFIG = {
    "api_endpoints": [
        {
            "name": "health_check",
            "url": "http://localhost:8000/health",
            "expected_status": 200,
            "timeout": 10
        }
    ],
    "log_directories": [
        "logs",
        "autoai/logs"
    ],
    "log_patterns": ["*.log", "*.txt", "error.log"],
    "github_repos": [
        {
            "name": "autoai",
            "owner": "Significant-Gravitas",
            "repo": "AutoAI",
            "current_version": "0.4.7"
        }
    ],
    "api_check_interval": 60,
    "github_check_interval": 3600
}
