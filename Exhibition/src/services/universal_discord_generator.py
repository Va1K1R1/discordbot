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
                "on_ready": "봇이 준비되었을 때",
                "on_message": "메시지가 전송되었을 때",
                "on_member_join": "멤버가 서버에 참가했을 때",
                "on_member_remove": "멤버가 서버에서 나갔을 때",
                "on_message_delete": "메시지가 삭제되었을 때",
                "on_message_edit": "메시지가 수정되었을 때",
                "on_reaction_add": "반응이 추가되었을 때",
                "on_reaction_remove": "반응이 제거되었을 때",
                "on_voice_state_update": "음성 상태가 변경되었을 때",
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
                            "doc": getattr(method, '__doc__', None) or "메서드"
                        })
                    elif inspect.isdatadescriptor(method):
                        properties.append({
                            "name": name,
                            "doc": getattr(method, '__doc__', None) or "속성"
                        })

            return {
                "class_name": cls.__name__,
                "doc": getattr(cls, '__doc__', None) or "클래스",
                "methods": methods[:10],  # 상위 10개만
                "properties": properties[:5]  # 상위 5개만
            }
        except Exception as e:
            logger.error(f"클래스 분석 실패 {cls}: {e}")
            return {"class_name": str(cls), "methods": [], "properties": []}

    def _categorize_features(self) -> Dict[str, List[str]]:
        """기능별 분류"""
        return {
            "메시지_관련": [
                "메시지 전송", "메시지 수정", "메시지 삭제", "메시지 고정",
                "반응 추가", "반응 제거", "메시지 검색"
            ],
            "사용자_관리": [
                "멤버 정보", "권한 관리", "역할 부여", "역할 제거",
                "닉네임 변경", "멤버 킥", "멤버 밴"
            ],
            "채널_관리": [
                "채널 생성", "채널 삭제", "채널 수정", "권한 설정"
            ],
            "UI_컴포넌트": [
                "버튼", "드롭다운", "모달", "임베드", "폼"
            ],
            "실시간_기능": [
                "이벤트 리스너", "음성 처리", "실시간 알림"
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
        Discord 봇 개발 전문가로서 사용자 요청을 분석하여 필요한 Discord API 기능들을 식별해주세요.
        
        사용 가능한 Discord API 카테고리:
        {json.dumps(self.api_ref.available_features, ensure_ascii=False, indent=2)}
        
        다음 JSON 형태로 분석 결과를 반환해주세요:
        {{
            "primary_features": ["주요 기능1", "주요 기능2"],
            "secondary_features": ["보조 기능1", "보조 기능2"],
            "ui_components": ["필요한 UI 컴포넌트들"],
            "events_needed": ["필요한 이벤트 리스너들"],
            "permissions_required": ["필요한 권한들"],
            "complexity": 1-10,
            "estimated_lines": 예상_코드_라인_수,
            "api_coverage": {{
                "core": 0-100,
                "ui": 0-100,
                "events": 0-100,
                "advanced": 0-100
            }},
            "features_used": ["사용될 Discord 클래스/메서드들"],
            "requirements": ["추가 라이브러리나 설정"]
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
        === Discord API 완전 레퍼런스 ===
        
        요청된 기능 분석:
        {json.dumps(feature_analysis, ensure_ascii=False, indent=2)}
        
        === 사용 가능한 모든 Discord 클래스 ===
        """

        # 핵심 클래스들 추가
        for class_name, class_info in self.api_ref.api_reference["core_classes"].items():
            context += f"\n## {class_name}\n"
            context += f"설명: {class_info['doc']}\n"
            context += "주요 메서드:\n"
            for method in class_info["methods"][:3]:  # 상위 3개만
                context += f"  - {method['name']}: {method['doc']}\n"

        # UI 컴포넌트들 추가
        context += "\n=== UI 컴포넌트들 ===\n"
        for ui_name, ui_info in self.api_ref.api_reference["ui_components"].items():
            context += f"- {ui_name}: {ui_info['doc']}\n"

        # 이벤트들 추가
        context += "\n=== 사용 가능한 이벤트들 ===\n"
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
        당신은 Discord API의 모든 기능을 완벽하게 활용할 수 있는 전문 개발자입니다.
        사용자의 요청에 따라 Discord API의 모든 클래스, 메서드, 이벤트를 자유롭게 조합하여 코드를 생성해주세요.
        
        {discord_context}
        
        코드 생성 가이드라인:
        1. 복잡도 수준: {complexity_level}
        2. 실험적 기능 사용: {use_experimental}
        3. 모든 Discord API 기능을 적극 활용
        4. 에러 처리 및 로깅 포함
        5. 완전한 기능 구현
        
        반드시 실행 가능한 Python 함수 형태로 생성해주세요:
        
        async def generated_function(interaction: discord.Interaction, user_input: str = ""):
            \"\"\"생성된 함수 설명\"\"\"
            try:
                # 여기에 실제 구현 코드
                await interaction.response.send_message("✅ 실행 완료!")
            except Exception as e:
                logger.error(f"오류: {{e}}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ 오류: {{e}}", ephemeral=True)
        """

        try:
            response, _ = await ai_service.generate_response(
                f"사용자 요청: {request}\n\n위의 Discord API 정보를 활용하여 완전한 코드를 생성해주세요.",
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
            Discord 봇 기능을 더욱 발전시킬 수 있는 향상 기능들을 제안해주세요.
            각 제안은 한 줄로 간단하고 구체적이어야 합니다.
            """

            response, _ = await ai_service.generate_response(
                f"원본 요청: {request}",
                system_message=system_prompt
            )
            return response.split('\n')[:5]  # 최대 5개
        except Exception as e:
            logger.error(f"향상 제안 실패: {e}")
            return ["기본 로깅 추가", "에러 처리 강화", "성능 모니터링"]

    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """기본 분석 결과"""
        return {
            "primary_features": ["기본 메시지"],
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
    요청: {request}
    기본 응답 함수입니다.
    """
    try:
        embed = discord.Embed(
            title="✅ AI 생성 커맨드",
            description=f"요청: {request}\\n\\n이 커맨드가 성공적으로 실행되었습니다!",
            color=0x00ff00
        )
        embed.add_field(name="입력값", value=user_input or "없음", inline=True)
        embed.set_footer(text="Universal AI Generator")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"커맨드 실행 오류: {{e}}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ 오류가 발생했습니다: {{e}}", ephemeral=True)
        '''

    def _get_fallback_result(self, request: str) -> Dict[str, Any]:
        """기본 결과"""
        return {
            "generated_code": self._get_fallback_code(request),
            "feature_analysis": self._get_fallback_analysis(),
            "discord_features_used": ["discord.Interaction", "discord.Embed"],
            "complexity_score": 3,
            "enhancement_suggestions": ["기본 기능 확장", "UI 개선", "에러 처리 강화"],
            "api_coverage": {"core": 30, "ui": 10, "events": 0, "advanced": 0},
            "execution_requirements": []
        }


# 전역 유니버설 생성기 인스턴스
universal_generator = UniversalDiscordGenerator()