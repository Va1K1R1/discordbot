import discord
from discord.ext import commands
from discord import app_commands
import inspect
import ast
import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Callable
from src.services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)


class DiscordAPIReference:
    """Discord API 전체 레퍼런스 시스템"""

    def __init__(self):
        self.api_reference = self._build_complete_api_reference()
        self.available_features = self._categorize_features()

    def _build_complete_api_reference(self) -> Dict[str, Any]:
        """Discord API 완전 레퍼런스 구축"""

        api_ref = {
            # 핵심 클래스들
            "core_classes": {
                "Bot": self._analyze_class(commands.Bot),
                "Client": self._analyze_class(discord.Client),
                "Guild": self._analyze_class(discord.Guild),
                "User": self._analyze_class(discord.User),
                "Member": self._analyze_class(discord.Member),
                "TextChannel": self._analyze_class(discord.TextChannel),
                "VoiceChannel": self._analyze_class(discord.VoiceChannel),
                "Message": self._analyze_class(discord.Message),
                "Embed": self._analyze_class(discord.Embed),
                "Role": self._analyze_class(discord.Role),
                "Permissions": self._analyze_class(discord.Permissions),
                "Interaction": self._analyze_class(discord.Interaction),
            },

            # UI 컴포넌트들
            "ui_components": {
                "View": self._analyze_class(discord.ui.View),
                "Button": self._analyze_class(discord.ui.Button),
                "Select": self._analyze_class(discord.ui.Select),
                "Modal": self._analyze_class(discord.ui.Modal),
                "TextInput": self._analyze_class(discord.ui.TextInput),
            },

            # 이벤트들
            "events": {
                "on_ready": "When bot is ready",
                "on_message": "When a message is sent",
                "on_member_join": "When member joins the server",
                "on_member_remove": "When member leaves the server",
                "on_message_delete": "When a message is deleted",
                "on_message_edit": "When a message is edited",
                "on_reaction_add": "When a reaction is added",
                "on_reaction_remove": "When a reaction is removed",
                "on_voice_state_update": "When voice state changes",
            },

            # 권한 시스템
            "permissions": [
                "send_messages", "manage_messages", "kick_members", "ban_members",
                "administrator", "manage_channels", "manage_guild", "add_reactions",
                "view_channel", "read_message_history", "mention_everyone", "use_voice_activation"
            ],

            # 색상 시스템
            "colors": ["red", "green", "blue", "yellow", "purple", "orange", "pink"],
        }

        return api_ref

    def _analyze_class(self, cls) -> Dict[str, Any]:
        """클래스 분석"""
        try:
            methods = []
            properties = []

            for name, method in inspect.getmembers(cls):
                if not name.startswith('_'):
                    if inspect.ismethod(method) or inspect.isfunction(method):
                        methods.append({
                            "name": name,
                            "doc": getattr(method, '__doc__', None) or "Method"
                        })
                    elif inspect.isdatadescriptor(method):
                        properties.append({
                            "name": name,
                            "doc": getattr(method, '__doc__', None) or "Property"
                        })

            return {
                "class_name": cls.__name__,
                "doc": getattr(cls, '__doc__', None) or "Class",
                "methods": methods[:10],  # 상위 10개만
                "properties": properties[:5]  # 상위 5개만
            }
        except Exception as e:
            logger.error(f"클래스 분석 실패 {cls}: {e}")
            return {"class_name": str(cls), "methods": [], "properties": []}

    def _categorize_features(self) -> Dict[str, List[str]]:
        """기능별 분류"""
        return {
            "message_related": [
                "Send messages", "Edit messages", "Delete messages", "Pin messages",
                "Add reactions", "Remove reactions", "Search messages"
            ],
            "user_management": [
                "Member info", "Permission management", "Role assignment", "Role removal",
                "Nickname change", "Kick member", "Ban member"
            ],
            "channel_management": [
                "Create channel", "Delete channel", "Edit channel", "Set permissions"
            ],
            "ui_components": [
                "Buttons", "Dropdowns", "Modals", "Embeds", "Forms"
            ],
            "realtime_features": [
                "Event listeners", "Voice processing", "Real-time notifications"
            ]
        }


class UniversalDiscordGenerator:
    """Discord API 모든 기능을 활용하는 유니버설 코드 생성기"""

    def __init__(self):
        self.api_ref = DiscordAPIReference()

    async def generate_universal_command(
            self,
            user_request: str,
            complexity_level: str = "advanced",
            use_experimental: bool = True
    ) -> Dict[str, Any]:
        """모든 Discord 기능을 활용한 유니버설 커맨드 생성"""

        try:
            # 1. 요청 분석
            feature_analysis = await self._analyze_discord_features_needed(user_request)

            # 2. Discord 컨텍스트 구축
            discord_context = self._build_complete_discord_context(feature_analysis)

            # 3. 고급 코드 생성
            generated_code = await self._generate_advanced_discord_code(
                user_request, discord_context, complexity_level, use_experimental
            )

            # 4. 향상 제안
            enhancement_suggestions = await self._suggest_enhancements(user_request, feature_analysis)

            return {
                "generated_code": generated_code,
                "feature_analysis": feature_analysis,
                "discord_features_used": feature_analysis.get("features_used", []),
                "complexity_score": feature_analysis.get("complexity", 0),
                "enhancement_suggestions": enhancement_suggestions,
                "api_coverage": feature_analysis.get("api_coverage", {}),
                "execution_requirements": feature_analysis.get("requirements", [])
            }

        except Exception as e:
            logger.error(f"Universal 커맨드 생성 실패: {e}")
            return self._get_fallback_result(user_request)

    async def _analyze_discord_features_needed(self, request: str) -> Dict[str, Any]:
        """Discord 기능 필요도 분석"""

        system_prompt = f"""
        As a Discord bot development expert, analyze the user request to identify the required Discord API features.
        
        Available Discord API categories:
        {json.dumps(self.api_ref.available_features, ensure_ascii=False, indent=2)}
        
        Return the analysis result in the following JSON format:
        {{
            "primary_features": ["main feature 1", "main feature 2"],
            "secondary_features": ["secondary feature 1", "secondary feature 2"],
            "ui_components": ["required UI components"],
            "events_needed": ["required event listeners"],
            "permissions_required": ["required permissions"],
            "complexity": 1-10,
            "estimated_lines": estimated_code_lines,
            "api_coverage": {{
                "core": 0-100,
                "ui": 0-100,
                "events": 0-100,
                "advanced": 0-100
            }},
            "features_used": ["Discord classes/methods to be used"],
            "requirements": ["additional libraries or configurations"]
        }}
        """

        try:
            response, _ = await ai_service.generate_response(
                request, system_message=system_prompt
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"기능 분석 실패: {e}")
            return self._get_fallback_analysis()

    def _build_complete_discord_context(self, feature_analysis: Dict[str, Any]) -> str:
        """완전한 Discord API 컨텍스트 구축"""

        context = f"""
        === Complete Discord API Reference ===
        
        Requested feature analysis:
        {json.dumps(feature_analysis, ensure_ascii=False, indent=2)}
        
        === Available Discord Classes ===
        """

        # 핵심 클래스들 추가
        for class_name, class_info in self.api_ref.api_reference["core_classes"].items():
            context += f"\n## {class_name}\n"
            context += f"Description: {class_info['doc']}\n"
            context += "Main methods:\n"
            for method in class_info["methods"][:3]:  # 상위 3개만
                context += f"  - {method['name']}: {method['doc']}\n"

        # UI 컴포넌트들 추가
        context += "\n=== UI Components ===\n"
        for ui_name, ui_info in self.api_ref.api_reference["ui_components"].items():
            context += f"- {ui_name}: {ui_info['doc']}\n"

        # 이벤트들 추가
        context += "\n=== Available Events ===\n"
        for event_name, event_desc in self.api_ref.api_reference["events"].items():
            context += f"- {event_name}: {event_desc}\n"

        return context

    async def _generate_advanced_discord_code(
            self,
            request: str,
            discord_context: str,
            complexity_level: str,
            use_experimental: bool
    ) -> str:
        """고급 Discord 코드 생성"""

        system_prompt = f"""
        You are an expert developer who can perfectly utilize all Discord API features.
        Generate code by freely combining all Discord API classes, methods, and events according to the user's request.
        
        {discord_context}
        
        Code generation guidelines:
        1. Complexity level: {complexity_level}
        2. Use experimental features: {use_experimental}
        3. Actively utilize all Discord API features
        4. Include error handling and logging
        5. Complete functional implementation
        
        Generate code in the form of an executable Python function:
        
        async def generated_function(interaction: discord.Interaction, user_input: str = ""):
            \"\"\"Generated function description\"\"\"
            try:
                # Actual implementation code here
                await interaction.response.send_message("✅ Execution completed!")
            except Exception as e:
                logger.error(f"Error: {{e}}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {{e}}", ephemeral=True)
        """

        try:
            response, _ = await ai_service.generate_response(
                f"User request: {request}\n\nPlease generate complete code using the Discord API information above.",
                system_message=system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            return self._get_fallback_code(request)

    async def _suggest_enhancements(
            self,
            request: str,
            feature_analysis: Dict[str, Any]
    ) -> List[str]:
        """향상 기능 제안"""

        try:
            system_prompt = """
            Suggest enhancement features that can further improve Discord bot functionality.
            Each suggestion should be simple and specific in one line.
            """

            response, _ = await ai_service.generate_response(
                f"Original request: {request}",
                system_message=system_prompt
            )
            return response.split('\n')[:5]  # 최대 5개
        except Exception as e:
            logger.error(f"향상 제안 실패: {e}")
            return ["Add basic logging", "Enhance error handling", "Performance monitoring"]

    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """기본 분석 결과"""
        return {
            "primary_features": ["Basic messaging"],
            "secondary_features": [],
            "ui_components": [],
            "events_needed": [],
            "permissions_required": [],
            "complexity": 3,
            "estimated_lines": 50,
            "api_coverage": {"core": 30, "ui": 0, "events": 0, "advanced": 0},
            "features_used": ["discord.Interaction"],
            "requirements": []
        }

    def _get_fallback_code(self, request: str) -> str:
        """기본 코드"""
        return f'''
async def generated_function(interaction: discord.Interaction, user_input: str = ""):
    """
    Request: {request}
    This is a basic response function.
    """
    try:
        embed = discord.Embed(
            title="✅ AI Generated Command",
            description=f"Request: {request}\\n\\nThis command has been executed successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Input", value=user_input or "None", inline=True)
        embed.set_footer(text="Universal AI Generator")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Command execution error: {{e}}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: {{e}}", ephemeral=True)
        '''

    def _get_fallback_result(self, request: str) -> Dict[str, Any]:
        """기본 결과"""
        return {
            "generated_code": self._get_fallback_code(request),
            "feature_analysis": self._get_fallback_analysis(),
            "discord_features_used": ["discord.Interaction", "discord.Embed"],
            "complexity_score": 3,
            "enhancement_suggestions": ["Extend basic features", "Improve UI", "Enhance error handling"],
            "api_coverage": {"core": 30, "ui": 10, "events": 0, "advanced": 0},
            "execution_requirements": []
        }


# 전역 유니버설 생성기 인스턴스
universal_generator = UniversalDiscordGenerator()