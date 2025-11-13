"""
간단한 ML 기반 적재 모델 (PyTorch 없이 scikit-learn 사용)

이 모델은 기존 알고리즘의 행동을 학습하여
적재 위치와 회전을 예측합니다.
"""

import numpy as np
import pickle
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class SimplePackingModel:
    """간단한 ML 기반 적재 예측 모델"""

    def __init__(self):
        """모델 초기화"""
        # Position 예측 (회귀)
        self.position_model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        # Rotation 예측 (분류)
        self.rotation_model = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        # 정규화
        self.state_scaler = StandardScaler()
        self.position_scaler = StandardScaler()

        self.is_trained = False

    def _extract_state_features(self, state: np.ndarray) -> np.ndarray:
        """상태에서 특징 추출"""
        # State는 occupancy grid (3D)
        # 간단한 통계 특징 추출
        features = []

        # 전체 점유율
        features.append(np.mean(state))

        # 각 축의 평균 점유율
        features.append(np.mean(state, axis=(1, 2)).mean())  # X축
        features.append(np.mean(state, axis=(0, 2)).mean())  # Y축
        features.append(np.mean(state, axis=(0, 1)).mean())  # Z축

        # 최대/최소
        features.append(np.max(state))
        features.append(np.min(state))

        # 분산
        features.append(np.std(state))

        # Flatten 일부 (너무 커지지 않도록 샘플링)
        flat = state.flatten()
        if len(flat) > 100:
            # 균등 샘플링
            indices = np.linspace(0, len(flat) - 1, 100, dtype=int)
            features.extend(flat[indices])
        else:
            features.extend(flat)

        return np.array(features, dtype=np.float32)

    def train(self, dataset: Dict):
        """데이터셋으로 모델 학습"""
        print("=== 모델 학습 시작 ===")

        states = dataset['states']
        actions = dataset['actions']
        rewards = dataset['rewards']

        print(f"학습 데이터: {len(states)} transitions")

        # 1. State 특징 추출
        print("1. 특징 추출 중...")
        X_states = []
        y_positions = []
        y_rotations = []

        for i, (state, action) in enumerate(zip(states, actions)):
            if i % 100 == 0:
                print(f"  진행: {i}/{len(states)}", end='\r')

            # 특징 추출
            features = self._extract_state_features(state)
            X_states.append(features)

            # 목표 값 추출
            position = action['position']
            rotation = action['rotation']

            y_positions.append(position)
            y_rotations.append(rotation)

        X_states = np.array(X_states)
        y_positions = np.array(y_positions)
        y_rotations = np.array(y_rotations)

        print(f"\n  특징 shape: {X_states.shape}")
        print(f"  Position shape: {y_positions.shape}")
        print(f"  Rotation shape: {y_rotations.shape}")

        # 2. 데이터 정규화
        print("\n2. 데이터 정규화 중...")
        X_states_scaled = self.state_scaler.fit_transform(X_states)
        y_positions_scaled = self.position_scaler.fit_transform(y_positions)

        # 3. 모델 학습
        print("\n3. Position 모델 학습 중...")
        self.position_model.fit(X_states_scaled, y_positions_scaled)
        pos_score = self.position_model.score(X_states_scaled, y_positions_scaled)
        print(f"  Position 모델 R² score: {pos_score:.4f}")

        print("\n4. Rotation 모델 학습 중...")
        self.rotation_model.fit(X_states_scaled, y_rotations)
        rot_score = self.rotation_model.score(X_states_scaled, y_rotations)
        print(f"  Rotation 모델 accuracy: {rot_score:.4f}")

        self.is_trained = True
        print("\n✓ 모델 학습 완료!")

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, int]:
        """상태에서 최적의 action 예측"""
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다.")

        # 특징 추출
        features = self._extract_state_features(state).reshape(1, -1)

        # 정규화
        features_scaled = self.state_scaler.transform(features)

        # 예측
        position_scaled = self.position_model.predict(features_scaled)
        position = self.position_scaler.inverse_transform(position_scaled)[0]

        rotation = self.rotation_model.predict(features_scaled)[0]

        return position, int(rotation)

    def save(self, filepath: str):
        """모델 저장"""
        model_data = {
            'position_model': self.position_model,
            'rotation_model': self.rotation_model,
            'state_scaler': self.state_scaler,
            'position_scaler': self.position_scaler,
            'is_trained': self.is_trained
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"모델이 {filepath}에 저장되었습니다.")

    @classmethod
    def load(cls, filepath: str) -> 'SimplePackingModel':
        """모델 로드"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        model = cls()
        model.position_model = model_data['position_model']
        model.rotation_model = model_data['rotation_model']
        model.state_scaler = model_data['state_scaler']
        model.position_scaler = model_data['position_scaler']
        model.is_trained = model_data['is_trained']

        print(f"모델이 {filepath}에서 로드되었습니다.")
        return model


if __name__ == '__main__':
    print("=== Simple Packing Model Test ===\n")

    # 테스트용 데이터 로드
    from data_converter import ImitationLearningDataset

    try:
        dataset = ImitationLearningDataset.load('data/training_data.pkl')
        print(f"데이터셋 로드 완료: {len(dataset)} transitions\n")

        # 모델 생성 및 학습
        model = SimplePackingModel()
        model.train({
            'states': dataset.states,
            'actions': dataset.actions,
            'rewards': dataset.rewards
        })

        # 모델 저장
        model.save('models/simple_packing_model.pkl')

        # 테스트 예측
        print("\n=== 예측 테스트 ===")
        test_state = dataset.states[0]
        predicted_position, predicted_rotation = model.predict(test_state)
        print(f"예측된 위치: {predicted_position}")
        print(f"예측된 회전: {predicted_rotation}")

        actual_position = dataset.actions[0]['position']
        actual_rotation = dataset.actions[0]['rotation']
        print(f"\n실제 위치: {actual_position}")
        print(f"실제 회전: {actual_rotation}")

        position_error = np.linalg.norm(predicted_position - actual_position)
        print(f"\n위치 오차: {position_error:.2f}")
        print(f"회전 정확도: {'O' if predicted_rotation == actual_rotation else 'X'}")

    except FileNotFoundError:
        print("학습 데이터가 없습니다. 먼저 generate_training_data.py를 실행하세요.")
