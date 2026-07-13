"""Build and validate a MediaPipe-compatible rig for the project hand model.

Run with Blender 4.5+:
  blender --factory-startup --background --python rigging/build_rig.py -- hand.glb output
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

import bpy
from mathutils import Matrix, Vector


FINGER_LANDMARKS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}

FINGER_BONES = {
    finger: tuple(f"{finger}{index}R" for index in range(1, 4))
    for finger in FINGER_LANDMARKS
}

ALL_BONES = (
    "wristR",
    "handR",
    *(name for chain in FINGER_BONES.values() for name in chain),
)

POSES = (
    ("01_extended", {}),
    ("02_soft_curl", {"all": (18, 28, 38)}),
    ("03_fist", {"all": (42, 62, 76), "thumb": (25, 42, 55)}),
    ("04_thumb", {"thumb": (35, 55, 68)}),
    ("05_index", {"index": (35, 58, 72)}),
    ("06_middle", {"middle": (35, 58, 72)}),
    ("07_ring_pinky", {"ring": (35, 58, 72), "pinky": (38, 60, 74)}),
    ("08_splay", {"splay": True}),
    ("09_wrist", {"wrist": (18, 16)}),
)


def args_after_separator() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [vertex.co for vertex in obj.data.vertices]
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def duplicate_source(mesh: bpy.types.Object) -> bpy.types.Object:
    backup_collection = bpy.data.collections.new("Original_Source_Backup")
    bpy.context.scene.collection.children.link(backup_collection)
    duplicate = mesh.copy()
    duplicate.data = mesh.data.copy()
    duplicate.name = "OriginalHand_UNMODIFIED"
    backup_collection.objects.link(duplicate)
    for collection in list(duplicate.users_collection):
        if collection != backup_collection:
            collection.objects.unlink(duplicate)
    duplicate.hide_render = True
    duplicate.hide_set(True)
    backup_collection.hide_render = True
    backup_collection.hide_viewport = True
    return duplicate


def normalize_mesh(mesh: bpy.types.Object) -> tuple[dict[int, Vector], dict]:
    # Bake the imported node transform, then move the wrist to the origin.
    mesh.data.transform(mesh.matrix_world)
    mesh.matrix_world = Matrix.Identity(4)
    minimum, maximum = bounds(mesh)
    size = maximum - minimum
    center_x = (minimum.x + maximum.x) * 0.5
    center_y = (minimum.y + maximum.y) * 0.5

    def point(x_ratio: float, z_ratio: float, y_ratio: float = 0.0) -> Vector:
        return Vector((
            center_x + size.x * x_ratio,
            center_y + size.y * y_ratio,
            minimum.z + size.z * z_ratio,
        ))

    wrist = point(0.0, 0.09)
    wrist_before_shift = wrist.copy()
    points = {
        0: wrist,
        1: point(-0.17, 0.17),
        2: point(-0.31, 0.25),
        3: point(-0.43, 0.34),
        4: point(-0.52, 0.46),
        5: point(-0.25, 0.39),
        6: point(-0.28, 0.57),
        7: point(-0.30, 0.74),
        8: point(-0.31, 0.91),
        9: point(0.00, 0.40),
        10: point(0.00, 0.61),
        11: point(0.00, 0.80),
        12: point(0.00, 0.995),
        13: point(0.20, 0.39),
        14: point(0.22, 0.58),
        15: point(0.24, 0.75),
        16: point(0.26, 0.91),
        17: point(0.34, 0.36),
        18: point(0.39, 0.51),
        19: point(0.43, 0.66),
        20: point(0.46, 0.80),
    }
    shift = Matrix.Translation(-wrist_before_shift)
    mesh.data.transform(shift)
    for index in points:
        points[index] -= wrist_before_shift
    metadata = {
        "original_bounds_min": list(minimum),
        "original_bounds_max": list(maximum),
        "dimensions": list(size),
        "wrist_origin_before_shift": list(wrist_before_shift),
        "right_hand_basis": "+Z fingers, +X index-to-pinky, -X thumb, Y thickness",
    }
    mesh.name = "RiggedHandMesh"
    mesh.data.name = "RiggedHandMesh"
    return points, metadata


def make_armature(points: dict[int, Vector], height: float) -> bpy.types.Object:
    data = bpy.data.armatures.new("MediaPipeHand_R")
    armature = bpy.data.objects.new("MediaPipeHand_R", data)
    bpy.context.scene.collection.objects.link(armature)
    armature.show_in_front = True
    armature["rig_type"] = "MediaPipe Hand Landmarker 21"
    armature["rig_side"] = "R"

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    palm_normal = Vector((0, -1, 0))

    def add_bone(name: str, head: Vector, tail: Vector, parent=None, deform=True):
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        bone.parent = parent
        bone.use_connect = False
        bone.use_deform = deform
        bone.align_roll(palm_normal)
        return bone

    wrist = add_bone("wristR", Vector((0, 0, -height * 0.12)), points[0])
    hand = add_bone("handR", points[0], points[9], wrist)
    landmark_map = {"wristR": [0, 0], "handR": [0, 9]}
    for finger, landmark_chain in FINGER_LANDMARKS.items():
        parent = hand
        for number, (start, end) in enumerate(zip(landmark_chain[:-1], landmark_chain[1:]), 1):
            name = f"{finger}{number}R"
            parent = add_bone(name, points[start], points[end], parent)
            landmark_map[name] = [start, end]

    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in data.bones:
        if bone.name in landmark_map:
            start, end = landmark_map[bone.name]
            bone["mediapipe_start"] = start
            bone["mediapipe_end"] = end
    armature["mediapipe_bone_landmarks"] = json.dumps(landmark_map)
    return armature


def point_segment_distance(point: Vector, start: Vector, end: Vector) -> float:
    segment = end - start
    if segment.length_squared < 1e-12:
        return (point - start).length
    t = max(0.0, min(1.0, (point - start).dot(segment) / segment.length_squared))
    return (point - (start + segment * t)).length


def nail_component_overrides(
    mesh: bpy.types.Object,
    points: dict[int, Vector],
    height: float,
) -> tuple[dict[int, str], list[dict]]:
    nail_material_indices = {
        index
        for index, slot in enumerate(mesh.material_slots)
        if slot.material and "nail" in slot.material.name.lower()
    }
    nail_vertices = {
        vertex_index
        for polygon in mesh.data.polygons
        if polygon.material_index in nail_material_indices
        for vertex_index in polygon.vertices
    }
    adjacency = {index: set() for index in nail_vertices}
    for edge in mesh.data.edges:
        a, b = edge.vertices
        if a in nail_vertices and b in nail_vertices:
            adjacency[a].add(b)
            adjacency[b].add(a)
    overrides: dict[int, str] = {}
    components = []
    unvisited = set(nail_vertices)
    tip_bones = {
        finger: (points[indices[-1]], FINGER_BONES[finger][-1])
        for finger, indices in FINGER_LANDMARKS.items()
    }
    while unvisited:
        seed = unvisited.pop()
        component = {seed}
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unvisited:
                    unvisited.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        centroid = sum((mesh.data.vertices[index].co for index in component), Vector()) / len(component)
        finger, (tip, bone_name) = min(
            tip_bones.items(),
            key=lambda item: (centroid - item[1][0]).length,
        )
        distance = (centroid - tip).length
        assigned = bone_name if distance < height * 0.23 else "handR"
        for index in component:
            overrides[index] = assigned
        components.append({
            "vertices": len(component),
            "centroid": list(centroid),
            "nearest_finger": finger,
            "tip_distance": distance,
            "assigned_bone": assigned,
        })
    return overrides, components


def bind_custom_weights(
    mesh: bpy.types.Object,
    armature: bpy.types.Object,
    points: dict[int, Vector],
    height: float,
) -> tuple[dict, list[dict]]:
    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    groups = {name: mesh.vertex_groups.new(name=name) for name in ALL_BONES}
    chains = {
        finger: [
            (bone_name, points[start], points[end])
            for bone_name, (start, end) in zip(
                FINGER_BONES[finger],
                zip(indices[:-1], indices[1:]),
            )
        ]
        for finger, indices in FINGER_LANDMARKS.items()
    }
    lowest_mcp = min(points[index].z for index in (5, 9, 13, 17))
    transition = height * 0.07
    epsilon = height * 0.025
    counts = {name: 0 for name in ALL_BONES}
    nail_overrides, nail_components = nail_component_overrides(mesh, points, height)

    for vertex in mesh.data.vertices:
        point = vertex.co
        if vertex.index in nail_overrides:
            weights = {nail_overrides[vertex.index]: 1.0}
            total = 1.0
            for name, weight in weights.items():
                groups[name].add([vertex.index], weight, "REPLACE")
                counts[name] += 1
            continue
        thumb_distance = min(
            point_segment_distance(point, start, end)
            for _, start, end in chains["thumb"]
        )
        is_thumb = (
            point.x < points[5].x - height * 0.025
            and point.z > height * 0.04
            and thumb_distance < height * 0.19
        )
        finger_zone = point.z > lowest_mcp - transition or is_thumb
        if not finger_zone:
            if point.z < -height * 0.025:
                wrist_weight = min(1.0, max(0.0, (-point.z) / (height * 0.12)))
                weights = {"wristR": wrist_weight, "handR": 1.0 - wrist_weight}
            else:
                weights = {"handR": 1.0}
        else:
            chain_distances = {
                finger: min(point_segment_distance(point, start, end) for _, start, end in chain)
                for finger, chain in chains.items()
            }
            finger = min(chain_distances, key=chain_distances.get)
            distances = [
                (name, point_segment_distance(point, start, end))
                for name, start, end in chains[finger]
            ]
            distances.sort(key=lambda item: item[1])
            selected = distances[:2]
            raw = [(name, 1.0 / ((distance + epsilon) ** 3)) for name, distance in selected]
            total = sum(value for _, value in raw)
            weights = {name: value / total for name, value in raw}
            mcp_z = points[FINGER_LANDMARKS[finger][0]].z
            if finger != "thumb" and point.z < mcp_z + transition:
                finger_factor = min(1.0, max(0.0, (point.z - (mcp_z - transition)) / (2 * transition)))
                weights = {name: value * finger_factor for name, value in weights.items()}
                weights["handR"] = 1.0 - finger_factor

        total = sum(weights.values()) or 1.0
        for name, weight in weights.items():
            normalized = min(1.0, max(0.0, weight / total))
            if normalized > 1e-6:
                groups[name].add([vertex.index], normalized, "REPLACE")
                counts[name] += 1

    modifier = mesh.modifiers.new("MediaPipeHand_Armature", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    mesh.parent = armature
    mesh.matrix_parent_inverse = armature.matrix_world.inverted_safe()
    mesh["gltf_skin_ready"] = True
    mesh["weight_method"] = "finger-chain nearest segment with two-bone joint blending"
    return counts, nail_components


def select_only(*objects: bpy.types.Object) -> None:
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export_glb(mesh: bpy.types.Object, armature: bpy.types.Object, output: str) -> None:
    select_only(mesh, armature)
    requested = {
        "filepath": output,
        "export_format": "GLB",
        "use_selection": True,
        "export_skins": True,
        "export_def_bones": True,
        "export_rest_position_armature": True,
        "export_animations": False,
        "export_extras": True,
        "export_materials": "EXPORT",
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    result = bpy.ops.export_scene.gltf(**{key: value for key, value in requested.items() if key in available})
    if "FINISHED" not in result or not os.path.isfile(output):
        raise RuntimeError("GLB export failed")


def set_pose(armature: bpy.types.Object, spec: dict) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0, 0, 0)
    for finger, bone_names in FINGER_BONES.items():
        angles = spec.get(finger, spec.get("all"))
        if angles:
            for name, angle in zip(bone_names, angles):
                armature.pose.bones[name].rotation_euler.x = math.radians(angle)
    if spec.get("splay"):
        splay = {"index1R": -8, "middle1R": -2, "ring1R": 5, "pinky1R": 11, "thumb1R": -12}
        for name, angle in splay.items():
            armature.pose.bones[name].rotation_euler.z = math.radians(angle)
    if spec.get("wrist"):
        x_angle, z_angle = spec["wrist"]
        armature.pose.bones["wristR"].rotation_euler.x = math.radians(x_angle)
        armature.pose.bones["wristR"].rotation_euler.z = math.radians(z_angle)


def setup_render(mesh: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 600
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.025, 0.03, 0.038)
    minimum, maximum = bounds(mesh)
    center = (minimum + maximum) * 0.5
    camera_data = bpy.data.cameras.new("PoseTestCamera")
    camera = bpy.data.objects.new("PoseTestCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + Vector((0, -5, 0.15))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(mesh.dimensions.x, mesh.dimensions.z) * 1.35
    scene.camera = camera
    light_data = bpy.data.lights.new("PoseTestKey", "AREA")
    light_data.energy = 900
    light_data.size = 4
    light = bpy.data.objects.new("PoseTestKey", light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = center + Vector((2.2, -3.0, 3.0))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()


def evaluated_metrics(mesh: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in data.vertices]
        finite = all(math.isfinite(value) for point in points for value in point)
        minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
        maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
        return {
            "finite_vertices": finite,
            "bounds_min": list(minimum),
            "bounds_max": list(maximum),
            "dimensions": list(maximum - minimum),
            "vertex_count": len(data.vertices),
            "polygon_count": len(data.polygons),
        }
    finally:
        evaluated.to_mesh_clear()


def build_pose_tests(mesh: bpy.types.Object, armature: bpy.types.Object, output_dir: str) -> list[dict]:
    pose_dir = os.path.join(output_dir, "pose_tests")
    os.makedirs(pose_dir, exist_ok=True)
    setup_render(mesh)
    action = bpy.data.actions.new("MediaPipe_Rig_Pose_Tests")
    armature.animation_data_create()
    armature.animation_data.action = action
    results = []
    for frame, (name, spec) in enumerate(POSES, start=1):
        bpy.context.scene.frame_set(frame)
        set_pose(armature, spec)
        for pose_bone in armature.pose.bones:
            pose_bone.keyframe_insert("rotation_euler", frame=frame, group=pose_bone.name)
        bpy.context.view_layer.update()
        metrics = evaluated_metrics(mesh)
        filepath = os.path.join(pose_dir, f"{name}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        metrics.update({"pose": name, "frame": frame, "image": os.path.relpath(filepath, output_dir)})
        results.append(metrics)
    return results


def main() -> None:
    if bpy.app.version < (4, 5, 0):
        raise RuntimeError(f"Blender 4.5+ required, found {bpy.app.version_string}")
    args = args_after_separator()
    if len(args) < 2:
        raise RuntimeError("Input GLB and output directory are required")
    input_path = os.path.abspath(args[0])
    output_dir = os.path.abspath(args[1])
    os.makedirs(output_dir, exist_ok=True)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=input_path)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one mesh, found {len(meshes)}")
    mesh = meshes[0]
    duplicate_source(mesh)
    source_stats = {
        "vertices": len(mesh.data.vertices),
        "polygons": len(mesh.data.polygons),
        "materials": [slot.material.name if slot.material else None for slot in mesh.material_slots],
        "uv_layers": [layer.name for layer in mesh.data.uv_layers],
        "color_attributes": [layer.name for layer in mesh.data.color_attributes],
        "shape_keys": [key.name for key in mesh.data.shape_keys.key_blocks] if mesh.data.shape_keys else [],
        "modifiers": [modifier.type for modifier in mesh.modifiers],
    }
    points, orientation = normalize_mesh(mesh)
    height = orientation["dimensions"][2]
    armature = make_armature(points, height)
    weight_counts, nail_components = bind_custom_weights(mesh, armature, points, height)

    bpy.context.scene.frame_set(1)
    set_pose(armature, {})
    main_blend = os.path.join(output_dir, "rigged_hand.blend")
    bpy.ops.wm.save_as_mainfile(filepath=main_blend)
    export_glb(mesh, armature, os.path.join(output_dir, "rigged_hand.glb"))

    pose_results = build_pose_tests(mesh, armature, output_dir)
    test_blend = os.path.join(output_dir, "rigged_hand_test.blend")
    bpy.ops.wm.save_as_mainfile(filepath=test_blend)

    validation = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "blender_version": bpy.app.version_string,
        "input": input_path,
        "source": source_stats,
        "orientation": orientation,
        "landmarks": {str(index): list(point) for index, point in points.items()},
        "bones": [
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "deform": bone.use_deform,
                "head": list(bone.head_local),
                "tail": list(bone.tail_local),
            }
            for bone in armature.data.bones
        ],
        "weight_vertex_counts": weight_counts,
        "nail_component_assignments": nail_components,
        "pose_tests": pose_results,
        "outputs": {
            "glb": "rigged_hand.glb",
            "blend": "rigged_hand.blend",
            "test_blend": "rigged_hand_test.blend",
        },
    }
    with open(os.path.join(output_dir, "rigging_validation.json"), "w", encoding="utf-8") as handle:
        json.dump(validation, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"status": "ok", "output": output_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
