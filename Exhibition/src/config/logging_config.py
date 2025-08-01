import logging
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import traceback

def setup_logging():
    """기존 기본 로깅 설정"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 기본 로거 설정
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Discord 라이브러리 로그 레벨 조정
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

class AIResponseLogger:
    """AI 응답 전용 로거 - 기존 로깅 시스템과 완전 분리"""
    
    def __init__(self, log_dir: str = None):
        # 프로젝트 루트 기준으로 로그 디렉토리 설정
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "logs" / "ai_responses"
        else:
            self.log_dir = Path(log_dir)
        
        # 디렉토리 생성 (안전하게)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"AI 로그 디렉토리 생성 실패: {e}")
            # 임시 디렉토리 사용
            self.log_dir = Path.cwd() / "temp_ai_logs"
            self.log_dir.mkdir(exist_ok=True)
        
        # 고유한 로거 이름으로 충돌 방지
        logger_name = f'ai_responses_logger_{id(self)}'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # 핸들러 중복 방지
        if not self.logger.handlers:
            self._setup_handlers()
        
        # 통계 추적
        self._stats = {
            'requests': 0,
            'responses': 0,
            'errors': 0,
            'total_processing_time': 0.0
        }
    
    def _setup_handlers(self):
        """로그 핸들러 설정 - 안전한 버전"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            # 1. 상세 텍스트 로그 파일
            text_log_file = self.log_dir / f"ai_detailed_{today}.log"
            text_handler = logging.FileHandler(text_log_file, encoding='utf-8')
            text_formatter = logging.Formatter(
                '%(asctime)s | AI-LOG | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            text_handler.setFormatter(text_formatter)
            
            # 2. JSON 구조화 로그 파일
            json_log_file = self.log_dir / f"ai_structured_{today}.jsonl"
            self.json_log_file = json_log_file
            
            # 3. 오류 전용 로그 파일
            error_log_file = self.log_dir / f"ai_errors_{today}.log"
            error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
            error_handler.setLevel(logging.ERROR)
            error_formatter = logging.Formatter(
                '%(asctime)s | AI-ERROR | %(message)s | %(exc_info)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            error_handler.setFormatter(error_formatter)
            
            # 4. 콘솔 출력 (개발 환경용)
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(
                    '🤖 %(asctime)s | %(message)s',
                    datefmt='%H:%M:%S'
                )
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)
            
            # 핸들러 추가
            self.logger.addHandler(text_handler)
            self.logger.addHandler(error_handler)
            
            # 상위 로거로 전파 방지 (기존 로깅과 완전 분리)
            self.logger.propagate = False
            
            # 초기화 로그
            self.logger.info(f"AI 로깅 시스템 초기화됨 - 로그 디렉토리: {self.log_dir}")
            
        except Exception as e:
            print(f"AI 로깅 핸들러 설정 실패: {e}")
            # 최소한 콘솔 핸들러라도 설정
            console_handler = logging.StreamHandler()
            self.logger.addHandler(console_handler)
            self.logger.propagate = False
    
    def log_ai_request(self, user_id: int, user_name: str, guild_id: int, 
                      channel_id: int, message: str, model: str = "unknown",
                      additional_data: Optional[Dict] = None):
        """AI 요청 로깅"""
        try:
            self._stats['requests'] += 1
            
            request_data = {
                "log_type": "AI_REQUEST",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"{user_id}_{int(datetime.now().timestamp())}",
                "user": {
                    "id": user_id,
                    "name": user_name
                },
                "context": {
                    "guild_id": guild_id,
                    "channel_id": channel_id
                },
                "message": {
                    "content": message,
                    "length": len(message),
                    "word_count": len(message.split())
                },
                "ai_config": {
                    "model": model
                },
                "additional_data": additional_data or {},
                "stats": dict(self._stats)
            }
            
            # 상세 텍스트 로그
            self.logger.info(
                f"AI 요청 시작 | 사용자: {user_name}({user_id}) | "
                f"길드: {guild_id} | 채널: {channel_id} | "
                f"메시지 길이: {len(message)}자 ({len(message.split())}단어) | "
                f"모델: {model} | 총 요청수: {self._stats['requests']}"
            )
            
            # JSON 구조화 로그
            self._write_json_log(request_data)
            
        except Exception as e:
            self.logger.error(f"AI 요청 로깅 실패: {e}")
    
    def log_ai_response(self, user_id: int, user_name: str, guild_id: int,
                       channel_id: int, request_message: str, response_message: str,
                       model: str, processing_time: float, 
                       token_usage: Optional[Dict] = None,
                       error: Optional[str] = None,
                       additional_metrics: Optional[Dict] = None):
        """AI 응답 로깅"""
        try:
            if error is None:
                self._stats['responses'] += 1
            else:
                self._stats['errors'] += 1
            
            self._stats['total_processing_time'] += processing_time
            
            response_data = {
                "log_type": "AI_RESPONSE",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"{user_id}_{int(datetime.now().timestamp())}",
                "user": {
                    "id": user_id,
                    "name": user_name
                },
                "context": {
                    "guild_id": guild_id,
                    "channel_id": channel_id
                },
                "request": {
                    "message": request_message,
                    "length": len(request_message),
                    "word_count": len(request_message.split())
                },
                "response": {
                    "message": response_message if response_message else "",
                    "length": len(response_message) if response_message else 0,
                    "word_count": len(response_message.split()) if response_message else 0
                },
                "performance": {
                    "model": model,
                    "processing_time_seconds": processing_time,
                    "tokens": token_usage or {},
                    "success": error is None,
                    "error": error
                },
                "metrics": additional_metrics or {},
                "stats": dict(self._stats)
            }
            
            # 성공/실패 상태 결정
            status = "성공" if error is None else f"실패 ({error})"
            log_method = self.logger.info if error is None else self.logger.error
            
            # 상세 텍스트 로그
            log_method(
                f"AI 응답 완료 | 사용자: {user_name}({user_id}) | "
                f"길드: {guild_id} | 채널: {channel_id} | "
                f"처리시간: {processing_time:.3f}초 | 모델: {model} | "
                f"요청: {len(request_message)}자 | "
                f"응답: {len(response_message) if response_message else 0}자 | "
                f"상태: {status} | "
                f"성공률: {(self._stats['responses']/(self._stats['requests']) * 100):.1f}%"
            )
            
            # 토큰 사용량 상세 로깅
            if token_usage:
                self.logger.info(
                    f"토큰 사용량 | 사용자: {user_name} | "
                    f"입력: {token_usage.get('prompt_tokens', 0)} | "
                    f"출력: {token_usage.get('completion_tokens', 0)} | "
                    f"총합: {token_usage.get('total_tokens', 0)} | "
                    f"예상비용: ${token_usage.get('estimated_cost', 0):.6f}"
                )
            
            # JSON 구조화 로그
            self._write_json_log(response_data)
            
        except Exception as e:
            self.logger.error(f"AI 응답 로깅 실패: {e}")
    
    def log_ai_error(self, user_id: int, user_name: str, guild_id: int,
                    channel_id: int, error_message: str, error_type: str,
                    request_message: str = "", model: str = "unknown",
                    stack_trace: Optional[str] = None):
        """AI 에러 로깅"""
        try:
            self._stats['errors'] += 1
            
            error_data = {
                "log_type": "AI_ERROR",
                "timestamp": datetime.now().isoformat(),
                "user": {
                    "id": user_id,
                    "name": user_name
                },
                "context": {
                    "guild_id": guild_id,
                    "channel_id": channel_id
                },
                "request_message": request_message,
                "error": {
                    "message": error_message,
                    "type": error_type,
                    "stack_trace": stack_trace or traceback.format_exc()
                },
                "ai_config": {
                    "model": model
                },
                "stats": dict(self._stats)
            }
            
            # 에러 로그
            self.logger.error(
                f"AI 에러 발생 | 사용자: {user_name}({user_id}) | "
                f"길드: {guild_id} | 채널: {channel_id} | "
                f"에러타입: {error_type} | 모델: {model} | "
                f"에러메시지: {error_message} | "
                f"총 에러수: {self._stats['errors']}"
            )
            
            # JSON 구조화 로그
            self._write_json_log(error_data)
            
        except Exception as e:
            print(f"AI 에러 로깅 실패: {e}")
    
    def log_model_performance(self, model: str, metrics: Dict[str, Any], 
                            timeframe: str = "1hour"):
        """모델 성능 통계 로깅"""
        try:
            performance_data = {
                "log_type": "MODEL_PERFORMANCE",
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "timeframe": timeframe,
                "metrics": metrics,
                "global_stats": dict(self._stats)
            }
            
            # 성능 로그
            self.logger.info(
                f"모델 성능 리포트 | 모델: {model} | 기간: {timeframe} | "
                f"평균응답시간: {metrics.get('avg_response_time', 0):.2f}초 | "
                f"성공률: {metrics.get('success_rate', 0):.1f}% | "
                f"총요청수: {metrics.get('total_requests', 0)}"
            )
            
            # JSON 구조화 로그
            self._write_json_log(performance_data)
            
        except Exception as e:
            self.logger.error(f"성능 로깅 실패: {e}")
    
    def log_user_activity(self, user_id: int, user_name: str, activity_data: Dict):
        """사용자 활동 로깅"""
        try:
            activity_log = {
                "log_type": "USER_ACTIVITY",
                "timestamp": datetime.now().isoformat(),
                "user": {
                    "id": user_id,
                    "name": user_name
                },
                "activity": activity_data
            }
            
            self.logger.info(f"사용자 활동 | {user_name}({user_id}) | {activity_data}")
            self._write_json_log(activity_log)
            
        except Exception as e:
            self.logger.error(f"사용자 활동 로깅 실패: {e}")
    
    def _write_json_log(self, data: Dict[Any, Any]):
        """JSON 로그 안전하게 기록"""
        try:
            json_line = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            with open(self.json_log_file, 'a', encoding='utf-8') as f:
                f.write(json_line + '\n')
                f.flush()  # 즉시 플러시
        except Exception as e:
            # JSON 로깅 실패는 조용히 처리하되 중요한 에러는 기록
            self.logger.error(f"JSON 로그 기록 실패: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        avg_processing_time = (
            self._stats['total_processing_time'] / self._stats['responses'] 
            if self._stats['responses'] > 0 else 0
        )
        
        success_rate = (
            (self._stats['responses'] / self._stats['requests'] * 100) 
            if self._stats['requests'] > 0 else 0
        )
        
        return {
            **self._stats,
            'avg_processing_time': avg_processing_time,
            'success_rate': success_rate
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self._stats = {
            'requests': 0,
            'responses': 0,
            'errors': 0,
            'total_processing_time': 0.0
        }
        self.logger.info("AI 로깅 통계가 초기화되었습니다.")

# 안전한 전역 인스턴스 생성
try:
    ai_logger = AIResponseLogger()
    AI_LOGGING_ENABLED = True
    print("✅ AI 로깅 시스템이 성공적으로 초기화되었습니다.")
except Exception as e:
    print(f"⚠️ AI 로거 초기화 실패: {e}")
    
    # 더미 AI 로거 클래스 (안전장치)
    class DummyAILogger:
        def log_ai_request(self, *args, **kwargs): pass
        def log_ai_response(self, *args, **kwargs): pass
        def log_ai_error(self, *args, **kwargs): pass
        def log_model_performance(self, *args, **kwargs): pass
        def log_user_activity(self, *args, **kwargs): pass
        def get_stats(self): return {}
        def reset_stats(self): pass
    
    ai_logger = DummyAILogger()
    AI_LOGGING_ENABLED = False