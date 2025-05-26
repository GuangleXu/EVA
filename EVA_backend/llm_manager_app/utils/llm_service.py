# EVA_backend/llm_manager_app/utils/llm_service.py

from typing import Any, Dict, List, Optional, Union, Tuple, Callable, Type
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_random_exponential
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
import aiohttp
from logs.logs import logger
import asyncio
from pydantic import Field, ConfigDict, BaseModel
from functools import lru_cache
from enum import Enum
import os
import json
from dotenv import load_dotenv

# 定义自己的ProcessingTimeoutError，避免循环导入
class ProcessingTimeoutError(Exception):
    """处理超时异常"""
    def __init__(self, message: str = "处理超时", code: int = 504):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

# 定义默认超时时间（秒）
DEFAULT_TIMEOUT = 30  # 30秒超时


class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class LLMClient:
    def __init__(self, provider: str):
        self.provider = provider
        self.config = settings.LLM_APIS.get(provider, {})
        # 从配置中获取超时设置，如果没有则使用默认值
        self.timeout = self.config.get("TIMEOUT", DEFAULT_TIMEOUT)

    async def _call_api(self, messages: List[dict]) -> dict:
        raise NotImplementedError


class DeepSeekClient(LLMClient):
    def __init__(self):
        super().__init__("deepseek")

    async def _call_api(self, messages: List[dict]) -> dict:
        headers = {
            "Authorization": f"Bearer {self.config.get('API_KEY', '')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.config.get("MODEL", "default-model"),
            "messages": messages,
            "temperature": self.config.get("TEMPERATURE", 0.7),
            "max_tokens": self.config.get("MAX_TOKENS", 1024)
        }

        try:
            # 使用asyncio.wait_for增加超时控制
            async with aiohttp.ClientSession() as session:
                async def make_request():
                    async with session.post(self.config.get("BASE_URL", ""), headers=headers, json=payload) as response:
                        return await self._handle_response(response)
                
                # 添加超时控制
                return await asyncio.wait_for(make_request(), timeout=self.timeout)
        except asyncio.TimeoutError:
            timeout_msg = f"DeepSeek API调用超时 ({self.timeout}秒)"
            logger.error(timeout_msg)
            # 返回超时错误，而不是静默失败
            from memory_service_app.utils.system_notify import send_system_notification_to_frontend
            await send_system_notification_to_frontend(
                message="【系统告警】LLM 服务超时，部分智能对话功能暂时不可用。",
                level="error"
            )
            return {"error": timeout_msg, "timeout": True}
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            from memory_service_app.utils.system_notify import send_system_notification_to_frontend
            await send_system_notification_to_frontend(
                message=f"【系统告警】LLM 服务异常：{str(e)}，请检查网络或API配置。",
                level="error"
            )
            return {"error": f"API请求错误: {str(e)}"}

    async def _handle_response(self, response: aiohttp.ClientResponse) -> dict:
        if response.status != 200:
            error_text = await response.text()
            logger.error(f"DeepSeek API返回错误: {response.status}, {error_text}")
            return {"error": f"API返回错误: {response.status}"}

        try:
            result = await response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return {"content": content}
            else:
                logger.error(f"DeepSeek API返回格式异常: {result}")
                return {"error": "API返回格式异常"}
        except Exception as e:
            logger.error(f"解析DeepSeek API响应失败: {str(e)}")
            return {"error": f"解析API响应失败: {str(e)}"}


class SiliconFlowClient(LLMClient):
    def __init__(self):
        super().__init__("siliconflow")

    async def _call_api(self, messages: List[dict]) -> dict:
        headers = {
            "Authorization": f"Bearer {self.config.get('API_KEY', '')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.config.get("MODEL", "default-model"),
            "messages": messages,
            "temperature": self.config.get("TEMPERATURE", 0.7),
            "max_tokens": self.config.get("MAX_TOKENS", 1024)
        }

        try:
            # 使用asyncio.wait_for增加超时控制
            async with aiohttp.ClientSession() as session:
                async def make_request():
                    async with session.post(self.config.get("BASE_URL", ""), headers=headers, json=payload) as response:
                        return await self._handle_response(response)
                
                # 添加超时控制
                return await asyncio.wait_for(make_request(), timeout=self.timeout)
        except asyncio.TimeoutError:
            timeout_msg = f"SiliconFlow API调用超时 ({self.timeout}秒)"
            logger.error(timeout_msg)
            # 返回超时错误，而不是静默失败
            from memory_service_app.utils.system_notify import send_system_notification_to_frontend
            await send_system_notification_to_frontend(
                message="【系统告警】LLM 服务超时，部分智能对话功能暂时不可用。",
                level="error"
            )
            return {"error": timeout_msg, "timeout": True}
        except Exception as e:
            logger.error(f"SiliconFlow API调用失败: {str(e)}")
            from memory_service_app.utils.system_notify import send_system_notification_to_frontend
            await send_system_notification_to_frontend(
                message=f"【系统告警】LLM 服务异常：{str(e)}，请检查网络或API配置。",
                level="error"
            )
            return {"error": f"API请求错误: {str(e)}"}

    async def _handle_response(self, response: aiohttp.ClientResponse) -> dict:
        if response.status != 200:
            error_text = await response.text()
            logger.error(f"SiliconFlow API返回错误: {response.status}, {error_text}")
            return {"error": f"API返回错误: {response.status}"}

        try:
            result = await response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return {"content": content}
            else:
                logger.error(f"SiliconFlow API返回格式异常: {result}")
                return {"error": "API返回格式异常"}
        except Exception as e:
            logger.error(f"解析SiliconFlow API响应失败: {str(e)}")
            return {"error": f"解析API响应失败: {str(e)}"}


class LLMManager(BaseChatModel):
    model_config = ConfigDict(extra="allow")
    is_initialized: bool = Field(default=False, exclude=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._clients = {}
        self.current_provider = "deepseek"
        self.initialize_sync()

    def initialize_sync(self):
        """同步初始化 LLM 服务"""
        if not self.is_initialized:
            self._clients = {
                "deepseek": DeepSeekClient(),
                "siliconflow": SiliconFlowClient()
            }
            self.is_initialized = True
            logger.info("LLM服务初始化完成 | 提供商: %s", self.current_provider)

    async def initialize(self):
        """异步初始化 LLM 服务（保持兼容性）"""
        if not self.is_initialized:
            await self._async_init_clients()
            self.is_initialized = True
            logger.info("LLM服务初始化完成 | 提供商: %s", self.current_provider)

    async def _async_init_clients(self):
        await asyncio.sleep(0.1)
        self._clients = {
            "deepseek": DeepSeekClient(),
            "siliconflow": SiliconFlowClient()
        }
        self.current_provider = "deepseek"

    def _format_messages(self, messages: List[Message]) -> List[dict]:
        return [msg.to_dict() for msg in messages]

    def _format_langchain_messages(self, messages: List[Message]) -> List[Any]:
        result = []
        for m in messages:
            if m.role == "user":
                result.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                result.append(AIMessage(content=m.content))
            elif m.role == "system":
                result.append(SystemMessage(content=m.content))
        return result

    def _llm_type(self) -> str:
        return "custom_llm"

    def _generate(self, messages: List[Any], stop: Optional[List[str]] = None, **kwargs) -> Any:
        """
        实现同步接口以兼容LangChain
        这是一个同步包装器，内部使用异步环境执行异步操作
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            # 如果已经在异步环境中，使用future来等待结果
            future = asyncio.run_coroutine_threadsafe(self._agenerate(messages, stop, **kwargs), loop)
            try:
                # 添加超时控制到同步调用
                timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
                return future.result(timeout=timeout)
            except asyncio.TimeoutError:
                # 超时处理
                error_msg = f"LLM生成超时 ({timeout}秒)"
                logger.error(error_msg)
                from langchain_core.outputs import ChatGeneration, ChatResult
                gen = ChatGeneration(
                    message=AIMessage(content=f"[超时错误] {error_msg}"),
                    generation_info={"finish_reason": "timeout"}
                )
                return ChatResult(generations=[gen])
        else:
            # 如果不在异步环境中，直接运行协程
            return loop.run_until_complete(self._agenerate(messages, stop, **kwargs))

    async def _agenerate(self, messages: List[Any], stop: Optional[List[str]] = None, **kwargs) -> Any:
        """实现异步生成方法，支持LangChain异步调用"""
        from langchain_core.outputs import ChatGenerationChunk, ChatResult, ChatGeneration
        
        try:
            # 转换LangChain消息为我们自己的消息格式
            converted_messages = []
            for msg in messages:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    role = "user" if msg.type == "human" else "assistant" if msg.type == "ai" else "system"
                    converted_messages.append(Message(role=role, content=msg.content))
            
            # 添加超时控制
            timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
            try:
                # 使用wait_for添加超时控制
                response = await asyncio.wait_for(
                    self.generate(converted_messages), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # 超时处理，返回错误提示而非跳过
                error_msg = f"LLM生成超时 ({timeout}秒)"
                logger.error(error_msg)
                # 创建包含超时提示的响应
                return ChatResult(generations=[
                    ChatGeneration(
                        message=AIMessage(content=f"[超时错误] {error_msg}"),
                        generation_info={"finish_reason": "timeout"}
                    )
                ])
            
            # 将结果转换为LangChain期望的格式
            content = response.get("content", "")
            
            # 检查是否超时
            if response.get("timeout", False):
                return ChatResult(generations=[
                    ChatGeneration(
                        message=AIMessage(content=f"[超时错误] {response.get('error', '调用超时')}"),
                        generation_info={"finish_reason": "timeout"}
                    )
                ])
                
            # 检查是否有错误
            if "error" in response:
                return ChatResult(generations=[
                    ChatGeneration(
                        message=AIMessage(content=f"[生成错误] {response['error']}"),
                        generation_info={"finish_reason": "error"}
                    )
                ])
            
            # 应用stop序列（如果提供）
            if stop:
                for s in stop:
                    if s in content:
                        content = content.split(s, 1)[0]
            
            # 创建LangChain的输出结构
            gen = ChatGeneration(
                message=AIMessage(content=content), 
                generation_info={"finish_reason": "stop"}
            )
            result = ChatResult(generations=[gen])
            return result
            
        except Exception as e:
            logger.error(f"_agenerate 方法出错: {str(e)}")
            # 返回带有错误信息的结果，而不是空结果
            gen = ChatGeneration(
                message=AIMessage(content=f"[生成错误] {str(e)}"), 
                generation_info={"finish_reason": "error"}
            )
            return ChatResult(generations=[gen])

    async def apredict(self, text: str, config: Optional[RunnableConfig] = None) -> str:
        messages = [Message(role="user", content=text)]
        # 获取配置中的超时设置或使用默认值
        timeout = getattr(config, "timeout", DEFAULT_TIMEOUT) if config else DEFAULT_TIMEOUT
        try:
            response = await asyncio.wait_for(self.generate(messages), timeout=timeout)
            # 检查是否超时或错误
            if "error" in response:
                if response.get("timeout", False):
                    return f"[超时错误] {response['error']}"
                return f"[生成错误] {response['error']}"
            return response.get("content", "LLM 生成失败")
        except asyncio.TimeoutError:
            error_msg = f"LLM生成超时 ({timeout}秒)"
            logger.error(error_msg)
            return f"[超时错误] {error_msg}"

    async def apredict_messages(self, messages: List[Message], config: Optional[RunnableConfig] = None) -> str:
        # 获取配置中的超时设置或使用默认值
        timeout = getattr(config, "timeout", DEFAULT_TIMEOUT) if config else DEFAULT_TIMEOUT
        try:
            response = await asyncio.wait_for(self.generate(messages), timeout=timeout)
            # 检查是否超时或错误
            if "error" in response:
                if response.get("timeout", False):
                    return f"[超时错误] {response['error']}"
                return f"[生成错误] {response['error']}"
            return response.get("content", "LLM 生成失败")
        except asyncio.TimeoutError:
            error_msg = f"LLM生成超时 ({timeout}秒)"
            logger.error(error_msg)
            return f"[超时错误] {error_msg}"

    async def agenerate_prompt(self, prompt: ChatPromptTemplate, config: Optional[RunnableConfig] = None) -> Any:
        return await self.apredict(prompt.format())

    async def generate(self, messages: List[Message]) -> Dict[str, Any]:
        """生成回复
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict: 包含生成内容的字典
        """
        if not self.is_initialized:
            await self.initialize()
            
        client = self._clients.get(self.current_provider)
        if not client:
            return {"error": f"未找到提供商: {self.current_provider}"}
            
        formatted_messages = self._format_messages(messages)
        response = await client._call_api(formatted_messages)
        
        if "error" in response:
            logger.error(f"LLM生成失败: {response['error']}")
            # 确保错误信息被返回，而不是静默失败
            return response
            
        return response


# 创建单例实例
llm_service = LLMManager()