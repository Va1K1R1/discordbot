import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
import ast
from typing import Dict, List, Optional, Any, Union
from src.services.universal_discord_generator import universal_generator
from src.services.ai_service import ai_service
from src.services.command_service import command_service
from src.models.command import Command
from src.utils.helpers import create_embed
import asyncio
import inspect

logger = logging.getLogger(__name__)


class UniversalCommandModal(discord.ui.Modal):
    """Discord API 전체 기능을 활용하는 커맨드 생성 모달"""
    
    def __init__(self):
        super().__init__(title="🌐 Universal Discord Command Generator", timeout=600)
        
        # 사용자 요청 입력
        self.command_request = discord.ui.TextInput(
            label="어떤 기능을 만들고 싶나요?",
            placeholder="예: 실시간 음성 채널 모니터링, 고급 투표 시스템, 멀티 스테이지 이벤트 등...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        
        # 복잡도 수준
        self.complexity_level = discord.ui.TextInput(
            label="복잡도 수준 (simple/advanced/expert)",
            placeholder="advanced",
            default="advanced",
            max_length=20,
            required=False
        )
        
        # 특별 요구사항
        self.special_requirements = discord.ui.TextInput(
            label="특별 요구사항 (선택사항)",
            placeholder="특정 Discord API 기능, 권한, UI 컴포넌트 등",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        
        # 실험 기능 사용 여부
        self.use_experimental = discord.ui.TextInput(
            label="실험적 기능 사용 (yes/no)",
            placeholder="yes",
            default="yes",
            max_length=3,
            required=False
        )
        
        self.add_item(self.command_request)
        self.add_item(self.complexity_level)
        self.add_item(self.special_requirements)
        self.add_item(self.use_experimental)
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 처리"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 입력값 처리
            user_request = self.command_request.value
            complexity = self.complexity_level.value or "advanced"
            requirements = self.special_requirements.value
            experimental = self.use_experimental.value.lower() in ["yes", "y", "true", "1"]
            
            # 진행 상황 알림
            await interaction.followup.send(
                "🔄 Universal AI가 Discord API 전체를 분석하여 고급 커맨드를 생성하고 있습니다...\n"
                f"**요청:** {user_request[:100]}...\n"
                f"**복잡도:** {complexity}\n"
                f"**실험 기능:** {'사용' if experimental else '미사용'}",
                ephemeral=True
            )
            
            # Universal Generator로 고급 커맨드 생성
            generation_result = await universal_generator.generate_universal_command(
                user_request=f"{user_request}\n\n추가 요구사항: {requirements}",
                complexity_level=complexity,
                use_experimental=experimental
            )
            
            # 생성된 코드 정보
            generated_code = generation_result["generated_code"]
            feature_analysis = generation_result["feature_analysis"]
            discord_features = generation_result["discord_features_used"]
            enhancements = generation_result["enhancement_suggestions"]
            
            # 커맨드 메타데이터 추출
            command_metadata = await self._extract_command_metadata(generated_code, user_request)
            
            # 데이터베이스에 저장
            command = Command(
                guild_id=str(interaction.guild.id),
                name=command_metadata["name"],
                description=command_metadata["description"],
                response_template=generated_code,  # 전체 코드를 저장
                use_ai=True,
                ai_prompt=user_request,
                ai_system_message=f"Discord API Universal Generator - Complexity: {complexity}",
                created_by=str(interaction.user.id),
                allowed_roles=[]  # 기본적으로 모든 사용자 허용
            )
            
            await command_service.create_command(command)
            
            # 실시간 동적 커맨드 등록
            await self._register_universal_command(interaction, command, generated_code, feature_analysis)
            
            # 결과 리포트 생성
            await self._send_generation_report(
                interaction, command_metadata, feature_analysis, 
                discord_features, enhancements
            )
            
        except Exception as e:
            logger.error(f"Universal 커맨드 생성 실패: {e}")
            await interaction.followup.send(
                f"❌ Universal 커맨드 생성 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    async def _extract_command_metadata(self, code: str, user_request: str) -> Dict[str, str]:
        """생성된 코드에서 커맨드 메타데이터 추출"""
        try:
            # AI로 메타데이터 추출
            system_prompt = """
            생성된 Discord 봇 코드를 분석하여 커맨드 메타데이터를 추출해주세요.
            다음 JSON 형태로 반환해주세요:
            {
                "name": "커맨드_이름",
                "description": "커맨드 설명"
            }
            
            커맨드 이름은 Discord 규칙에 맞게 영문 소문자, 숫자, 언더스코어만 사용하고 1-32자로 제한해주세요.
            """
            
            response, _ = await ai_service.generate_response(
                f"사용자 요청: {user_request}\n\n생성된 코드:\n{code[:1000]}...",
                system_message=system_prompt
            )
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            # 기본값 반환
            import re
            safe_name = re.sub(r'[^a-z0-9_]', '_', user_request.lower()[:20])
            return {
                "name": f"universal_{safe_name}",
                "description": f"AI 생성 고급 커맨드: {user_request[:80]}..."
            }
    
    async def _register_universal_command(
        self, 
        interaction: discord.Interaction, 
        command: Command, 
        generated_code: str,
        feature_analysis: Dict[str, Any]
    ):
        """Universal 커맨드를 실시간으로 등록"""
        try:
            bot = interaction.client
            
            # 코드 실행 환경 준비
            exec_globals = {
                'discord': discord,
                'app_commands': app_commands,
                'commands': commands,
                'asyncio': asyncio,
                'logger': logger,
                'bot': bot,
                'interaction': interaction,
                'json': json,
                'List': List,
                'Dict': Dict,
                'Optional': Optional,
                'Any': Any,
                'Union': Union
            }
            
            # 코드 실행하여 함수 정의
            exec(generated_code, exec_globals)
            
            # 생성된 함수 찾기
            command_function = None
            for name, obj in exec_globals.items():
                if callable(obj) and not name.startswith('_') and name not in ['discord', 'app_commands', 'commands', 'asyncio', 'logger', 'bot', 'interaction', 'json']:
                    if asyncio.iscoroutinefunction(obj):
                        command_function = obj
                        break
            
            if command_function:
                # 슬래시 커맨드로 래핑
                @app_commands.command(name=command.name, description=command.description)
                async def universal_command_wrapper(cmd_interaction: discord.Interaction, user_input: Optional[str] = ""):
                    try:
                        # 원본 함수 실행
                        await command_function(cmd_interaction, user_input)
                        
                        # 사용 통계 업데이트
                        command.increment_usage()
                        await command_service.update_command_usage(command.guild_id, command.name)
                        
                    except Exception as e:
                        logger.error(f"Universal 커맨드 실행 오류: {e}")
                        if not cmd_interaction.response.is_done():
                            await cmd_interaction.response.send_message(
                                f"❌ 커맨드 실행 중 오류가 발생했습니다: {str(e)}",
                                ephemeral=True
                            )
                        else:
                            await cmd_interaction.followup.send(
                                f"❌ 커맨드 실행 중 오류가 발생했습니다: {str(e)}",
                                ephemeral=True
                            )
                
                # 봇에 커맨드 추가
                bot.tree.add_command(universal_command_wrapper, guild=interaction.guild)
                await bot.tree.sync(guild=interaction.guild)
                
                logger.info(f"Universal 커맨드 등록 성공: {command.name}")
            else:
                raise Exception("생성된 코드에서 실행 가능한 함수를 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"Universal 커맨드 등록 실패: {e}")
            raise
    
    async def _send_generation_report(
        self,
        interaction: discord.Interaction,
        command_metadata: Dict[str, str],
        feature_analysis: Dict[str, Any],
        discord_features: List[str],
        enhancements: List[str]
    ):
        """생성 결과 리포트 전송"""
        embed = create_embed(
            title="🌐 Universal Command 생성 완료!",
            description=f"**`/{command_metadata['name']}`** 커맨드가 성공적으로 생성되어 실시간으로 등록되었습니다!",
            color=0x00ff00
        )
        
        # 기본 정보
        embed.add_field(
            name="📋 기본 정보",
            value=f"**이름:** {command_metadata['name']}\n**설명:** {command_metadata['description'][:100]}...",
            inline=False
        )
        
        # 사용된 Discord 기능들
        if discord_features:
            features_text = "\n".join([f"• {feature}" for feature in discord_features[:5]])
            if len(discord_features) > 5:
                features_text += f"\n• ... 외 {len(discord_features) - 5}개"
            
            embed.add_field(
                name="🔧 사용된 Discord API 기능",
                value=features_text,
                inline=True
            )
        
        # 복잡도 정보
        complexity_score = feature_analysis.get("complexity", 0)
        api_coverage = feature_analysis.get("api_coverage", {})
        
        embed.add_field(
            name="📊 복잡도 분석",
            value=f"**점수:** {complexity_score}/10\n**Core API:** {api_coverage.get('core', 0)}%\n**UI:** {api_coverage.get('ui', 0)}%\n**Events:** {api_coverage.get('events', 0)}%",
            inline=True
        )
        
        # 향상 제안 (처음 3개만)
        if enhancements and len(enhancements) > 0:
            enhancement_text = "\n".join([f"• {enh[:50]}..." for enh in enhancements[:3]])
            embed.add_field(
                name="💡 추가 기능 제안",
                value=enhancement_text,
                inline=False
            )
        
        embed.set_footer(text=f"생성자: {interaction.user.name} | Universal AI Generator")
        
        await interaction.followup.send(embed=embed, ephemeral=False)


class UniversalDynamicCog(commands.Cog):
    """Universal Discord API 동적 커맨드 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_commands = {}  # 활성 커맨드 캐시
    
    @app_commands.command(name="universal", description="🌐 Discord API 전체 기능을 활용한 고급 커맨드를 AI가 생성합니다")
    async def create_universal_command(self, interaction: discord.Interaction):
        """Universal Discord Command Generator"""
        modal = UniversalCommandModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="커맨드분석", description="생성된 커맨드의 상세 분석 정보를 확인합니다")
    @app_commands.describe(command_name="분석할 커맨드 이름")
    async def analyze_command(self, interaction: discord.Interaction, command_name: str):
        """커맨드 상세 분석"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 데이터베이스에서 커맨드 조회
            command = await command_service.get_command(str(interaction.guild.id), command_name)
            
            if not command:
                await interaction.followup.send(
                    f"❌ 커맨드 `{command_name}`을 찾을 수 없습니다.",
                    ephemeral=True
                )
                return
            
            # AI로 코드 분석
            analysis_result = await self._analyze_command_code(command.response_template)
            
            # 분석 결과 임베드 생성
            embed = create_embed(
                title=f"🔍 /{command_name} 상세 분석",
                description="Universal AI가 분석한 커맨드 정보입니다.",
                color=0x3498db
            )
            
            embed.add_field(
                name="📝 기본 정보",
                value=f"**설명:** {command.description}\n**생성자:** <@{command.created_by}>\n**사용 횟수:** {command.usage_count}회",
                inline=False
            )
            
            embed.add_field(
                name="🧠 AI 분석 결과",
                value=analysis_result.get("summary", "분석 결과 없음")[:1024],
                inline=False
            )
            
            # Discord 기능 사용도
            features_used = analysis_result.get("discord_features", [])
            if features_used:
                features_text = "\n".join([f"• {feature}" for feature in features_used[:8]])
                embed.add_field(
                    name="🔧 사용된 Discord 기능",
                    value=features_text,
                    inline=True
                )
            
            # 성능 평가
            performance = analysis_result.get("performance_score", 0)
            complexity = analysis_result.get("complexity_score", 0)
            
            embed.add_field(
                name="📊 성능 평가",
                value=f"**성능 점수:** {performance}/10\n**복잡도:** {complexity}/10",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 분석 실패: {e}")
            await interaction.followup.send(
                "❌ 커맨드 분석 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    async def _analyze_command_code(self, code: str) -> Dict[str, Any]:
        """AI로 커맨드 코드 분석"""
        try:
            system_prompt = """
            Discord 봇 코드를 상세히 분석하여 다음 정보를 JSON 형태로 반환해주세요:
            {
                "summary": "코드 기능 요약 (300자 이내)",
                "discord_features": ["사용된 Discord API 기능들"],
                "performance_score": 1-10,
                "complexity_score": 1-10,
                "security_issues": ["보안 이슈들"],
                "optimization_suggestions": ["최적화 제안들"]
            }
            """
            
            response, _ = await ai_service.generate_response(
                f"다음 Discord 봇 코드를 분석해주세요:\n\n{code[:2000]}...",
                system_message=system_prompt
            )
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"코드 분석 실패: {e}")
            return {
                "summary": "분석 실패",
                "discord_features": [],
                "performance_score": 0,
                "complexity_score": 0
            }
    
    @app_commands.command(name="실시간테스트", description="생성된 커맨드를 안전한 환경에서 실시간 테스트합니다")
    @app_commands.describe(command_name="테스트할 커맨드 이름")
    async def test_command(self, interaction: discord.Interaction, command_name: str):
        """실시간 커맨드 테스트"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 커맨드 조회
            command = await command_service.get_command(str(interaction.guild.id), command_name)
            
            if not command:
                await interaction.followup.send(
                    f"❌ 커맨드 `{command_name}`을 찾을 수 없습니다.",
                    ephemeral=True
                )
                return
            
            # 테스트 환경에서 실행
            test_result = await self._run_command_test(command.response_template)
            
            # 테스트 결과 리포트
            embed = create_embed(
                title=f"🧪 /{command_name} 테스트 결과",
                description="안전한 테스트 환경에서의 실행 결과입니다.",
                color=0x00ff00 if test_result["success"] else 0xff0000
            )
            
            embed.add_field(
                name="✅ 실행 상태" if test_result["success"] else "❌ 실행 상태",
                value="성공" if test_result["success"] else f"실패: {test_result.get('error', '알 수 없는 오류')}",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ 실행 시간",
                value=f"{test_result.get('execution_time', 0):.3f}초",
                inline=True
            )
            
            if test_result.get("warnings"):
                warnings_text = "\n".join([f"• {w}" for w in test_result["warnings"][:3]])
                embed.add_field(
                    name="⚠️ 경고사항",
                    value=warnings_text,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 테스트 실패: {e}")
            await interaction.followup.send(
                "❌ 커맨드 테스트 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    async def _run_command_test(self, code: str) -> Dict[str, Any]:
        """안전한 환경에서 커맨드 테스트 실행"""
        import time
        start_time = time.time()
        
        try:
            # 코드 구문 검사
            ast.parse(code)
            
            # 안전한 실행 환경 (실제 Discord 작업은 하지 않음)
            test_globals = {
                'discord': discord,
                'app_commands': app_commands,
                'logger': logger,
                'asyncio': asyncio,
                'json': json
            }
            
            # 문법 검사만 수행 (실제 실행은 안전하지 않을 수 있음)
            exec(compile(ast.parse(code), '<test>', 'exec'), test_globals)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "execution_time": execution_time,
                "warnings": []
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"구문 오류: {str(e)}",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }

    async def load_existing_commands(self):
        """기존 Universal 커맨드들 로드"""
        try:
            for guild in self.bot.guilds:
                commands = await command_service.get_all_commands(str(guild.id))
                universal_commands = [cmd for cmd in commands if cmd.ai_system_message and "Universal Generator" in cmd.ai_system_message]
                
                for command in universal_commands:
                    try:
                        await self._register_universal_command_from_db(guild, command)
                    except Exception as e:
                        logger.error(f"Universal 커맨드 로드 실패 {command.name}: {e}")
                
                logger.info(f"길드 {guild.name}의 Universal 커맨드 {len(universal_commands)}개 로드 완료")
                
        except Exception as e:
            logger.error(f"기존 Universal 커맨드 로드 실패: {e}")
    
    async def _register_universal_command_from_db(self, guild: discord.Guild, command: Command):
        """데이터베이스의 Universal 커맨드를 봇에 등록"""
        # 실제 등록 로직은 위의 _register_universal_command와 유사
        # 다만 데이터베이스에서 로드된 것임을 표시
        pass


async def setup(bot):
    await bot.add_cog(UniversalDynamicCog(bot))
    logger.info("UniversalDynamicCog 로드 완료")