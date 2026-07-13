"""Prepare the downloaded anatomical hand for the MediaPipe web demo.

The source GLB is preserved separately. This script removes its viewer helper,
normalizes bone names, adds the app's wrist control, exports a rest-pose GLB,
and creates repeatable pose-test files with Blender 4.5+.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

import bpy
from mathutils import Vector


SOURCE_URL = "https://sketchfab.com/3d-models/anatomically-accurate-rigged-hand-model-for-xr-86f37207468b427ead21e2eef820c06c"
CREATOR = "Emma L. D. Lieker"
LICENSE = "CC BY-NC 4.0"

BONE_RENAMES = {
    "radius_ulna": "handR",
    "thumb_trapez": "thumb0R",
    "thumb_meta": "thumb1R",
    "thumb_prox": "thumb2R",
    "thumb_dist": "thumb3R",
    "index_meta": "index0R",
    "index_prox": "index1R",
    "index_midd": "index2R",
    "index_dist": "index3R",
    "midd_meta": "middle0R",
    "midd_prox": "middle1R",
    "midd_midd": "middle2R",
    "midd_dist": "middle3R",
    "ring_meta": "ring0R",
    "ring_prox": "ring1R",
    "ring_midd": "ring2R",
    "ring_dist": "ring3R",
    "pinky_meta": "pinky0R",
    "pinky_prox": "pinky1R",
    "pinky_midd": "pinky2R",
    "pinky_dist": "pinky3R",
}

FINGER_BONES = {
    finger: [f"{finger}{index}R" for index in range(1, 4)]
    for finger in ("thumb", "index", "middle", "ring", "pinky")
}

POSES = [
    ("01_extended", {}),
    ("02_soft_curl", {"all": (18, 25, 20), "thumb": (12, 18, 14)}),
    ("03_fist", {"all": (46, 68, 72), "thumb": (30, 42, 48)}),
    ("04_thumb", {"thumb": (38, 55, 58)}),
    ("05_index", {"index": (38, 58, 62)}),
    ("06_middle", {"middle": (38, 58, 62)}),
    ("07_ring_pinky", {"ring": (38, 58, 62), "pinky": (42, 62, 68)}),
    ("08_splay", {"splay": True}),
    ("09_wrist", {"wrist": (14, 12)}),
]


def args_after_separator() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def clear_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def select_only(*objects: bpy.types.Object) -> None:
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def prepare_rig(mesh: bpy.types.Object, armature: bpy.types.Object) -> None:
    armature.animation_data_clear()
    for pose_bone in armature.pose.bones:
        pose_bone.matrix_basis.identity()

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for old_name, new_name in BONE_RENAMES.items():
        bone = armature.data.edit_bones.get(old_name)
        if not bone:
            raise RuntimeError(f"Missing source bone: {old_name}")
        bone.name = new_name

    hand = armature.data.edit_bones["handR"]
    wrist = armature.data.edit_bones.new("wristR")
    direction = (hand.tail - hand.head).normalized()
    wrist.head = hand.head - direction * max(hand.length * 0.75, 0.1)
    wrist.tail = hand.head
    wrist.use_deform = False
    hand.parent = wrist
    bpy.ops.object.mode_set(mode="OBJECT")

    # Bone renaming normally propagates, but explicit group renaming keeps this
    # deterministic across Blender versions.
    for old_name, new_name in BONE_RENAMES.items():
        group = mesh.vertex_groups.get(old_name)
        if group:
            group.name = new_name

    armature.name = "AnatomicalHandRig_R"
    armature.data.name = "AnatomicalHandRig_R"
    mesh.name = "AnatomicalHandMesh_R"
    mesh.data.name = "AnatomicalHandMesh_R"
    if mesh.material_slots and mesh.material_slots[0].material:
        mesh.material_slots[0].material.name = "AnatomicalHandSurface"

    mesh["source_model"] = SOURCE_URL
    mesh["creator"] = CREATOR
    mesh["license"] = LICENSE
    armature["rig_type"] = "MediaPipe Hand Landmarker 21"
    armature["source_model"] = SOURCE_URL
    armature["license"] = LICENSE
    bpy.context.view_layer.update()


def export_glb(mesh: bpy.types.Object, armature: bpy.types.Object, output: str) -> None:
    select_only(mesh, armature)
    requested = {
        "filepath": output,
        "export_format": "GLB",
        "use_selection": True,
        "export_skins": True,
        "export_def_bones": False,
        "export_rest_position_armature": True,
        "export_animations": False,
        "export_extras": True,
        "export_materials": "EXPORT",
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    result = bpy.ops.export_scene.gltf(**{key: value for key, value in requested.items() if key in available})
    if "FINISHED" not in result or not os.path.isfile(output):
        raise RuntimeError("GLB export failed")


def reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0, 0, 0)


def set_pose(armature: bpy.types.Object, spec: dict) -> None:
    reset_pose(armature)
    for finger, bone_names in FINGER_BONES.items():
        angles = spec.get(finger, spec.get("all"))
        if angles:
            for name, angle in zip(bone_names, angles):
                armature.pose.bones[name].rotation_euler.x = math.radians(angle)
    if spec.get("splay"):
        for name, angle in {
            "thumb1R": -12,
            "index1R": -8,
            "middle1R": -2,
            "ring1R": 5,
            "pinky1R": 11,
        }.items():
            armature.pose.bones[name].rotation_euler.z = math.radians(angle)
    if spec.get("wrist"):
        x_angle, z_angle = spec["wrist"]
        armature.pose.bones["wristR"].rotation_euler.x = math.radians(x_angle)
        armature.pose.bones["wristR"].rotation_euler.z = math.radians(z_angle)


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


def setup_render(mesh: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 600
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.025, 0.03, 0.038)

    corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    center = sum(corners, Vector()) / 8
    span = max(mesh.dimensions.y, mesh.dimensions.z)
    camera_data = bpy.data.cameras.new("PoseTestCamera")
    camera = bpy.data.objects.new("PoseTestCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((span * 2, 0, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.35
    scene.camera = camera


def build_pose_tests(mesh: bpy.types.Object, armature: bpy.types.Object, output_dir: str) -> list[dict]:
    pose_dir = os.path.join(output_dir, "pose_tests")
    os.makedirs(pose_dir, exist_ok=True)
    setup_render(mesh)
    action = bpy.data.actions.new("Anatomical_Hand_Pose_Tests")
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
    if len(args) < 3:
        raise RuntimeError("Input GLB, dist directory, and web GLB path are required")
    input_path, output_dir, web_glb = map(os.path.abspath, args[:3])
    os.makedirs(output_dir, exist_ok=True)

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=input_path)
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one armature, found {len(armatures)}")
    armature = armatures[0]
    skinned_meshes = [obj for obj in meshes if any(mod.type == "ARMATURE" for mod in obj.modifiers)]
    if len(skinned_meshes) != 1:
        raise RuntimeError(f"Expected one skinned mesh, found {len(skinned_meshes)}")
    mesh = skinned_meshes[0]
    for helper in (obj for obj in meshes if obj != mesh):
        bpy.data.objects.remove(helper, do_unlink=True)

    prepare_rig(mesh, armature)
    source_stats = {
        "vertices": len(mesh.data.vertices),
        "polygons": len(mesh.data.polygons),
        "materials": [slot.material.name if slot.material else None for slot in mesh.material_slots],
        "uv_layers": [layer.name for layer in mesh.data.uv_layers],
        "weighted_vertices": sum(1 for vertex in mesh.data.vertices if vertex.groups),
    }

    reset_pose(armature)
    bpy.context.scene.frame_set(1)
    armature.animation_data_clear()
    main_blend = os.path.join(output_dir, "rigged_hand.blend")
    bpy.ops.wm.save_as_mainfile(filepath=main_blend)
    dist_glb = os.path.join(output_dir, "rigged_hand.glb")
    export_glb(mesh, armature, dist_glb)
    export_glb(mesh, armature, web_glb)

    pose_results = build_pose_tests(mesh, armature, output_dir)
    test_blend = os.path.join(output_dir, "rigged_hand_test.blend")
    bpy.ops.wm.save_as_mainfile(filepath=test_blend)

    validation = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "blender_version": bpy.app.version_string,
        "input": input_path,
        "source_url": SOURCE_URL,
        "creator": CREATOR,
        "license": LICENSE,
        "source": source_stats,
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
