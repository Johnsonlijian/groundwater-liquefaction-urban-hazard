"""Shared Blender materials for the DGLS Figure 1 cutaway scene."""
from __future__ import annotations

import bpy


def mat(name: str, color, alpha: float = 1.0, roughness: float = 0.55):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Roughness"].default_value = roughness
    if alpha < 1:
        material.blend_method = "BLEND"
        material.use_screen_refraction = True
        material.show_transparent_back = True
    return material


def build_materials():
    return {
        "surface": mat("surface_green", (0.43, 0.60, 0.34, 1), 1),
        "soil": mat("cutaway_soil", (0.58, 0.36, 0.21, 1), 1),
        "front": mat("cutaway_dark_face", (0.03, 0.025, 0.02, 1), 0.84),
        "aquifer": mat("transparent_shallow_aquifer", (0.19, 0.66, 0.95, 0.38), 0.38, 0.15),
        "water": mat("water_table_blue", (0.12, 0.58, 0.90, 0.68), 0.68, 0.1),
        "sand": mat("susceptible_sand_silt", (0.80, 0.63, 0.44, 1), 1),
        "aquitard": mat("confining_aquitard", (0.45, 0.47, 0.51, 1), 1),
        "building": mat("city_building", (0.77, 0.84, 0.91, 1), 1),
        "recharge": mat("recharge_orange", (0.85, 0.32, 0.12, 1), 1),
        "depletion": mat("depletion_blue", (0.12, 0.40, 0.72, 1), 1),
        "well": mat("monitoring_well_white", (0.96, 0.98, 1.0, 1), 1),
        "glow": mat("hidden_state_variable_glow", (0.95, 0.82, 0.18, 1), 1),
    }
