"""
세션 관리 모듈
"""
from typing import Optional, Dict
from datetime import datetime, timedelta
from core.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """세션 관리 클래스"""

    def __init__(self, use_supabase: bool = False, supabase_client=None):
        """
        세션 매니저 초기화

        Args:
            use_supabase: Supabase 사용 여부
            supabase_client: Supabase 클라이언트 인스턴스
        """
        self.use_supabase = use_supabase
        self.supabase_client = supabase_client
        self.local_sessions: Dict[str, Dict] = {}
        logger.info(f"SessionManager 초기화 - Supabase: {use_supabase}")

    def save(
        self,
        session_id: str,
        session_type: str,
        data: dict,
        expires_days: int = 7
    ) -> bool:
        """
        세션 저장

        Args:
            session_id: 세션 ID
            session_type: 세션 타입 ('csv', 'order' 등)
            data: 세션 데이터
            expires_days: 만료 일수 (기본 7일)

        Returns:
            성공 여부
        """
        if self.use_supabase and self.supabase_client:
            try:
                sessions_table = self.supabase_client.get_table('sessions')
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

                sessions_table.upsert({
                    'session_id': session_id,
                    'session_type': session_type,
                    'data': data,
                    'expires_at': expires_at
                }).execute()

                logger.info(f"Supabase 세션 저장 성공: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Supabase 세션 저장 오류: {e}", exc_info=True)
                logger.warning("인메모리로 저장합니다")

        # 인메모리 저장 (fallback)
        self.local_sessions[session_id] = {
            'type': session_type,
            'expires_at': datetime.now() + timedelta(days=expires_days),
            **data
        }
        logger.debug(f"인메모리 세션 저장: {session_id}")
        return True

    def get(self, session_id: str) -> Optional[Dict]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 (없거나 만료되면 None)
        """
        if self.use_supabase and self.supabase_client:
            try:
                sessions_table = self.supabase_client.get_table('sessions')
                response = sessions_table.select("*").eq('session_id', session_id).execute()

                if response.data and len(response.data) > 0:
                    session = response.data[0]

                    # 만료 확인
                    if self._is_expired(session.get('expires_at')):
                        logger.info(f"세션 만료됨: {session_id}")
                        self.delete(session_id)
                        return None

                    session_data = session.get('data', {})
                    session_data['type'] = session.get('session_type', '')
                    logger.debug(f"Supabase 세션 조회 성공: {session_id}")
                    return session_data
            except Exception as e:
                logger.error(f"Supabase 세션 조회 오류: {e}", exc_info=True)
                logger.warning("인메모리에서 조회합니다")

        # 인메모리에서 조회 (fallback)
        session = self.local_sessions.get(session_id)
        if session:
            # 만료 확인
            if 'expires_at' in session and session['expires_at'] < datetime.now():
                logger.info(f"인메모리 세션 만료됨: {session_id}")
                del self.local_sessions[session_id]
                return None

            logger.debug(f"인메모리 세션 조회 성공: {session_id}")
            return session

        logger.warning(f"세션을 찾을 수 없음: {session_id}")
        return None

    def delete(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        deleted = False

        if self.use_supabase and self.supabase_client:
            try:
                sessions_table = self.supabase_client.get_table('sessions')
                sessions_table.delete().eq('session_id', session_id).execute()
                deleted = True
                logger.info(f"Supabase 세션 삭제: {session_id}")
            except Exception as e:
                logger.error(f"Supabase 세션 삭제 오류: {e}", exc_info=True)

        # 인메모리에서도 삭제
        if session_id in self.local_sessions:
            del self.local_sessions[session_id]
            deleted = True
            logger.debug(f"인메모리 세션 삭제: {session_id}")

        return deleted

    def cleanup_expired(self) -> int:
        """
        만료된 세션 정리

        Returns:
            정리된 세션 수
        """
        count = 0

        # 인메모리 세션 정리
        now = datetime.now()
        expired_keys = [
            key for key, session in self.local_sessions.items()
            if 'expires_at' in session and session['expires_at'] < now
        ]

        for key in expired_keys:
            del self.local_sessions[key]
            count += 1

        if count > 0:
            logger.info(f"만료된 세션 {count}개 정리 완료")

        return count

    @staticmethod
    def _is_expired(expires_at_str: Optional[str]) -> bool:
        """
        만료 여부 확인

        Args:
            expires_at_str: ISO 포맷 만료 시간 문자열

        Returns:
            만료 여부
        """
        if not expires_at_str:
            return False

        try:
            exp_time = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            return exp_time < datetime.now(exp_time.tzinfo)
        except Exception:
            return False
