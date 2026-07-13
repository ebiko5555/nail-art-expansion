"""Dependency-free structural and numeric validation for the generated GLB."""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path


REQUIRED_BONES = {
    "wristR", "handR",
    "thumb1R", "thumb2R", "thumb3R",
    "index1R", "index2R", "index3R",
    "middle1R", "middle2R", "middle3R",
    "ring1R", "ring2R", "ring3R",
    "pinky1R", "pinky2R", "pinky3R",
}

COMPONENTS = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


def load_glb(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError("GLB header is invalid")
    offset = 12
    document = None
    binary = b""
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binary = chunk
    if document is None:
        raise ValueError("JSON chunk is missing")
    return document, binary


def accessor_values(document: dict, binary: bytes, index: int):
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    fmt, component_size = COMPONENTS[accessor["componentType"]]
    component_count = TYPE_COUNTS[accessor["type"]]
    element_size = component_size * component_count
    stride = view.get("byteStride", element_size)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    unpack = struct.Struct("<" + fmt * component_count).unpack_from
    for item in range(accessor["count"]):
        yield unpack(binary, start + item * stride)


def verify(path: Path) -> dict:
    document, binary = load_glb(path)
    node_names = {node.get("name") for node in document.get("nodes", [])}
    missing = sorted(REQUIRED_BONES - node_names)
    if missing:
        raise ValueError("Missing bones: " + ", ".join(missing))
    skins = document.get("skins", [])
    if len(skins) != 1:
        raise ValueError(f"Expected one skin, found {len(skins)}")
    joint_names = {
        document["nodes"][index].get("name")
        for index in skins[0].get("joints", [])
    }
    missing_skin_bones = sorted(REQUIRED_BONES - joint_names)
    if missing_skin_bones:
        raise ValueError("Required bones are not skin joints: " + ", ".join(missing_skin_bones))
    meshes = document.get("meshes", [])
    if len(meshes) != 1:
        raise ValueError(f"Expected one mesh, found {len(meshes)}")

    checked_numbers = 0
    weight_rows = 0
    bad_weight_rows = 0
    for primitive in meshes[0].get("primitives", []):
        for semantic, accessor_index in primitive.get("attributes", {}).items():
            for values in accessor_values(document, binary, accessor_index):
                checked_numbers += len(values)
                if not all(math.isfinite(float(value)) for value in values):
                    raise ValueError(f"Non-finite value in {semantic}")
                if semantic == "WEIGHTS_0":
                    weight_rows += 1
                    accessor = document["accessors"][accessor_index]
                    if accessor["componentType"] == 5126:
                        total = sum(values)
                    else:
                        maximum = {5121: 255, 5123: 65535}[accessor["componentType"]]
                        total = sum(values) / maximum
                    if abs(total - 1.0) > 0.02:
                        bad_weight_rows += 1
    if bad_weight_rows:
        raise ValueError(f"Unnormalized weight rows: {bad_weight_rows}")
    return {
        "status": "ok",
        "file": str(path),
        "bytes": path.stat().st_size,
        "meshes": len(meshes),
        "skins": len(skins),
        "joints": len(skins[0]["joints"]),
        "required_bones": len(REQUIRED_BONES),
        "checked_numeric_components": checked_numbers,
        "weight_rows": weight_rows,
    }


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "rigged_hand.glb")
    print(json.dumps(verify(target), ensure_ascii=False, indent=2))
