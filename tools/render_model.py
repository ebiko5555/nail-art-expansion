"""Render front and side model inspection images without modifying the source."""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_view(mesh: bpy.types.Object, output: str, direction: Vector) -> None:
    corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    center = sum(corners, Vector()) / 8
    span = max(mesh.dimensions) * 1.35
    camera_data = bpy.data.cameras.new("InspectionCamera")
    camera = bpy.data.objects.new("InspectionCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + direction.normalized() * max(span * 2, 2)
    look_at(camera, center)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.04, 0.05)
    scene.render.filepath = output
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(camera_data)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    input_path, output_dir = map(os.path.abspath, args[:2])
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=input_path)
    mesh = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    os.makedirs(output_dir, exist_ok=True)

    light_data = bpy.data.lights.new("InspectionKey", "AREA")
    light_data.energy = 1000
    light_data.shape = "DISK"
    light_data.size = 5
    light = bpy.data.objects.new("InspectionKey", light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = Vector((2.5, -3.5, 4.0))
    look_at(light, mesh.matrix_world.translation)

    render_view(mesh, os.path.join(output_dir, "front.png"), Vector((0, -1, 0)))
    render_view(mesh, os.path.join(output_dir, "back.png"), Vector((0, 1, 0)))
    render_view(mesh, os.path.join(output_dir, "side.png"), Vector((1, 0, 0)))


if __name__ == "__main__":
    main()
