"""Unified natural language interaction system for voice and text."""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class InteractionConfig:
    """Configuration for the interaction system."""
    
    # Voice settings
    enable_voice_input: bool = False
    enable_voice_output: bool = False
    stt_model: str = "base"  # Whisper model
    tts_provider: str = "gtts"  # gtts, elevenlabs, streamelements, macos
    tts_voice_id: Optional[str] = None
    
    # Interaction settings
    enable_continuous_listening: bool = False
    wake_word: Optional[str] = None  # e.g., "助手" or "Hey Assistant"
    auto_execute_commands: bool = True  # Auto-execute without confirmation
    conversation_history_length: int = 10
    
    # Paths
    audio_input_device: Optional[str] = None  # Microphone device
    audio_output_device: Optional[str] = None  # Speaker device


@dataclass
class UserInput:
    """Represents user input from voice or text."""
    
    text: str
    source: str = "text"  # "text", "voice", "file"
    confidence: float = 1.0  # STT confidence score
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemResponse:
    """Represents system response to user."""
    
    text: str
    action_taken: Optional[str] = None  # Command that was executed
    success: bool = True
    speech_audio: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class NaturalLanguageInterface:
    """
    Main interface for voice/text interaction with the AI system.
    
    This class provides a robot-like interaction experience where users can:
    1. Speak or type commands in natural language
    2. The system understands intent and executes appropriate commands
    3. Responds with voice and/or text feedback
    
    Example usage:
        >>> interface = NaturalLanguageInterface(config, agent, command_registry)
        >>> # Text mode
        >>> response = interface.process_text("帮我创建一个Python项目")
        >>> # Voice mode
        >>> response = await interface.process_voice_async()
    """
    
    def __init__(
        self,
        config: InteractionConfig,
        agent: Any,  # Agent instance
        command_registry: Any,  # CommandRegistry instance
        llm_adapter: Optional[Any] = None,
    ):
        self.config = config
        self.agent = agent
        self.command_registry = command_registry
        self.llm_adapter = llm_adapter
        
        # Initialize components
        self.stt_engine = None
        self.tts_engine = None
        self.conversation_history: list[dict[str, str]] = []
        
        if config.enable_voice_input:
            self._init_stt()
        if config.enable_voice_output:
            self._init_tts()
        
        logger.info("NaturalLanguageInterface initialized")
    
    def _init_stt(self):
        """Initialize Speech-to-Text engine."""
        try:
            from dual_ring_ai.adapters.whisper import WhisperAdapter
            
            self.stt_engine = WhisperAdapter(
                enabled=True,
                model=self.config.stt_model,
                language="zh"  # Default to Chinese
            )
            logger.info(f"STT engine initialized with model: {self.config.stt_model}")
        except ImportError:
            logger.warning("Whisper not available. Install with: pip install openai-whisper")
            self.stt_engine = None
    
    def _init_tts(self):
        """Initialize Text-to-Speech engine."""
        try:
            from autoai.speech.say import say_text
            from autoai.config import Config
            
            # Get config from agent if available
            app_config = getattr(self.agent, 'config', None)
            if app_config is None:
                # Create minimal config
                app_config = Config()
                app_config.text_to_speech_provider = self.config.tts_provider
                if self.config.tts_voice_id:
                    app_config.elevenlabs_voice_id = self.config.tts_voice_id
            
            self.tts_engine = lambda text: say_text(
                text, 
                app_config, 
                voice_index=0
            )
            logger.info(f"TTS engine initialized: {self.config.tts_provider}")
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            self.tts_engine = None
    
    def process_text(self, text: str) -> SystemResponse:
        """
        Process text input and execute appropriate commands.
        
        Args:
            text: User's text input
            
        Returns:
            SystemResponse with result
        """
        logger.info(f"Processing text input: {text}")
        
        # Add to conversation history
        self._add_to_history("user", text)
        
        try:
            # Step 1: Understand intent using LLM
            intent = self._understand_intent(text)
            
            # Step 2: Map intent to command
            command_name, command_args = self._map_intent_to_command(intent, text)
            
            # Step 3: Execute command
            if command_name:
                result = self._execute_command(command_name, command_args)
                response_text = result.get("response", "命令执行完成")
                action_taken = command_name
            else:
                # No command matched, just get AI response
                response_text = self._generate_conversational_response(text)
                action_taken = None
            
            # Step 4: Generate response
            response = SystemResponse(
                text=response_text,
                action_taken=action_taken,
                success=True
            )
            
            # Step 5: Convert to speech if enabled
            if self.config.enable_voice_output and self.tts_engine:
                self.tts_engine(response_text)
            
            # Add to history
            self._add_to_history("assistant", response_text)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing text: {e}", exc_info=True)
            error_response = SystemResponse(
                text=f"抱歉，处理您的请求时出错：{str(e)}",
                success=False
            )
            return error_response
    
    async def process_voice_async(self, audio_path: Optional[Path] = None) -> SystemResponse:
        """
        Process voice input asynchronously.
        
        Args:
            audio_path: Path to audio file. If None, records from microphone.
            
        Returns:
            SystemResponse with result
        """
        if not self.stt_engine:
            return SystemResponse(
                text="语音识别未启用",
                success=False
            )
        
        try:
            # Step 1: Get audio input
            if audio_path is None:
                audio_path = await self._record_audio_async()
            
            if audio_path is None or not audio_path.exists():
                return SystemResponse(
                    text="未能获取音频输入",
                    success=False
                )
            
            # Step 2: Transcribe speech to text
            transcription = self.stt_engine.transcribe(audio_path)
            
            if transcription.get("status") != "completed":
                return SystemResponse(
                    text=f"语音识别失败：{transcription.get('reason', '未知错误')}",
                    success=False
                )
            
            # Extract text from transcription
            text = self._extract_transcription_text(transcription)
            logger.info(f"Transcribed: {text}")
            
            # Step 3: Process as text
            return self.process_text(text)
            
        except Exception as e:
            logger.error(f"Error processing voice: {e}", exc_info=True)
            return SystemResponse(
                text=f"语音处理失败：{str(e)}",
                success=False
            )
    
    def start_interactive_session(self):
        """
        Start an interactive voice/text session (like talking to a robot).
        
        This creates a continuous loop where the system:
        1. Listens for voice input or reads text input
        2. Processes the input
        3. Responds with voice and text
        4. Repeats
        """
        print("\n" + "="*60)
        print("🤖 助手交互系统已启动")
        print("="*60)
        print("模式: " + ("语音+文字" if self.config.enable_voice_input else "仅文字"))
        print("输入 '退出' 或 'exit' 结束会话")
        print("="*60 + "\n")
        
        try:
            while True:
                # Get user input
                if self.config.enable_voice_input:
                    user_input = self._get_multimodal_input()
                else:
                    user_input = input("👤 您: ")
                
                # Check for exit
                if user_input.lower() in ["退出", "exit", "quit", "bye"]:
                    print("\n👋 再见！")
                    break
                
                if not user_input.strip():
                    continue
                
                # Process input
                print("🤖 助手: 思考中...", end="", flush=True)
                response = self.process_text(user_input)
                print("\r", end="")  # Clear "thinking" message
                
                # Display response
                if response.action_taken:
                    print(f"   [执行: {response.action_taken}]")
                print(f"   {response.text}\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 会话已中断")
        except Exception as e:
            logger.error(f"Session error: {e}", exc_info=True)
            print(f"\n❌ 错误: {e}")
    
    def _understand_intent(self, text: str) -> dict[str, Any]:
        """
        Use LLM to understand user intent from natural language.
        
        Returns dict with:
        - intent_type: category of intent (e.g., "create_file", "search_web", "general_chat")
        - confidence: confidence score
        - entities: extracted entities
        - raw_text: original text
        """
        # If we have an LLM adapter, use it
        if self.llm_adapter:
            try:
                return self.llm_adapter.analyze_intent(text, self.conversation_history)
            except Exception as e:
                logger.warning(f"LLM intent analysis failed: {e}, using fallback")
        
        # Fallback: simple keyword-based intent detection
        return self._simple_intent_detection(text)
    
    def _simple_intent_detection(self, text: str) -> dict[str, Any]:
        """Simple keyword-based intent detection (fallback)."""
        text_lower = text.lower()
        
        # File operations
        if any(kw in text_lower for kw in ["创建文件", "新建文件", "write file", "create file"]):
            return {
                "intent_type": "create_file",
                "confidence": 0.8,
                "entities": {"action": "create"},
                "raw_text": text
            }
        
        # Web search
        if any(kw in text_lower for kw in ["搜索", "查找", "search", "find"]):
            return {
                "intent_type": "web_search",
                "confidence": 0.7,
                "entities": {"action": "search"},
                "raw_text": text
            }
        
        # Code execution
        if any(kw in text_lower for kw in ["运行", "执行代码", "run code", "execute"]):
            return {
                "intent_type": "execute_code",
                "confidence": 0.75,
                "entities": {"action": "execute"},
                "raw_text": text
            }
        
        # General chat
        return {
            "intent_type": "general_chat",
            "confidence": 0.5,
            "entities": {},
            "raw_text": text
        }
    
    def _map_intent_to_command(
        self, 
        intent: dict[str, Any], 
        original_text: str
    ) -> tuple[Optional[str], dict[str, str]]:
        """
        Map understood intent to a specific command.
        
        Returns:
            Tuple of (command_name, command_args)
        """
        intent_type = intent.get("intent_type", "")
        
        # Try to find matching command in registry
        available_commands = self.command_registry.commands
        
        # Simple mapping based on intent type
        intent_to_command_map = {
            "create_file": "write_to_file",
            "read_file": "read_file",
            "web_search": "web_search",
            "execute_code": "execute_python_code",
            "list_files": "list_files",
        }
        
        command_name = intent_to_command_map.get(intent_type)
        
        # Verify command exists
        if command_name and command_name in available_commands:
            # Extract arguments from text (simplified)
            command_args = self._extract_command_args(intent, original_text)
            return command_name, command_args
        
        # No direct mapping found
        return None, {}
    
    def _extract_command_args(
        self, 
        intent: dict[str, Any], 
        text: str
    ) -> dict[str, str]:
        """Extract command arguments from natural language text."""
        # This is a simplified implementation
        # In production, use NLP techniques or LLM for better extraction
        args = {}
        
        # Extract file path if mentioned
        if "文件" in text or "file" in text.lower():
            # Simple heuristic: look for quoted strings or paths
            import re
            matches = re.findall(r'["\']([^"\']+)["\']', text)
            if matches:
                args["filename"] = matches[0]
        
        return args
    
    def _execute_command(
        self, 
        command_name: str, 
        command_args: dict[str, str]
    ) -> dict[str, Any]:
        """Execute a command and return result."""
        try:
            # Call command through registry
            result = self.command_registry.call(command_name, **command_args)
            
            return {
                "success": True,
                "response": str(result) if result else "命令执行成功",
                "result": result
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "response": f"命令执行失败: {str(e)}",
                "error": str(e)
            }
    
    def _generate_conversational_response(self, text: str) -> str:
        """Generate a conversational response when no command matches."""
        # Use agent's LLM capabilities for general conversation
        try:
            # This would ideally use the agent's think method
            # For now, return a simple response
            return f"我理解了：'{text}'。请问您需要我执行什么具体操作吗？"
        except Exception as e:
            return f"抱歉，我无法处理这个请求：{str(e)}"
    
    def _add_to_history(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Trim history if too long
        max_len = self.config.conversation_history_length
        if len(self.conversation_history) > max_len * 2:  # *2 for user+assistant
            self.conversation_history = self.conversation_history[-max_len*2:]
    
    def _extract_transcription_text(self, transcription: dict) -> str:
        """Extract text from Whisper transcription result."""
        # Whisper returns JSON with text field
        stdout = transcription.get("stdout", "")
        if stdout:
            import json
            try:
                result = json.loads(stdout)
                return result.get("text", "")
            except:
                pass
        
        # Fallback: return stdout directly
        return stdout.strip()
    
    async def _record_audio_async(self) -> Optional[Path]:
        """Record audio from microphone asynchronously."""
        # This would use PyAudio or similar library
        # For now, return None to indicate recording not implemented
        logger.warning("Microphone recording not yet implemented")
        return None
    
    def _get_multimodal_input(self) -> str:
        """Get input from either voice or keyboard."""
        print("🎤 请说话（按回车切换到文字输入）: ", end="", flush=True)
        
        # In a real implementation, this would:
        # 1. Start listening for voice
        # 2. Allow pressing Enter to switch to text
        # 3. Detect silence to stop recording
        
        # For now, fall back to text input
        return input()
