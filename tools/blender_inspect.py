"""Blender 4.5+ headless model inventory for hand-rigging work."""

from __future__ import annotations

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector


def args_after_separator() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def vec(value) -> list[float]:
    return [round(float(v), 6) for v in value]


def mesh_topology(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
        non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
        loose_vertices = sum(1 for vertex in bm.verts if not vertex.link_edges)
    finally:
        bm.free()
    return {
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "loose_vertices": loose_vertices,
    }


def mesh_info(obj: bpy.types.Object) -> dict:
    data = obj.data
    world_bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = [min(point[i] for point in world_bounds) for i in range(3)]
    maxs = [max(point[i] for point in world_bounds) for i in range(3)]
    armature_modifiers = [
        {
            "name": modifier.name,
            "object": modifier.object.name if modifier.object else None,
        }
        for modifier in obj.modifiers
        if modifier.type == "ARMATURE"
    ]
    weighted_vertices = 0
    negative_weights = 0
    over_one_weights = 0
    for vertex in data.vertices:
        weights = [group.weight for group in vertex.groups]
        if weights:
            weighted_vertices += 1
        negative_weights += sum(1 for weight in weights if weight < 0)
        over_one_weights += sum(1 for weight in weights if weight > 1)
    return {
        "name": obj.name,
        "data_name": data.name,
        "vertices": len(data.vertices),
        "edges": len(data.edges),
        "polygons": len(data.polygons),
        "location": vec(obj.location),
        "rotation_euler_degrees": vec(math.degrees(v) for v in obj.rotation_euler),
        "scale": vec(obj.scale),
        "dimensions": vec(obj.dimensions),
        "world_bounds_min": vec(mins),
        "world_bounds_max": vec(maxs),
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "uv_layers": [layer.name for layer in data.uv_layers],
        "color_attributes": [layer.name for layer in data.color_attributes],
        "shape_keys": [key.name for key in data.shape_keys.key_blocks] if data.shape_keys else [],
        "modifiers": [{"name": modifier.name, "type": modifier.type} for modifier in obj.modifiers],
        "armature_modifiers": armature_modifiers,
        "vertex_groups": [group.name for group in obj.vertex_groups],
        "weighted_vertices": weighted_vertices,
        "negative_weights": negative_weights,
        "over_one_weights": over_one_weights,
        "topology": mesh_topology(obj),
    }


def armature_info(obj: bpy.types.Object) -> dict:
    bones = []
    for bone in obj.data.bones:
        bones.append({
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "children": [child.name for child in bone.children],
            "head_local": vec(bone.head_local),
            "tail_local": vec(bone.tail_local),
            "length": round(float(bone.length), 6),
            "matrix_local": [round(float(value), 6) for row in bone.matrix_local for value in row],
            "use_deform": bool(bone.use_deform),
        })
    return {
        "name": obj.name,
        "data_name": obj.data.name,
        "bone_count": len(bones),
        "location": vec(obj.location),
        "rotation_euler_degrees": vec(math.degrees(v) for v in obj.rotation_euler),
        "scale": vec(obj.scale),
        "bones": bones,
    }


def main() -> None:
    args = args_after_separator()
    input_path = os.path.abspath(args[0]) if args else bpy.data.filepath
    output_path = os.path.abspath(args[1]) if len(args) > 1 else input_path + ".inventory.json"
    if input_path.lower().endswith((".glb", ".gltf")):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.ops.import_scene.gltf(filepath=input_path)
    report = {
        "input": input_path,
        "blender_version": bpy.app.version_string,
        "scene": bpy.context.scene.name,
        "objects": [{"name": obj.name, "type": obj.type} for obj in bpy.data.objects],
        "meshes": [mesh_info(obj) for obj in bpy.data.objects if obj.type == "MESH"],
        "armatures": [armature_info(obj) for obj in bpy.data.objects if obj.type == "ARMATURE"],
        "images": [
            {
                "name": image.name,
                "filepath": image.filepath,
                "packed": image.packed_file is not None,
                "size": list(image.size),
            }
            for image in bpy.data.images
        ],
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"MODEL_INVENTORY={output_path}")


if __name__ == "__main__":
    main()
