import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.services.ai_service import AIService


class TestAIService:
    @pytest.fixture
    def ai_service(self):
        return AIService()

    @patch('asyncio.to_thread')
    async def test_generate_response(self, mock_to_thread, ai_service):
        # Mock OpenAI 응답
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "테스트 응답"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_to_thread.return_value = mock_response

        # 테스트 실행
        response, metadata = await ai_service.generate_response("테스트 프롬프트")

        # 검증
        assert response == "테스트 응답"
        assert metadata["tokens_used"] == 100
        assert metadata["finish_reason"] == "stop"
        mock_to_thread.assert_called_once()

    @patch('src.services.ai_service.AIService.generate_response')
    async def test_analyze_intent(self, mock_generate, ai_service):
        # Mock generate_response 메서드
        mock_generate.return_value = (
            '{"intent": "커맨드 생성", "confidence": 0.9, "entities": {"command_name": "test"}}',
            {}
        )

        # 테스트 실행
        result = await ai_service.analyze_intent("새 커맨드 만들어줘")

        # 검증
        assert result["intent"] == "커맨드 생성"
        assert result["confidence"] == 0.9
        assert result["entities"]["command_name"] == "test"
        mock_generate.assert_called_once()

    @patch('src.services.ai_service.AIService.generate_response')
    async def test_generate_command_metadata(self, mock_generate, ai_service):
        # Mock generate_response 메서드
        mock_generate.return_value = (
            '{"name": "test_command", "description": "테스트 커맨드", "response_template": "테스트 응답: {input}"}',
            {}
        )

        # 테스트 실행
        result = await ai_service.generate_command_metadata("테스트 커맨드를 만들어줘")

        # 검증
        assert result["name"] == "test_command"
        assert result["description"] == "테스트 커맨드"
        assert result["response_template"] == "테스트 응답: {input}"
        mock_generate.assert_called_once()

    @patch('src.services.ai_service.AIService.generate_response')
    async def test_enhance_response(self, mock_generate, ai_service):
        # Mock generate_response 메서드
        mock_generate.return_value = ("향상된 테스트 응답", {})

        # 테스트 실행
        result = await ai_service.enhance_response(
            "기본 템플릿: {input}",
            "테스트 입력",
            {"user": "테스트 사용자"}
        )

        # 검증
        assert result == "향상된 테스트 응답"
        mock_generate.assert_called_once()

    @patch('src.services.ai_service.AIService.generate_response')
    async def test_enhance_response_error(self, mock_generate, ai_service):
        # Mock generate_response 메서드가 예외 발생
        mock_generate.side_effect = Exception("테스트 오류")

        # 테스트 실행
        base_template = "기본 템플릿: {input}"
        result = await ai_service.enhance_response(
            base_template,
            "테스트 입력",
            {"user": "테스트 사용자"}
        )

        # 검증 - 오류 발생 시 기본 템플릿 반환
        assert result == base_template
        mock_generate.assert_called_once()
