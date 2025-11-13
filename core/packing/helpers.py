"""
패킹 관련 헬퍼 함수
"""
from typing import Dict, Tuple, List
from py3dbp import Bin, Item


class RotationHelper:
    """아이템 회전 처리 헬퍼"""

    # Rotation type별 position 및 WHD 매핑
    ROTATION_MAPPING = {
        0: {  # RT_WHD
            'position_offset': lambda item: (item.width // 2, item.height // 2, item.depth // 2),
            'dimensions': lambda item: (item.width, item.height, item.depth)
        },
        1: {  # RT_HWD
            'position_offset': lambda item: (item.height // 2, item.width // 2, item.depth // 2),
            'dimensions': lambda item: (item.height, item.width, item.depth)
        },
        2: {  # RT_HDW
            'position_offset': lambda item: (item.height // 2, item.depth // 2, item.width // 2),
            'dimensions': lambda item: (item.height, item.depth, item.width)
        },
        3: {  # RT_DHW
            'position_offset': lambda item: (item.depth // 2, item.height // 2, item.width // 2),
            'dimensions': lambda item: (item.depth, item.height, item.width)
        },
        4: {  # RT_DWH
            'position_offset': lambda item: (item.depth // 2, item.width // 2, item.height // 2),
            'dimensions': lambda item: (item.depth, item.width, item.height)
        },
        5: {  # RT_WDH
            'position_offset': lambda item: (item.width // 2, item.depth // 2, item.height // 2),
            'dimensions': lambda item: (item.width, item.depth, item.height)
        }
    }

    @classmethod
    def get_item_position_and_dimensions(cls, item: Item) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """
        아이템의 회전 타입에 따른 position과 dimensions 계산

        Args:
            item: py3dbp Item 객체

        Returns:
            (position, dimensions) 튜플
        """
        rotation_type = item.rotation_type
        mapping = cls.ROTATION_MAPPING.get(rotation_type)

        if not mapping:
            raise ValueError(f"Invalid rotation type: {rotation_type}")

        # 기본 position에 offset 추가
        offset = mapping['position_offset'](item)
        position = tuple(
            int(item.position[i]) + int(offset[i])
            for i in range(3)
        )

        # Dimensions 계산
        dimensions = tuple(int(d) for d in mapping['dimensions'](item))

        return position, dimensions


class PackingSerializer:
    """패킹 결과 직렬화 헬퍼"""

    @staticmethod
    def serialize_box(box: Bin) -> Dict:
        """
        박스를 딕셔너리로 변환

        Args:
            box: py3dbp Bin 객체

        Returns:
            박스 정보 딕셔너리
        """
        position = (
            int(box.width) // 2,
            int(box.height) // 2,
            int(box.depth) // 2
        )

        return {
            "partNumber": box.partno,
            "position": position,
            "WHD": (int(box.width), int(box.height), int(box.depth)),
            "weight": int(box.max_weight),
            "gravity": box.gravity
        }

    @staticmethod
    def serialize_item(item: Item) -> Dict:
        """
        아이템을 딕셔너리로 변환

        Args:
            item: py3dbp Item 객체

        Returns:
            아이템 정보 딕셔너리
        """
        position, dimensions = RotationHelper.get_item_position_and_dimensions(item)

        return {
            "partNumber": item.partno,
            "name": item.name,
            "type": item.typeof,
            "color": item.color,
            "position": position,
            "rotationType": item.rotation_type,
            "WHD": dimensions,
            "weight": int(item.weight)
        }

    @staticmethod
    def serialize_bin_result(bin_obj: Bin) -> Dict:
        """
        전체 bin 결과를 직렬화

        Args:
            bin_obj: py3dbp Bin 객체

        Returns:
            bin 결과 딕셔너리
        """
        return {
            "box": [PackingSerializer.serialize_box(bin_obj)],
            "fitItem": [PackingSerializer.serialize_item(item) for item in bin_obj.items],
            "unfitItem": [PackingSerializer.serialize_item(item) for item in bin_obj.unfitted_items]
        }


class ColorGenerator:
    """색상 생성 헬퍼"""

    @staticmethod
    def generate_color(seed: int) -> str:
        """
        시드값으로 랜덤 색상 생성

        Args:
            seed: 색상 시드값

        Returns:
            HEX 색상 코드
        """
        import random
        random.seed(seed)
        return "#" + ''.join(random.choice('0123456789ABCDEF') for _ in range(6))
