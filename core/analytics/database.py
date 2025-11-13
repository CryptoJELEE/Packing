"""
데이터베이스 관리 모듈
SQLite를 사용한 시뮬레이션 및 사용 로그 추적
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from pathlib import Path


class AnalyticsDatabase:
    """분석용 데이터베이스 클래스"""

    def __init__(self, db_path: str = "data/analytics.db"):
        """
        데이터베이스 초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        # 디렉토리 생성
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 시뮬레이션 실행 기록 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pallet_type TEXT,
                pallet_width REAL,
                pallet_height REAL,
                pallet_depth REAL,
                pallet_weight REAL,
                total_items INTEGER,
                fitted_items INTEGER,
                unfitted_items INTEGER,
                packing_efficiency REAL,
                total_volume REAL,
                used_volume REAL,
                processing_time REAL,
                bigger_first INTEGER,
                fix_point INTEGER,
                check_stable INTEGER,
                support_ratio REAL,
                use_advanced_strategy INTEGER,
                try_multiple_strategies INTEGER,
                strategy_used TEXT,
                success INTEGER,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)

        # 파일 업로드 기록 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size INTEGER,
                rows_count INTEGER,
                session_id TEXT,
                ip_address TEXT
            )
        """)

        # 에러 로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                endpoint TEXT,
                request_data TEXT,
                session_id TEXT,
                ip_address TEXT
            )
        """)

        # 관리자 계정 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulations_timestamp
            ON simulations(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulations_session
            ON simulations(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp
            ON error_logs(timestamp)
        """)

        conn.commit()
        conn.close()

    def log_simulation(self, data: Dict[str, Any]) -> int:
        """
        시뮬레이션 실행 로그 저장

        Args:
            data: 시뮬레이션 데이터 딕셔너리

        Returns:
            생성된 레코드 ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO simulations (
                session_id, pallet_type, pallet_width, pallet_height,
                pallet_depth, pallet_weight, total_items, fitted_items,
                unfitted_items, packing_efficiency, total_volume, used_volume,
                processing_time, bigger_first, fix_point, check_stable,
                support_ratio, use_advanced_strategy, try_multiple_strategies,
                strategy_used, success, error_message, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('session_id'),
            data.get('pallet_type'),
            data.get('pallet_width'),
            data.get('pallet_height'),
            data.get('pallet_depth'),
            data.get('pallet_weight'),
            data.get('total_items', 0),
            data.get('fitted_items', 0),
            data.get('unfitted_items', 0),
            data.get('packing_efficiency', 0.0),
            data.get('total_volume', 0.0),
            data.get('used_volume', 0.0),
            data.get('processing_time', 0.0),
            data.get('bigger_first', 1),
            data.get('fix_point', 1),
            data.get('check_stable', 1),
            data.get('support_ratio', 0.75),
            data.get('use_advanced_strategy', 0),
            data.get('try_multiple_strategies', 0),
            data.get('strategy_used'),
            data.get('success', 1),
            data.get('error_message'),
            data.get('ip_address'),
            data.get('user_agent')
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def log_file_upload(self, data: Dict[str, Any]) -> int:
        """
        파일 업로드 로그 저장

        Args:
            data: 파일 업로드 데이터

        Returns:
            생성된 레코드 ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO file_uploads (
                file_type, filename, file_size, rows_count,
                session_id, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('file_type'),
            data.get('filename'),
            data.get('file_size'),
            data.get('rows_count'),
            data.get('session_id'),
            data.get('ip_address')
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def log_error(self, data: Dict[str, Any]) -> int:
        """
        에러 로그 저장

        Args:
            data: 에러 데이터

        Returns:
            생성된 레코드 ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO error_logs (
                error_type, error_message, stack_trace, endpoint,
                request_data, session_id, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('error_type'),
            data.get('error_message'),
            data.get('stack_trace'),
            data.get('endpoint'),
            data.get('request_data'),
            data.get('session_id'),
            data.get('ip_address')
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        통계 데이터 조회

        Args:
            days: 최근 일수

        Returns:
            통계 데이터
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 기본 통계
        cursor.execute("""
            SELECT
                COUNT(*) as total_simulations,
                AVG(packing_efficiency) as avg_efficiency,
                AVG(processing_time) as avg_processing_time,
                SUM(total_items) as total_items_processed,
                SUM(fitted_items) as total_fitted_items,
                SUM(unfitted_items) as total_unfitted_items,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_runs,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_runs
            FROM simulations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))

        stats = dict(cursor.fetchone())

        # 파레트 타입별 통계
        cursor.execute("""
            SELECT
                pallet_type,
                COUNT(*) as count,
                AVG(packing_efficiency) as avg_efficiency
            FROM simulations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
                AND pallet_type IS NOT NULL
            GROUP BY pallet_type
            ORDER BY count DESC
        """, (days,))

        stats['pallet_type_stats'] = [dict(row) for row in cursor.fetchall()]

        # 일별 사용량
        cursor.execute("""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as count,
                AVG(packing_efficiency) as avg_efficiency
            FROM simulations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (days,))

        stats['daily_usage'] = [dict(row) for row in cursor.fetchall()]

        # 시간대별 사용량
        cursor.execute("""
            SELECT
                strftime('%H', timestamp) as hour,
                COUNT(*) as count
            FROM simulations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (days,))

        stats['hourly_usage'] = [dict(row) for row in cursor.fetchall()]

        # 에러 통계
        cursor.execute("""
            SELECT
                error_type,
                COUNT(*) as count
            FROM error_logs
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 10
        """, (days,))

        stats['top_errors'] = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return stats

    def get_recent_simulations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        최근 시뮬레이션 목록 조회

        Args:
            limit: 조회 개수

        Returns:
            시뮬레이션 목록
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM simulations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        simulations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return simulations

    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        최근 에러 목록 조회

        Args:
            limit: 조회 개수

        Returns:
            에러 목록
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM error_logs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        errors = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return errors


# 전역 인스턴스
analytics_db = AnalyticsDatabase()
