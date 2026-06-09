"""Create the DGLS Figure 1 Blender cutaway scene.

Run inside Blender:
    blender --background --python blender/render_fig1.py
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector

try:
    from materials import build_materials
except Exception:
    from .materials import build_materials


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "export" / "blender"
OUT.mkdir(parents=True, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def cube(name, loc, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    return obj


def cylinder(name, loc, radius, depth, material, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def cone(name, loc, radius1, radius2, depth, material, vertices=48):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def arrow(name, start, end, material, radius=0.035):
    start_v = Vector(start)
    end_v = Vector(end)
    mid = (start_v + end_v) / 2
    direction = end_v - start_v
    length = direction.length
    shaft = cylinder(name + "_shaft", mid, radius, length * 0.78, material, 24)
    shaft.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    head_loc = start_v + direction * 0.88
    head = cone(name + "_head", head_loc, radius * 4.0, 0.0, length * 0.18, material, 32)
    head.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return shaft, head


def add_curve(name, points, material, bevel_depth=0.025):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 18
    spl = curve.splines.new("POLY")
    spl.points.add(len(points) - 1)
    for p, co in zip(spl.points, points):
        p.co = (co[0], co[1], co[2], 1)
    curve.bevel_depth = bevel_depth
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def make_scene():
    clear_scene()
    mats = build_materials()

    # Geological block and exposed cut face.
    cube("BasinBlock_soil", (0, 0, -1.2), (9.5, 5.7, 2.4), mats["soil"])
    cube("Cutaway_front_face", (0, -2.88, -1.2), (9.55, 0.08, 2.45), mats["front"])
    cube("Urban_surface", (0, 0, 0.05), (9.55, 5.75, 0.14), mats["surface"])

    # Layered geology on cut face.
    cube("Unsaturated_zone", (0, -2.94, -0.20), (9.3, 0.10, 0.45), mats["soil"])
    cube("Shallow_aquifer", (0, -2.98, -0.88), (9.25, 0.12, 0.62), mats["aquifer"])
    cube("Susceptible_sand_silt", (0, -3.02, -1.52), (9.25, 0.12, 0.42), mats["sand"])
    cube("Confining_aquitard", (0, -3.05, -2.00), (9.25, 0.12, 0.22), mats["aquitard"])

    # Curved water table and static baseline line.
    wt = [(-4.45, -3.13, -0.82), (-2.5, -3.13, -0.74), (-0.5, -3.13, -0.86), (1.9, -3.13, -0.62), (4.45, -3.13, -0.36)]
    add_curve("Observed_dynamic_water_table", wt, mats["water"], 0.04)
    add_curve("Static_baseline_water_table", [(-4.45, -3.17, -0.55), (4.45, -3.17, -0.55)], mats["well"], 0.012)

    # City and local monitoring objects.
    for i, (x, y, h) in enumerate([(-3.4, -0.6, 0.9), (-2.7, 0.2, 1.35), (-1.9, -0.35, 1.05), (-0.8, 0.55, 1.55), (0.25, -0.15, 0.85)]):
        cube(f"City_building_{i+1}", (x, y, 0.05 + h / 2), (0.42, 0.42, h), mats["building"])
    cylinder("Monitoring_well", (2.7, -2.72, -0.55), 0.055, 1.9, mats["well"], 32)
    cube("Infiltration_basin", (-3.2, 1.65, 0.13), (1.2, 0.7, 0.05), mats["water"])
    cylinder("Pumping_well", (3.45, 1.35, -0.45), 0.06, 1.45, mats["depletion"], 32)

    # Process arrows and mechanism markers.
    arrow("Recharge_arrow", (-3.2, 1.65, 1.8), (-3.2, 1.65, 0.25), mats["recharge"], 0.04)
    arrow("Pumping_arrow", (3.45, 1.35, 0.25), (3.45, 1.35, 1.75), mats["depletion"], 0.04)
    cone("Cone_of_depression", (3.45, 1.35, -0.37), 1.05, 0.16, 0.36, mats["depletion"], 64)
    cylinder("Hidden_state_variable_marker", (1.45, -3.20, -0.55), 0.13, 0.08, mats["glow"], 48)

    # Seismic-wave traces on the exposed face.
    for k in range(4):
        pts = []
        for j in range(80):
            x = -4.2 + j * 0.11
            z = -2.15 + 0.11 * math.sin(j * 0.45 + k)
            pts.append((x, -3.22, z + k * 0.18))
        add_curve(f"Seismic_wave_{k+1}", pts, mats["recharge"], 0.015)

    # Lighting/camera.
    bpy.ops.object.light_add(type="AREA", location=(0, -4, 6))
    bpy.context.object.name = "Softbox_front"
    bpy.context.object.data.energy = 650
    bpy.context.object.data.size = 5.5
    bpy.ops.object.light_add(type="AREA", location=(-4, 3, 5))
    bpy.context.object.name = "Softbox_left"
    bpy.context.object.data.energy = 280
    bpy.context.object.data.size = 4

    bpy.ops.object.camera_add(location=(7.8, -8.6, 5.6), rotation=(math.radians(60), 0, math.radians(43)))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 9.5

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 96
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.render.resolution_x = 4200
    bpy.context.scene.render.resolution_y = 3000
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Fig1_DGLS_cutaway_scene.blend"))


if __name__ == "__main__":
    make_scene()
