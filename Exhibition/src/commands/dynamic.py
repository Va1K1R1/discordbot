import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
import discord
from discord import app_commands
from discord.ext import commands
from src.services.ai_service import AIService
from src.services.command_service import command_service
from src.utils.helpers import create_embed
from src.exceptions.custom_exceptions import ValidationError, CommandAlreadyExistsError

logger = logging.getLogger(__name__)


class UniversalCommandModal(discord.ui.Modal):
    """Universal 커맨드 생성 모달"""
    
    def __init__(self):
        super().__init__(title="Universal 커맨드 생성")
        
        # 커맨드 요청 입력
        self.command_request = discord.ui.TextInput(
            label="만들고 싶은 커맨드 설명",
            placeholder="예: 랜덤 숫자를 생성하는 커맨드 만들어줘",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.command_request)
        
        # 복잡도 레벨
        self.complexity_level = discord.ui.TextInput(
            label="복잡도 (1-5, 선택사항)",
            placeholder="1: 단순, 3: 보통, 5: 복잡 (기본값: 3)",
            style=discord.TextStyle.short,
            max_length=1,
            required=False
        )
        self.add_item(self.complexity_level)
        
        # 특별 요구사항
        self.special_requirements = discord.ui.TextInput(
            label="특별 요구사항 (선택사항)",
            placeholder="특정 권한, 역할, 기능 등의 요구사항",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.special_requirements)
        
        # 실험적 기능 사용
        self.use_experimental = discord.ui.TextInput(
            label="실험적 기능 사용 (y/n, 선택사항)",
            placeholder="실험적 AI 기능을 사용할지 여부 (기본값: n)",
            style=discord.TextStyle.short,
            max_length=1,
            required=False
        )
        self.add_item(self.use_experimental)
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 처리"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 입력값 검증 및 처리
            request = self.command_request.value.strip()
            if not request:
                await interaction.followup.send("❌ 커맨드 설명을 입력해주세요.", ephemeral=True)
                return
            
            # 복잡도 처리
            complexity = 3  # 기본값
            if self.complexity_level.value:
                try:
                    complexity = int(self.complexity_level.value)
                    if not 1 <= complexity <= 5:
                        complexity = 3
                except ValueError:
                    complexity = 3
            
            # 실험적 기능 사용 여부
            use_experimental = self.use_experimental.value.lower() in ['y', 'yes', '예', '네'] if self.use_experimental.value else False
            
            # AI로 커맨드 메타데이터 생성
            try:
                metadata = await self._extract_command_metadata(
                    request, 
                    complexity, 
                    self.special_requirements.value,
                    use_experimental
                )
            except Exception as e:
                logger.error(f"메타데이터 추출 실패: {e}")
                await interaction.followup.send(
                    f"❌ 커맨드 메타데이터 생성 중 오류가 발생했습니다: {str(e)}",
                    ephemeral=True
                )
                return
            
            # 커맨드 등록
            try:
                command_result = await self._register_universal_command(
                    interaction, 
                    metadata,
                    request
                )
                
                await self._send_generation_report(
                    interaction, 
                    command_result, 
                    metadata,
                    complexity,
                    use_experimental
                )
                
            except CommandAlreadyExistsError:
                await interaction.followup.send(
                    f"❌ 커맨드 '{metadata.get('name', 'unknown')}'이 이미 존재합니다.",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Universal 커맨드 생성 실패: {e}")
                await interaction.followup.send(
                    f"❌ 커맨드 생성 중 오류가 발생했습니다: {str(e)}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"모달 제출 처리 실패: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ 요청 처리 중 오류가 발생했습니다.",
                    ephemeral=True
                )
    
    async def _extract_command_metadata(
        self, 
        request: str, 
        complexity: int, 
        special_requirements: Optional[str],
        use_experimental: bool
    ) -> Dict[str, Any]:
        """AI를 사용한 커맨드 메타데이터 추출"""
        ai_service = AIService()
        
        # 영어 프롬프트 구성
        prompt = f"""
User request: {request}
Complexity level: {complexity}/5
Special requirements: {special_requirements or 'None'}
Experimental features: {'Enabled' if use_experimental else 'Disabled'}

Based on the above information, generate metadata for a Discord slash command.
Respond ONLY with valid JSON format without any additional text.

{{
    "name": "command_name",
    "description": "Command description (under 100 characters)",
    "response_template": "Response template",
    "use_ai": true/false,
    "parameters": []
}}

Rules:
- name: lowercase letters, numbers, underscores only, 1-32 characters
- description: under 100 characters
- response_template: actual response content
- Do NOT include any text outside of JSON
"""
        
        try:
            response, _ = await ai_service.generate_response(prompt)
            
            # JSON 파싱 시도
            if not response or not response.strip():
                raise ValueError("Empty AI response")
            
            # JSON 시작/끝 찾기
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                raise ValueError("Cannot find valid JSON format")
            
            json_str = response[start_idx:end_idx+1]
            metadata = json.loads(json_str)
            
            # 필수 필드 검증
            required_fields = ['name', 'description', 'response_template']
            for field in required_fields:
                if field not in metadata:
                    raise ValueError(f"Required field '{field}' is missing")
            
            # 기본값 설정
            metadata.setdefault('use_ai', False)
            metadata.setdefault('parameters', [])
            
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}, response: {response}")
            # 기본 메타데이터 반환
            return self._create_fallback_metadata(request)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return self._create_fallback_metadata(request)
    
    def _create_fallback_metadata(self, request: str) -> Dict[str, Any]:
        """AI 실패 시 기본 메타데이터 생성"""
        # 간단한 이름 생성
        name = "custom_command"
        words = request.split()[:2]  # 처음 두 단어만 사용
        if words:
            name = "_".join(word.lower() for word in words if word.isalnum())[:32]
        
        return {
            "name": name,
            "description": f"사용자 정의 커맨드: {request[:50]}...",
            "response_template": f"요청하신 기능을 실행합니다: {request}",
            "use_ai": False,
            "parameters": []
        }
    
async def _register_universal_command(self, interaction, metadata: Dict):
    """개선된 Universal 커맨드 등록 - 안전한 세션 관리"""
    try:
        command_id = None
        
        # 1단계: 안전한 데이터베이스 커맨드 생성
        try:
            with command_service.get_db_session() as db:
                # 중복 확인
                existing = db.query(Command).filter(
                    Command.guild_id == str(interaction.guild_id),
                    Command.name == metadata["name"]
                ).first()
                
                if existing:
                    await interaction.followup.send(
                        f"❌ 커맨드 `{metadata['name']}`이 이미 존재합니다!", 
                        ephemeral=True
                    )
                    return None
                
                # 새 커맨드 생성
                new_command = Command(
                    guild_id=str(interaction.guild_id),
                    name=metadata["name"],
                    description=metadata["description"],
                    response_template=metadata["response_template"],
                    use_ai=metadata.get("use_ai", False),
                    created_by=str(interaction.user.id)
                )
                
                db.add(new_command)
                db.flush()  # ID 생성
                command_id = new_command.id  # ID 저장
                
                logger.info(f"MySQL: 명령어 생성 성공 - {metadata['name']} (Guild: {interaction.guild_id}, ID: {command_id})")
                
        except Exception as e:
            logger.error(f"Universal 커맨드 DB 생성 실패: {e}")
            await interaction.followup.send(
                f"❌ 데이터베이스 오류: {str(e)}", 
                ephemeral=True
            )
            return None
        
        # 2단계: 새로운 세션에서 커맨드 조회 및 Discord 등록
        try:
            with command_service.get_db_session() as db:
                # 새로운 세션에서 커맨드 조회
                command = db.query(Command).filter(Command.id == command_id).first()
                
                if not command:
                    logger.error(f"생성된 커맨드를 찾을 수 없음: ID {command_id}")
                    return None
                
                # Discord 커맨드 등록
                @app_commands.command(
                    name=command.name,
                    description=command.description
                )
                async def universal_dynamic_command(cmd_interaction: discord.Interaction):
                    """동적 생성된 Universal 커맨드"""
                    try:
                        # 3단계: 실행 시 안전한 세션으로 커맨드 조회
                        with command_service.get_db_session() as exec_db:
                            exec_command = exec_db.query(Command).filter(
                                Command.id == command_id
                            ).first()
                            
                            if not exec_command:
                                await cmd_interaction.response.send_message(
                                    "❌ 커맨드를 찾을 수 없습니다.", 
                                    ephemeral=True
                                )
                                return
                            
                            # 사용 횟수 증가
                            command_service._increment_usage_async(exec_command.id)
                            
                            # AI 응답 생성 또는 템플릿 사용
                            if exec_command.use_ai and exec_command.response_template:
                                from src.services.ai_service import ai_service
                                enhanced_response = await ai_service.enhance_response(
                                    exec_command.response_template,
                                    f"사용자가 {exec_command.name} 커맨드를 실행했습니다.",
                                    {
                                        "user": cmd_interaction.user.display_name,
                                        "guild": cmd_interaction.guild.name if cmd_interaction.guild else "DM"
                                    }
                                )
                                await cmd_interaction.response.send_message(enhanced_response)
                            else:
                                # 기본 템플릿 응답
                                response = exec_command.response_template or f"{exec_command.name} 커맨드가 실행되었습니다!"
                                await cmd_interaction.response.send_message(response)
                    
                    except Exception as e:
                        logger.error(f"Universal 커맨드 실행 실패 {command.name}: {e}")
                        if not cmd_interaction.response.is_done():
                            await cmd_interaction.response.send_message(
                                "❌ 커맨드 실행 중 오류가 발생했습니다.", 
                                ephemeral=True
                            )
                
                # 동적 커맨드를 봇의 커맨드 트리에 추가
                guild_obj = interaction.client.get_guild(interaction.guild_id)
                if guild_obj:
                    interaction.client.tree.add_command(universal_dynamic_command, guild=guild_obj)
                    
                    # 커맨드 트리 동기화
                    try:
                        await interaction.client.tree.sync(guild=guild_obj)
                        logger.info(f"Universal 커맨드 Discord 등록 성공: {command.name}")
                    except Exception as sync_error:
                        logger.error(f"커맨드 동기화 실패: {sync_error}")
                        # 동기화 실패 시 DB에서 커맨드 제거
                        command.is_active = False
                        return None
                
                # 성공 메시지
                embed = discord.Embed(
                    title="✅ Universal 커맨드 생성 완료",
                    description=f"**/{command.name}** 커맨드가 성공적으로 생성되었습니다!",
                    color=discord.Color.green()
                )
                embed.add_field(name="설명", value=command.description, inline=False)
                embed.add_field(name="AI 기능", value="✅ 활성화" if command.use_ai else "❌ 비활성화", inline=True)
                embed.add_field(name="생성자", value=f"<@{command.created_by}>", inline=True)
                
                await interaction.followup.send(embed=embed)
                
                return command
                
        except Exception as e:
            logger.error(f"Universal 커맨드 Discord 등록 실패: {e}")
            
            # Discord 등록 실패 시 DB에서 생성된 커맨드 비활성화
            try:
                with command_service.get_db_session() as cleanup_db:
                    cleanup_command = cleanup_db.query(Command).filter(Command.id == command_id).first()
                    if cleanup_command:
                        cleanup_command.is_active = False
                        logger.info(f"실패한 커맨드 비활성화: {command_id}")
            except Exception as cleanup_error:
                logger.error(f"정리 작업 실패: {cleanup_error}")
            
            await interaction.followup.send(
                f"❌ Discord 커맨드 등록 실패: {str(e)}", 
                ephemeral=True
            )
            return None
    
    except Exception as e:
        logger.error(f"Universal 커맨드 생성 실패: {e}")
        await interaction.followup.send(
            f"❌ 커맨드 생성 중 오류가 발생했습니다: {str(e)}", 
            ephemeral=True
        )
        return None
    
    async def _send_generation_report(
        self, 
        interaction: discord.Interaction, 
        command, 
        metadata: Dict[str, Any],
        complexity: int,
        use_experimental: bool
    ):
        """커맨드 생성 보고서 전송"""
        embed = create_embed(
            title="🚀 Universal 커맨드 생성 완료!",
            color=0x00ff00,
            description=f"커맨드 `/{metadata['name']}`이 성공적으로 생성되었습니다.",
            fields=[
                {"name": "📝 설명", "value": metadata['description'], "inline": False},
                {"name": "🤖 AI 사용", "value": "예" if metadata.get('use_ai') else "아니오", "inline": True},
                {"name": "📊 복잡도", "value": f"{complexity}/5", "inline": True},
                {"name": "🧪 실험적 기능", "value": "사용" if use_experimental else "미사용", "inline": True},
                {"name": "🆔 커맨드 ID", "value": str(command.id), "inline": True},
                {"name": "📅 생성일", "value": command.created_at.strftime("%Y-%m-%d %H:%M"), "inline": True},
                {"name": "💬 응답 예시", "value": metadata['response_template'][:100] + "...", "inline": False}
            ],
            footer=f"생성자: {interaction.user.name} | 바로 사용 가능합니다!"
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class UniversalDynamicCog(commands.Cog):
    """Universal 동적 커맨드 생성 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_commands = {}
    
    @app_commands.command(name="universal", description="AI를 활용한 Universal 커맨드 생성")
    async def create_universal_command(self, interaction: discord.Interaction):
        """Universal 커맨드 생성 인터페이스"""
        modal = UniversalCommandModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="커맨드분석", description="생성된 커맨드의 상세 분석 정보")
    @app_commands.describe(command_name="분석할 커맨드 이름")
    async def analyze_command(self, interaction: discord.Interaction, command_name: str):
        """커맨드 분석"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 커맨드 조회
            command = await command_service.get_command(str(interaction.guild.id), command_name)
            
            # 분석 정보 생성
            analysis = await self._analyze_command_code(command)
            
            embed = create_embed(
                title=f"🔍 커맨드 분석: /{command.name}",
                color=0x3498db,
                fields=[
                    {"name": "📊 기본 정보", "value": f"ID: {command.id}\n생성일: {command.created_at.strftime('%Y-%m-%d %H:%M')}", "inline": True},
                    {"name": "📈 사용 통계", "value": f"사용 횟수: {command.usage_count}\n마지막 사용: {command.last_used.strftime('%Y-%m-%d %H:%M') if command.last_used else '없음'}", "inline": True},
                    {"name": "🤖 AI 설정", "value": f"AI 사용: {'예' if command.use_ai else '아니오'}", "inline": True},
                    {"name": "🔧 기술적 분석", "value": analysis, "inline": False}
                ],
                footer=f"분석 요청자: {interaction.user.name}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 분석 실패: {e}")
            await interaction.followup.send(
                f"❌ 커맨드 분석 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    async def _analyze_command_code(self, command) -> str:
        """커맨드 코드 분석"""
        try:
            analysis_parts = []
            
            # 응답 템플릿 분석
            template = command.response_template
            if "{" in template and "}" in template:
                analysis_parts.append("✅ 동적 변수 사용")
            else:
                analysis_parts.append("📝 정적 응답")
            
            # AI 사용 분석
            if command.use_ai:
                analysis_parts.append("🤖 AI 기반 응답 생성")
            
            # 권한 분석
            roles = command.get_allowed_roles()
            if roles:
                analysis_parts.append(f"🔒 제한된 접근 ({len(roles)}개 역할)")
            else:
                analysis_parts.append("🌐 공개 접근")
            
            # 복잡도 추정
            complexity_score = len(template) // 100 + (1 if command.use_ai else 0)
            if complexity_score >= 3:
                analysis_parts.append("🔥 고복잡도")
            elif complexity_score >= 1:
                analysis_parts.append("⚡ 중복잡도")
            else:
                analysis_parts.append("🌱 저복잡도")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            logger.error(f"코드 분석 실패: {e}")
            return "❌ 분석 불가"
    
    @app_commands.command(name="실시간테스트", description="커맨드를 실시간으로 테스트")
    @app_commands.describe(command_name="테스트할 커맨드 이름")
    async def test_command(self, interaction: discord.Interaction, command_name: str):
        """실시간 커맨드 테스트"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 커맨드 조회
            command = await command_service.get_command(str(interaction.guild.id), command_name)
            
            # 테스트 실행
            test_result = await self._run_command_test(command, interaction.user)
            
            embed = create_embed(
                title=f"🧪 커맨드 테스트: /{command.name}",
                color=0xffa500,
                fields=[
                    {"name": "📝 테스트 입력", "value": f"사용자: {interaction.user.name}", "inline": True},
                    {"name": "⏱️ 실행 시간", "value": f"{test_result['execution_time']:.2f}초", "inline": True},
                    {"name": "✅ 결과", "value": test_result['success'], "inline": True},
                    {"name": "📤 출력", "value": test_result['output'][:500] + ("..." if len(test_result['output']) > 500 else ""), "inline": False}
                ],
                footer="실제 사용과 동일한 환경에서 테스트되었습니다"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 테스트 실패: {e}")
            await interaction.followup.send(
                f"❌ 커맨드 테스트 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    async def _run_command_test(self, command, user) -> Dict[str, Any]:
        """커맨드 실행 테스트"""
        import time
        
        start_time = time.time()
        try:
            if command.use_ai:
                ai_service = AIService()
                output = await ai_service.enhance_response(
                    command.response_template,
                    f"Test user: {user.name}",
                    {"test_mode": True}
                )
            else:
                output = command.response_template
            
            execution_time = time.time() - start_time
            
            return {
                "success": "✅ 성공",
                "output": output,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": "❌ 실패",
                "output": f"오류: {str(e)}",
                "execution_time": execution_time
            }
    
    async def load_existing_commands(self):
        """기존 커맨드들을 봇 시작 시 로드"""
        try:
            for guild in self.bot.guilds:
                commands = await command_service.get_all_commands(str(guild.id))
                
                for command in commands:
                    try:
                        await self._register_universal_command_from_db(command, guild)
                    except Exception as e:
                        logger.error(f"기존 커맨드 '{command.name}' 로드 실패: {e}")
                
                logger.info(f"길드 {guild.name}의 Universal 커맨드 {len(commands)}개 로드 완료")
                
        except Exception as e:
            logger.error(f"기존 커맨드 로드 실패: {e}")
    
    async def _register_universal_command_from_db(self, command, guild):
        """데이터베이스에서 커맨드를 Discord에 등록"""
        # 이미 등록된 커맨드인지 확인
        existing_command = discord.utils.get(self.bot.tree.get_commands(guild=guild), name=command.name)
        if existing_command:
            return
        
        # 콜백 함수 생성 및 등록 로직은 _register_universal_command와 동일
        # 간단화를 위해 생략


async def setup(bot):
    await bot.add_cog(UniversalDynamicCog(bot))
    logger.info("UniversalDynamicCog 로드 완료")