-- Supabase 데이터베이스 스키마
-- Supabase 대시보드의 SQL Editor에서 실행하세요

-- 마스터 데이터 테이블
CREATE TABLE IF NOT EXISTS master_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  partno TEXT UNIQUE NOT NULL,
  name TEXT,
  width FLOAT,
  height FLOAT,
  depth FLOAT,
  weight FLOAT,
  packaging TEXT,
  category TEXT,
  original_data JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 세션 테이블
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id TEXT UNIQUE NOT NULL,
  session_type TEXT, -- 'csv' or 'order'
  data JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);

-- 시뮬레이션 결과 테이블
CREATE TABLE IF NOT EXISTS simulation_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id TEXT,
  bin_name TEXT,
  result_data JSONB,
  report_path TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_master_items_partno ON master_items(partno);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_simulation_results_session_id ON simulation_results(session_id);

-- RLS (Row Level Security) 정책 설정 (선택사항)
-- ALTER TABLE master_items ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE simulation_results ENABLE ROW LEVEL SECURITY;

-- 공개 읽기 정책 (필요한 경우)
-- CREATE POLICY "Allow public read access" ON master_items FOR SELECT USING (true);
-- CREATE POLICY "Allow public read access" ON sessions FOR SELECT USING (true);
-- CREATE POLICY "Allow public read access" ON simulation_results FOR SELECT USING (true);

