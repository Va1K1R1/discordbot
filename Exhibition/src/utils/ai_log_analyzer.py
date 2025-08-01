import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class AILogAnalyzer:
    """AI 로그 분석 및 리포팅 시스템"""
    
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "logs" / "ai_responses"
        else:
            self.log_dir = Path(log_dir)
    
    def load_json_logs(self, days: int = 7, log_types: Optional[List[str]] = None) -> List[Dict]:
        """JSON 로그 로드"""
        logs = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = self.log_dir / f"ai_structured_{date.strftime('%Y%m%d')}.jsonl"
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            try:
                                log_entry = json.loads(line.strip())
                                
                                # 로그 타입 필터링
                                if log_types is None or log_entry.get('log_type') in log_types:
                                    logs.append(log_entry)
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"JSON 파싱 실패 {log_file}:{line_num}: {e}")
                except Exception as e:
                    logger.error(f"로그 파일 읽기 실패 {log_file}: {e}")
        
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def get_comprehensive_stats(self, days: int = 7) -> Dict[str, Any]:
        """종합 사용량 통계"""
        logs = self.load_json_logs(days)
        
        # 기본 카운트
        requests = [log for log in logs if log.get('log_type') == 'AI_REQUEST']
        responses = [log for log in logs if log.get('log_type') == 'AI_RESPONSE']
        errors = [log for log in logs if log.get('log_type') == 'AI_ERROR']
        
        successful_responses = [r for r in responses if r.get('performance', {}).get('success', False)]
        
        # 사용자별 통계
        user_stats = defaultdict(lambda: {
            'name': 'Unknown',
            'requests': 0,
            'successful_responses': 0,
            'errors': 0,
            'total_processing_time': 0.0,
            'avg_message_length': 0,
            'total_tokens': 0
        })
        
        for log in logs:
            user_id = log.get('user', {}).get('id')
            user_name = log.get('user', {}).get('name', 'Unknown')
            
            if user_id:
                user_stats[user_id]['name'] = user_name
                
                if log.get('log_type') == 'AI_REQUEST':
                    user_stats[user_id]['requests'] += 1
                    user_stats[user_id]['avg_message_length'] += log.get('message', {}).get('length', 0)
                
                elif log.get('log_type') == 'AI_RESPONSE':
                    if log.get('performance', {}).get('success', False):
                        user_stats[user_id]['successful_responses'] += 1
                        user_stats[user_id]['total_processing_time'] += log.get('performance', {}).get('processing_time_seconds', 0)
                        
                        tokens = log.get('performance', {}).get('tokens', {})
                        user_stats[user_id]['total_tokens'] += tokens.get('total_tokens', 0)
                
                elif log.get('log_type') == 'AI_ERROR':
                    user_stats[user_id]['errors'] += 1
        
        # 사용자별 평균 계산
        for user_id, stats in user_stats.items():
            if stats['requests'] > 0:
                stats['avg_message_length'] = stats['avg_message_length'] / stats['requests']
            if stats['successful_responses'] > 0:
                stats['avg_processing_time'] = stats['total_processing_time'] / stats['successful_responses']
        
        # 모델별 통계
        model_stats = defaultdict(lambda: {
            'requests': 0,
            'successes': 0,
            'errors': 0,
            'total_processing_time': 0.0,
            'total_tokens': 0
        })
        
        for log in responses + errors:
            model = log.get('ai_config', {}).get('model') or log.get('performance', {}).get('model', 'unknown')
            
            if log.get('log_type') == 'AI_RESPONSE':
                model_stats[model]['requests'] += 1
                if log.get('performance', {}).get('success', False):
                    model_stats[model]['successes'] += 1
                    model_stats[model]['total_processing_time'] += log.get('performance', {}).get('processing_time_seconds', 0)
                    
                    tokens = log.get('performance', {}).get('tokens', {})
                    model_stats[model]['total_tokens'] += tokens.get('total_tokens', 0)
            
            elif log.get('log_type') == 'AI_ERROR':
                model_stats[model]['errors'] += 1
        
        # 시간대별 통계
        hourly_stats = defaultdict(int)
        for log in requests:
            try:
                timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                hour = timestamp.hour
                hourly_stats[hour] += 1
            except:
                continue
        
        # 응답 시간 분석
        response_times = [
            r.get('performance', {}).get('processing_time_seconds', 0)
            for r in successful_responses
        ]
        
        return {
            'period_days': days,
            'overview': {
                'total_requests': len(requests),
                'total_responses': len(responses),
                'successful_responses': len(successful_responses),
                'total_errors': len(errors),
                'success_rate': (len(successful_responses) / len(responses) * 100) if responses else 0,
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'median_response_time': sorted(response_times)[len(response_times)//2] if response_times else 0
            },
            'users': {
                'total_unique_users': len(user_stats),
                'top_users': sorted(
                    [(uid, stats) for uid, stats in user_stats.items()],
                    key=lambda x: x[1]['requests'],
                    reverse=True
                )[:10],
                'user_details': dict(user_stats)
            },
            'models': {
                'model_performance': {
                    model: {
                        **stats,
                        'success_rate': (stats['successes'] / stats['requests'] * 100) if stats['requests'] > 0 else 0,
                        'avg_response_time': (stats['total_processing_time'] / stats['successes']) if stats['successes'] > 0 else 0
                    }
                    for model, stats in model_stats.items()
                }
            },
            'temporal': {
                'hourly_distribution': dict(hourly_stats),
                'peak_hour': max(hourly_stats.items(), key=lambda x: x[1])[0] if hourly_stats else 0
            },
            'performance': {
                'response_times': response_times,
                'percentiles': {
                    '50th': sorted(response_times)[len(response_times)//2] if response_times else 0,
                    '90th': sorted(response_times)[int(len(response_times)*0.9)] if response_times else 0,
                    '95th': sorted(response_times)[int(len(response_times)*0.95)] if response_times else 0,
                    '99th': sorted(response_times)[int(len(response_times)*0.99)] if response_times else 0
                }
            }
        }
    
    def generate_report(self, days: int = 7, output_file: Optional[str] = None) -> str:
        """상세 리포트 생성"""
        stats = self.get_comprehensive_stats(days)
        
        report = f"""
# AI 봇 사용량 분석 리포트
**분석 기간**: 최근 {days}일 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 기준)

## 📊 전체 개요
- **총 요청**: {stats['overview']['total_requests']:,}건
- **성공한 응답**: {stats['overview']['successful_responses']:,}건
- **에러**: {stats['overview']['total_errors']:,}건
- **성공률**: {stats['overview']['success_rate']:.1f}%
- **평균 응답시간**: {stats['overview']['avg_response_time']:.2f}초
- **중간값 응답시간**: {stats['overview']['median_response_time']:.2f}초

## 👥 사용자 통계
- **총 사용자 수**: {stats['users']['total_unique_users']:,}명

### 상위 사용자 (요청수 기준)
"""
        
        for i, (user_id, user_stats) in enumerate(stats['users']['top_users'][:5], 1):
            report += f"{i}. **{user_stats['name']}** ({user_id})\n"
            report += f"   - 요청: {user_stats['requests']}건\n"
            report += f"   - 성공: {user_stats['successful_responses']}건\n"
            report += f"   - 에러: {user_stats['errors']}건\n"
            report += f"   - 평균 응답시간: {user_stats.get('avg_processing_time', 0):.2f}초\n\n"
        
        report += f"""
## 🤖 모델 성능
"""
        
        for model, perf in stats['models']['model_performance'].items():
            report += f"### {model}\n"
            report += f"- 요청: {perf['requests']}건\n"
            report += f"- 성공률: {perf['success_rate']:.1f}%\n"
            report += f"- 평균 응답시간: {perf['avg_response_time']:.2f}초\n"
            report += f"- 총 토큰: {perf['total_tokens']:,}\n\n"
        
        report += f"""
## ⏰ 시간대별 분석
- **피크 시간**: {stats['temporal']['peak_hour']}시
- **시간대별 요청 분포**:
"""
        
        for hour in sorted(stats['temporal']['hourly_distribution'].keys()):
            count = stats['temporal']['hourly_distribution'][hour]
            bar = '█' * (count // max(1, max(stats['temporal']['hourly_distribution'].values()) // 20))
            report += f"  {hour:2d}시: {count:3d}건 {bar}\n"
        
        report += f"""
## 📈 성능 분석
- **응답시간 백분위수**:
  - 50th: {stats['performance']['percentiles']['50th']:.2f}초
  - 90th: {stats['performance']['percentiles']['90th']:.2f}초
  - 95th: {stats['performance']['percentiles']['95th']:.2f}초
  - 99th: {stats['performance']['percentiles']['99th']:.2f}초

---
*리포트 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"리포트가 저장되었습니다: {output_file}")
        
        return report
    
    def export_to_csv(self, output_file: str, days: int = 7):
        """CSV로 내보내기"""
        logs = self.load_json_logs(days)
        
        # 플랫 구조로 변환
        flat_logs = []
        for log in logs:
            try:
                flat_log = {
                    'timestamp': log.get('timestamp'),
                    'log_type': log.get('log_type'),
                    'user_id': log.get('user', {}).get('id'),
                    'user_name': log.get('user', {}).get('name'),
                    'guild_id': log.get('context', {}).get('guild_id'),
                    'channel_id': log.get('context', {}).get('channel_id'),
                }
                
                if log.get('log_type') == 'AI_REQUEST':
                    flat_log.update({
                        'message_length': log.get('message', {}).get('length'),
                        'word_count': log.get('message', {}).get('word_count'),
                        'model': log.get('ai_config', {}).get('model')
                    })
                
                elif log.get('log_type') == 'AI_RESPONSE':
                    perf = log.get('performance', {})
                    flat_log.update({
                        'processing_time': perf.get('processing_time_seconds'),
                        'success': perf.get('success'),
                        'model': perf.get('model'),
                        'request_length': log.get('request', {}).get('length'),
                        'response_length': log.get('response', {}).get('length'),
                        'error': perf.get('error'),
                        'prompt_tokens': perf.get('tokens', {}).get('prompt_tokens'),
                        'completion_tokens': perf.get('tokens', {}).get('completion_tokens'),
                        'total_tokens': perf.get('tokens', {}).get('total_tokens')
                    })
                
                elif log.get('log_type') == 'AI_ERROR':
                    flat_log.update({
                        'error_type': log.get('error', {}).get('type'),
                        'error_message': log.get('error', {}).get('message'),
                        'model': log.get('ai_config', {}).get('model')
                    })
                
                flat_logs.append(flat_log)
                
            except Exception as e:
                logger.warning(f"로그 변환 실패: {e}")
                continue
        
        # DataFrame 생성 및 저장
        df = pd.DataFrame(flat_logs)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"CSV 파일이 생성되었습니다: {output_file} ({len(flat_logs)}개 레코드)")
    
    def create_visualizations(self, days: int = 7, output_dir: str = "reports"):
        """시각화 생성"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            stats = self.get_comprehensive_stats(days)
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # 1. 시간대별 사용량
            plt.figure(figsize=(12, 6))
            hourly_data = stats['temporal']['hourly_distribution']
            hours = list(range(24))
            counts = [hourly_data.get(h, 0) for h in hours]
            
            plt.bar(hours, counts)
            plt.title('시간대별 AI 요청 분포')
            plt.xlabel('시간')
            plt.ylabel('요청 수')
            plt.xticks(range(0, 24, 2))
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path / 'hourly_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 2. 응답시간 히스토그램
            if stats['performance']['response_times']:
                plt.figure(figsize=(10, 6))
                plt.hist(stats['performance']['response_times'], bins=30, edgecolor='black')
                plt.title('응답시간 분포')
                plt.xlabel('응답시간 (초)')
                plt.ylabel('빈도')
                plt.axvline(stats['overview']['avg_response_time'], color='red', linestyle='--', label='평균')
                plt.axvline(stats['overview']['median_response_time'], color='orange', linestyle='--', label='중간값')
                plt.legend()
                plt.grid(axis='y', alpha=0.3)
                plt.tight_layout()
                plt.savefig(output_path / 'response_time_distribution.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            print(f"시각화 파일이 생성되었습니다: {output_path}")
            
        except ImportError:
            print("시각화를 위해 matplotlib과 seaborn을 설치해주세요: pip install matplotlib seaborn")
        except Exception as e:
            logger.error(f"시각화 생성 실패: {e}")

# 전역 분석기 인스턴스
log_analyzer = AILogAnalyzer()

# 사용 예제
if __name__ == "__main__":
    # 기본 통계 출력
    analyzer = AILogAnalyzer()
    stats = analyzer.get_comprehensive_stats(7)
    
    print("=== AI 봇 사용량 통계 (최근 7일) ===")
    print(f"총 요청: {stats['overview']['total_requests']}")
    print(f"성공률: {stats['overview']['success_rate']:.1f}%")
    print(f"평균 응답시간: {stats['overview']['avg_response_time']:.2f}초")
    
    # 리포트 생성
    report = analyzer.generate_report(7, "ai_usage_report.md")
    
    # CSV 내보내기
    analyzer.export_to_csv("ai_logs_export.csv", 7)
    
    # 시각화 생성
    analyzer.create_visualizations(7, "ai_reports")