
import json
import os
from datetime import datetime
from tkinter import Image
import zipfile
import re

import google.generativeai as genai
import PIL.Image
import PIL.ImageDraw
import random
try:
    from . import external_files as ef
except ImportError:
    import external_files as ef

# from google import genai

# Load .env variables from a .env file if it exists (for local testing)
def _to_number_or_default(value, default_value):
    try:
        return float(value)
    except Exception:
        return float(default_value)

_ALLOWED_SECTION_TYPES = {
    "start_zone",
    "jump_tutorial",
    "platform_sequence",
    "gap_sequence",
    "moving_platform_tutorial",
    "hazard_zone",
    "branch",
    "timed_challenge_sequence",
    "exploration_zone",
    "end_zone",
}
def _coerce_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


API_KEY="AIzaSyDa8oGtpSEUCAcwqN9f8oTt0Jy_zin5-Og"

def _normalize_range(value, minimum, maximum, default_range):
    if not isinstance(value, list) or len(value) < 2:
        return default_range
    left = int(round(_to_number_or_default(value[0], default_range[0])))
    right = int(round(_to_number_or_default(value[1], default_range[1])))
    left = max(minimum, min(maximum, left))
    right = max(minimum, min(maximum, right))
    if left > right:
        left, right = right, left
    return [left, right]


def _extract_json_object(text: str) -> str:
    """Extract the first JSON object from model output, including fenced output."""
    if not text:
        return ""
    raw = text.strip()

    # Handle markdown-fenced responses:
    # ```json
    # { ... }
    # ```
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return ""
    return raw[start:end + 1]


def _try_parse_agent_language_json(text: str) -> dict | None:
    if not text:
        return None
    candidate = _extract_json_object(text)
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    if "globals" not in parsed or "levels" not in parsed:
        return None
    return parsed


def _clamp_int(value, minimum, maximum, fallback):
    try:
        number = int(round(float(value)))
    except Exception:
        number = fallback
    return max(minimum, min(maximum, number))


def _range_pair(value, fallback_left, fallback_right):
    if isinstance(value, list) and len(value) >= 2:
        return value[0], value[1]
    return fallback_left, fallback_right


def _build_internal_sketch_image(agent_language: dict) -> PIL.Image.Image:
    """
    Builds a simple in-memory sketch image from agent-language JSON.
    This is an internal visualization aid, not an exported asset.
    """
    globals_obj = agent_language.get("globals", {}) if isinstance(agent_language, dict) else {}
    levels = agent_language.get("levels", []) if isinstance(agent_language, dict) else []
    level = levels[0] if levels and isinstance(levels[0], dict) else {}
    sections = level.get("sections", []) if isinstance(level, dict) else []
    if not isinstance(sections, list):
        sections = []

    rng_seed = _clamp_int(globals_obj.get("rng_seed", 42), 0, 10_000_000, 42)
    rng = random.Random(rng_seed)

    width_tiles = 140
    height_tiles = 28
    tile = 8

    image = PIL.Image.new("RGB", (width_tiles * tile, height_tiles * tile), "white")
    draw = PIL.ImageDraw.Draw(image)

    empty_color = (255, 255, 255)
    solid_color = (40, 40, 40)
    hazard_color = (220, 40, 40)
    reward_color = (240, 180, 40)
    moving_color = (120, 80, 220)
    marker_color = (20, 120, 240)

    draw.rectangle([0, 0, width_tiles * tile, height_tiles * tile], fill=empty_color)

    floor_y = height_tiles - 3
    draw.rectangle([0, floor_y * tile, width_tiles * tile, height_tiles * tile], fill=(230, 230, 230))

    x_cursor = 2
    spawn_drawn = False
    goal_drawn = False

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_type = section.get("type", "platform_sequence")
        params = section.get("parameters", {})
        if not isinstance(params, dict):
            params = {}

        section_len = _clamp_int(params.get("length_tiles", 12), 4, 30, 12)
        base_y = _clamp_int(params.get("base_y", 0), -6, 6, 0)
        y_base = floor_y - base_y

        count = _clamp_int(params.get("count", 3), 1, 20, 3)
        platform_width = _clamp_int(params.get("platform_width", 2), 1, 8, 2)
        gap_left, gap_right = _range_pair(params.get("gap"), 1, 2)
        gap_min = _clamp_int(gap_left, 0, 8, 1)
        gap_max = _clamp_int(gap_right, 0, 8, 2)
        if gap_min > gap_max:
            gap_min, gap_max = gap_max, gap_min

        hv_left, hv_right = _range_pair(params.get("height_variation"), 0, 0)
        hv_min = _clamp_int(hv_left, 0, 6, 0)
        hv_max = _clamp_int(hv_right, 0, 6, 0)
        if hv_min > hv_max:
            hv_min, hv_max = hv_max, hv_min

        start_x = x_cursor
        local_x = start_x

        if section_type in {"start_zone", "end_zone"}:
            width = _clamp_int(params.get("width", section_len), 3, 30, section_len)
            left_px = local_x * tile
            right_px = min((local_x + width) * tile, width_tiles * tile - 1)
            top_px = y_base * tile
            draw.rectangle([left_px, top_px, right_px, top_px + tile - 1], fill=solid_color)
            if section_type == "start_zone" and not spawn_drawn:
                draw.ellipse([left_px, top_px - 2 * tile, left_px + tile, top_px - tile], fill=marker_color)
                spawn_drawn = True
            if section_type == "end_zone" and not goal_drawn:
                draw.rectangle([right_px - tile, top_px - 2 * tile, right_px, top_px], fill=(60, 180, 60))
                goal_drawn = True
            local_x += width
        elif section_type == "hazard_zone":
            width = _clamp_int(params.get("effect_area_width", section_len), 4, 30, section_len)
            for hx in range(local_x, min(local_x + width, width_tiles - 2)):
                draw.polygon(
                    [
                        (hx * tile, y_base * tile),
                        ((hx + 0.5) * tile, (y_base - 1) * tile),
                        ((hx + 1) * tile, y_base * tile),
                    ],
                    fill=hazard_color,
                )
            local_x += width
        elif section_type == "branch":
            branch_len = _clamp_int(params.get("length_tiles", 12), 6, 40, 12)
            paths = section.get("paths", [])
            if not isinstance(paths, list):
                paths = []
            path_count = _clamp_int(params.get("paths", params.get("paths_count", len(paths) or 2)), 2, 5, max(2, len(paths)))
            if len(paths) < path_count:
                paths = paths + [{} for _ in range(path_count - len(paths))]

            # Draw one horizontal lane per path so branch topology is visible.
            lane_step = 3
            lane_start_y = max(3, y_base - 1)
            lane_ys = [max(2, lane_start_y - lane_step * i) for i in range(path_count)]

            # Trunk leading into branch.
            for bx in range(local_x, min(local_x + 2, width_tiles - 2)):
                draw.rectangle([bx * tile, y_base * tile, (bx + 1) * tile - 1, y_base * tile + tile - 1], fill=solid_color)

            lane_x0 = local_x + 2
            lane_x1 = min(local_x + branch_len, width_tiles - 3)
            for path_idx in range(path_count):
                path_obj = paths[path_idx] if path_idx < len(paths) and isinstance(paths[path_idx], dict) else {}
                py = lane_ys[path_idx]
                # Lane body
                for bx in range(lane_x0, lane_x1):
                    draw.rectangle([bx * tile, py * tile, (bx + 1) * tile - 1, py * tile + tile - 1], fill=solid_color)

                features = [str(x).lower() for x in _coerce_list(path_obj.get("features", []))]
                reward = _coerce_list(path_obj.get("reward", []))
                difficulty = str(path_obj.get("difficulty", "")).lower()

                # Feature hints: hazards and moving sections.
                if any("spike" in f or "hazard" in f for f in features):
                    for bx in range(lane_x0 + 1, lane_x1, 4):
                        draw.polygon(
                            [
                                (bx * tile, py * tile),
                                ((bx + 0.5) * tile, (py - 1) * tile),
                                ((bx + 1) * tile, py * tile),
                            ],
                            fill=hazard_color,
                        )
                if any("moving" in f or "timing" in f for f in features):
                    for bx in range(lane_x0 + 2, lane_x1, 6):
                        draw.rectangle(
                            [bx * tile, (py - 1) * tile, (bx + 1) * tile - 1, py * tile - 1],
                            outline=moving_color,
                            width=1,
                        )

                # Difficulty hint via lane marker.
                if difficulty in {"hard", "extreme"}:
                    draw.rectangle([lane_x0 * tile, (py - 2) * tile, lane_x0 * tile + tile - 1, (py - 1) * tile - 1], fill=hazard_color)
                elif difficulty in {"medium"}:
                    draw.rectangle([lane_x0 * tile, (py - 2) * tile, lane_x0 * tile + tile - 1, (py - 1) * tile - 1], fill=(245, 150, 30))
                else:
                    draw.rectangle([lane_x0 * tile, (py - 2) * tile, lane_x0 * tile + tile - 1, (py - 1) * tile - 1], fill=(60, 180, 60))

                # Reward hint at end of each path.
                if reward:
                    rx = lane_x1 - 1
                    draw.ellipse([rx * tile, (py - 2) * tile, (rx + 1) * tile - 1, (py - 1) * tile - 1], fill=reward_color)

            local_x += branch_len
        else:
            for _ in range(count):
                h_var = rng.randint(hv_min, hv_max) if hv_max > 0 else 0
                py = max(2, y_base - h_var)
                left_px = local_x * tile
                right_px = min((local_x + platform_width) * tile, width_tiles * tile - 1)
                top_px = py * tile
                draw.rectangle([left_px, top_px, right_px, top_px + tile - 1], fill=solid_color)
                local_x += platform_width + rng.randint(gap_min, gap_max)

        x_cursor = min(width_tiles - 4, max(local_x + 1, start_x + section_len))

    # Ensure both high-level landmarks exist in the sketch.
    if not spawn_drawn:
        draw.ellipse([2 * tile, (floor_y - 2) * tile, 3 * tile, (floor_y - 1) * tile], fill=marker_color)
    if not goal_drawn:
        draw.rectangle(
            [(width_tiles - 4) * tile, (floor_y - 2) * tile, (width_tiles - 3) * tile, floor_y * tile],
            fill=(60, 180, 60),
        )

    return image


def _write_ldtk_zip(ldtk_json_text: str, output_dir: str = "level_design_agent\\output") -> str:
    parsed = json.loads(ldtk_json_text)
    normalized_text = json.dumps(parsed, ensure_ascii=True, indent=2)

    abs_output_dir = os.path.abspath(output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ldtk_filename = f"generated_level_{timestamp}.ldtk"
    zip_filename = f"generated_level_{timestamp}.zip"

    ldtk_path = os.path.join(abs_output_dir, ldtk_filename)
    zip_path = os.path.join(abs_output_dir, zip_filename)

    with open(ldtk_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(ldtk_path, arcname=ldtk_filename)

    return zip_path


def _is_image_path(value: str) -> bool:
    if not isinstance(value, str):
        return False
    ext = os.path.splitext(value)[1].lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _extract_existing_image_path(value: str) -> str | None:
    if not isinstance(value, str):
        return None

    # 1) Direct value
    direct = value.strip().strip('"').strip("'")
    if _is_image_path(direct) and os.path.exists(direct):
        return direct

    # 2) "Bridge image created at:" / multiline output support
    line_candidates = []
    for line in value.splitlines():
        cleaned = line.strip().strip('"').strip("'")
        if cleaned:
            if cleaned.lower().startswith("bridge image created at:"):
                cleaned = cleaned.split(":", 1)[1].strip()
            line_candidates.append(cleaned)

    # 3) Regex extract Windows-like absolute image paths from free text
    regex_candidates = re.findall(r"[A-Za-z]:\\[^\n\r\"']+\.(?:png|jpg|jpeg|webp|bmp)", value, flags=re.IGNORECASE)
    line_candidates.extend(regex_candidates)

    for candidate in line_candidates:
        if _is_image_path(candidate) and os.path.exists(candidate):
            return candidate

    return None


def _write_bridge_image_from_agent_language(agent_language_json: str, output_dir: str | None = None) -> str:
    parsed_agent_language = _try_parse_agent_language_json(agent_language_json)
    if not parsed_agent_language:
        raise ValueError("Invalid agent-language JSON for bridge image generation.")

    image = _build_internal_sketch_image(parsed_agent_language)
    if output_dir is None:
        output_dir = getattr(ef, "bridge_output_dir", "level_design_agent\\output")
    abs_output_dir = os.path.abspath(output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(abs_output_dir, f"bridge_visual_{timestamp}.png")
    image.save(image_path, format="PNG")
    return image_path


def _write_bridge_images_from_agent_language(agent_language_json: str, output_dir: str | None = None) -> list[str]:
    parsed_agent_language = _try_parse_agent_language_json(agent_language_json)
    if not parsed_agent_language:
        raise ValueError("Invalid agent-language JSON for bridge image generation.")

    globals_obj = parsed_agent_language.get("globals", {})
    levels = parsed_agent_language.get("levels", [])
    if not isinstance(levels, list) or not levels:
        raise ValueError("No levels found in agent-language JSON.")

    if output_dir is None:
        output_dir = getattr(ef, "bridge_output_dir", "level_design_agent\\output")
    abs_output_dir = os.path.abspath(output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    image_paths = []
    for idx, level_obj in enumerate(levels, start=1):
        one_level_payload = {
            "globals": globals_obj,
            "levels": [level_obj if isinstance(level_obj, dict) else {}],
        }
        image = _build_internal_sketch_image(one_level_payload)
        image_path = os.path.join(abs_output_dir, f"bridge_visual_{timestamp}_L{idx}.png")
        image.save(image_path, format="PNG")
        image_paths.append(image_path)

    return image_paths


def image_to_ldtk_with_examples(target_image_path: str, api_key, content_pairs, model_name="gemini-2.5-flash") -> str:
    if not target_image_path or not os.path.exists(target_image_path):
        return f"API Error: Target image path does not exist: {target_image_path}"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    request_content = []
    request_content.append(
        "The following are image and LDtk JSON examples. Convert the target image into valid LDtk JSON."
    )

    for index, (img_path, text_path) in enumerate(content_pairs):
        request_content.append(f"\n##Example {index + 1}\n")
        if img_path:
            try:
                request_content.append(PIL.Image.open(img_path))
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                continue
        text = _read_text_file(text_path)
        if text:
            request_content.append(text)

    request_content.append("\n##Target Image\n")
    request_content.append(PIL.Image.open(target_image_path))
    request_content.append(
        """
Return only a valid JSON object for LDtk.
Do not include markdown or explanation text.
"""
    )

    try:
        response = model.generate_content(
            request_content,
            generation_config={"response_mime_type": "application/json"},
        )
        raw_text = (response.text or "").strip()
        json_text = _extract_json_object(raw_text)
        if not json_text:
            return f"API Error: Model response did not contain a JSON object. Raw: {raw_text[:500]}"
        parsed = json.loads(json_text)
        return json.dumps(parsed, ensure_ascii=True, indent=2)
    except TypeError:
        try:
            print("Model did not suppoert json response")
            response = model.generate_content(request_content)
            raw_text = (response.text or "").strip()
            json_text = _extract_json_object(raw_text)
            if not json_text:
                return f"API Error: Model response did not contain a JSON object. Raw: {raw_text[:500]}"
            parsed = json.loads(json_text)
            return json.dumps(parsed, ensure_ascii=True, indent=2)
        except Exception as e:
            return f"API Error: {e}"
    except Exception as e:
        return f"API Error: {e}"


def _agent_language_to_ldtk_by_level_images(agent_language_json: str, api_key, content_pairs, model_name="gemini-2.5-flash") -> str:
    try:
        image_paths = _write_bridge_images_from_agent_language(agent_language_json)
    except Exception as e:
        return f"API Error: Failed to create bridge images: {e}"

    merged_project = None
    merged_levels = []

    for image_path in image_paths:
        one_result = image_to_ldtk_with_examples(
            target_image_path=image_path,
            api_key=api_key,
            content_pairs=content_pairs,
            model_name=model_name,
        )
        if isinstance(one_result, str) and one_result.startswith("API Error:"):
            return one_result

        try:
            parsed = json.loads(one_result)
        except Exception as e:
            return f"API Error: Failed to parse per-level LDtk result: {e}"

        level_items = parsed.get("levels", []) if isinstance(parsed, dict) else []
        if not isinstance(level_items, list) or not level_items:
            return "API Error: Per-level LDtk conversion returned no levels."

        if merged_project is None:
            merged_project = parsed
        merged_levels.append(level_items[0])

    if not isinstance(merged_project, dict):
        return "API Error: Failed to build merged LDtk project."

    merged_project["levels"] = merged_levels
    return json.dumps(merged_project, ensure_ascii=True, indent=2)

def _normalize_agent_language_schema(parsed: dict) -> dict:
    if not isinstance(parsed, dict):
        parsed = {}

    globals_in = parsed.get("globals", {}) if isinstance(parsed.get("globals"), dict) else {}
    player_constraints = globals_in.get("player_constraints", {}) if isinstance(globals_in.get("player_constraints"), dict) else {}

    max_jump_distance = int(round(_to_number_or_default(player_constraints.get("max_jump_distance_tiles"), 4)))
    max_jump_height = int(round(_to_number_or_default(player_constraints.get("max_jump_height_tiles"), 2)))
    max_jump_distance = max(1, min(12, max_jump_distance))
    max_jump_height = max(1, min(8, max_jump_height))

    normalized_globals = {
        "grid_size": int(round(_to_number_or_default(globals_in.get("grid_size"), 8))),
        "rng_seed": int(round(_to_number_or_default(globals_in.get("rng_seed"), 42))),
        "player_constraints": {
            "max_jump_distance_tiles": max_jump_distance,
            "max_jump_height_tiles": max_jump_height,
            "double_jump": bool(player_constraints.get("double_jump", False)),
        },
        "tile_value_map": globals_in.get("tile_value_map", {"empty": 0, "solid": 1, "hazard": 2}),
        "entity_types": globals_in.get(
            "entity_types",
            {
                "player_spawn": "PlayerSpawn",
                "goal": "Goal",
                "enemy_patrol": "EnemyPatrol",
                "coin": "Coin",
                "powerup": "Powerup",
                "hazard_spike": "HazardSpike",
            },
        ),
    }

    normalized_levels = []
    levels_in = parsed.get("levels", [])
    if not isinstance(levels_in, list):
        levels_in = []

    for i, level_data in enumerate(levels_in):
        level_obj = level_data if isinstance(level_data, dict) else {}
        level_number = int(round(_to_number_or_default(level_obj.get("level"), i + 1)))
        difficulty = _to_number_or_default(level_obj.get("difficulty"), 1.0)
        difficulty = max(1.0, min(10.0, difficulty))

        sections_in = level_obj.get("sections", [])
        if not isinstance(sections_in, list):
            sections_in = []

        normalized_sections = []
        has_branch = False

        for section_data in sections_in:
            section_obj = section_data if isinstance(section_data, dict) else {}
            section_type = section_obj.get("type", "platform_sequence")
            if section_type not in _ALLOWED_SECTION_TYPES:
                section_type = "platform_sequence"

            parameters = section_obj.get("parameters", {})
            if not isinstance(parameters, dict):
                parameters = {}

            # Consistency: use "count" everywhere.
            if "platform_count" in parameters and "count" not in parameters:
                parameters["count"] = parameters.pop("platform_count")

            # Consistency: speed is always a range.
            if "speed" in parameters and "speed_range" not in parameters:
                speed_val = parameters.pop("speed")
                if isinstance(speed_val, list) and len(speed_val) >= 2:
                    parameters["speed_range"] = [float(speed_val[0]), float(speed_val[1])]
                else:
                    numeric_speed = _to_number_or_default(speed_val, 0.5)
                    parameters["speed_range"] = [numeric_speed, numeric_speed]

            # Deterministic placement fields for LDtk conversion.
            parameters.setdefault("length_tiles", 12)
            parameters.setdefault("start_x_policy", "append")
            parameters.setdefault("base_y", 0)

            # Playability guards.
            if "gap" in parameters:
                parameters["gap"] = _normalize_range(parameters["gap"], 1, max_jump_distance, [1, min(2, max_jump_distance)])
            if "height_variation" in parameters:
                parameters["height_variation"] = _normalize_range(parameters["height_variation"], 0, max_jump_height, [0, min(1, max_jump_height)])
            if "platform_height" in parameters:
                parameters["platform_height"] = max(0, min(max_jump_height, int(round(_to_number_or_default(parameters["platform_height"], 1)))))

            intent = section_obj.get("intent", {})
            if not isinstance(intent, dict):
                intent = {}

            requires = _coerce_list(section_obj.get("requires", []))
            requires = [str(x) for x in requires]

            target_layer = section_obj.get("target_layer")
            if target_layer not in {"IntGrid_layer", "Entities"}:
                if section_type in {"platform_sequence", "gap_sequence", "jump_tutorial", "start_zone", "end_zone"}:
                    target_layer = "IntGrid_layer"
                else:
                    target_layer = "Entities"

            normalized_section = {
                "type": section_type,
                "target_layer": target_layer,
                "parameters": parameters,
                "intent": intent,
                "requires": requires,
            }

            if section_type == "branch":
                has_branch = True
                paths_in = section_obj.get("paths", [])
                if not isinstance(paths_in, list):
                    paths_in = []
                normalized_paths = []
                for path_index, path in enumerate(paths_in):
                    path_obj = path if isinstance(path, dict) else {}
                    normalized_paths.append(
                        {
                            "path_name": str(path_obj.get("path_name", f"Path {path_index + 1}")),
                            "difficulty": str(path_obj.get("difficulty", "medium")),
                            "features": [str(x) for x in _coerce_list(path_obj.get("features", []))],
                            "requires": [str(x) for x in _coerce_list(path_obj.get("requires", []))],
                            "reward": [str(x) for x in _coerce_list(path_obj.get("reward", []))],
                        }
                    )
                while len(normalized_paths) < 2:
                    default_index = len(normalized_paths) + 1
                    normalized_paths.append(
                        {
                            "path_name": f"Path {default_index}",
                            "difficulty": "medium",
                            "features": [],
                            "requires": [],
                            "reward": [],
                        }
                    )
                normalized_section["paths"] = normalized_paths

            normalized_sections.append(normalized_section)

        # Branch coverage for more complex levels.
        if difficulty >= 5.0 and not has_branch:
            normalized_sections.append(
                {
                    "type": "branch",
                    "target_layer": "Entities",
                    "parameters": {"length_tiles": 12, "start_x_policy": "append", "base_y": 0},
                    "intent": {"risk_reward": "medium"},
                    "requires": [],
                    "paths": [
                        {"path_name": "Path A", "difficulty": "hard", "features": [], "requires": [], "reward": []},
                        {"path_name": "Path B", "difficulty": "easy", "features": [], "requires": [], "reward": []},
                    ],
                }
            )

        normalized_levels.append(
            {
                "level": level_number,
                "difficulty": round(difficulty, 2),
                "sections": normalized_sections,
            }
        )

    return {"globals": normalized_globals, "levels": normalized_levels}


def _read_text_file(text_path: str) -> str | None:
    if not text_path:
        return None
    # Try utf-8 first, then fall back to a permissive decode to avoid crashes.
    try:
        with open(text_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        with open(text_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def _collect_text_examples(content_pairs):
    examples = []
    for text_before, text_after in content_pairs:
        before_value = _read_text_file(text_before)
        after_value = _read_text_file(text_after)
        if before_value and after_value:
            examples.append((before_value, after_value))
    return examples


def _generate_json_response(model, request_content) -> str:
    # Ask Gemini for strict JSON output when supported.
    try:
        response = model.generate_content(
            request_content,
            generation_config={"response_mime_type": "application/json"},
        )
    except TypeError:
        # Backward-compatible fallback for older SDK signatures.
        response = model.generate_content(request_content)

    raw_text = (response.text or "").strip()
    json_text = _extract_json_object(raw_text)
    if not json_text:
        raise ValueError(f"Model response did not contain a JSON object. Raw: {raw_text[:500]}")
    return json_text

def open_image_if_exists(path: str):
    if not path or not os.path.exists(path):
        return None
    try:
        return Image.open(path)
    except Exception:
        return None
def language_to_bridge_visual(user_request, api_key, content_pairs, model_name="gemini-2.5-flash") -> str:
    """
    Converts level language into a text-only visualization while preserving
    the original agent-language shape.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    request_content = []
    examples = _collect_text_examples(content_pairs)

    context = """
    You are converting platformer level language into a VISUALIZED version of
    the SAME agent-language JSON schema. Do not generate any image.

    Keep the original schema and values:
    {
      "globals": {...},
      "levels": [
        {
          "level": <int>,
          "difficulty": <float>,
          "sections": [...]
        }
      ]
    }

    Add visualization hints without changing the existing format:
    - Keep all existing keys and values compatible with the current agent-language format.
    - Add optional text-only visualization fields:
      - level-level field: "visualization_notes": [ ... ]
      - section-level field: "visualization": {
          "mental_image": <short phrase>,
          "layout_pattern": <short phrase>,
          "landmark_hint": <short phrase>
        }
    - If a section already has fields, preserve them and only add visualization fields.
    - Return valid JSON only.
    """
    request_content.append(context)
    for index, (text_before, text_after) in enumerate(examples):
        image = open_image_if_exists(text_after)

        request_content.append(f"\n##Example {index + 1}\n")
        request_content.append(f"Example Input {index + 1}:\n{text_before}\n")
        request_content.append(f"Example Output {index + 1}:\n{image}\n")

    prompt = (
        "\nConvert the following input into the same agent-language JSON plus text-only visualization hints.\n"
        f"Input:\n{user_request}\n"
        "Preserve original structure and values. Return JSON only."
    )
    request_content.append(prompt)

    try:
        json_text = _generate_json_response(model, request_content)
        parsed = json.loads(json_text)
        return json.dumps(parsed, ensure_ascii=True, indent=2)
    except Exception as e:
        return f"API Error: {e}"


def bridge_visual_to_ldtk(bridge_visual_json: str, api_key, model_name="gemini-2.5-flash") -> str:
    """
    Converts text-only visual bridge JSON into LDtk JSON.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    request_content = []

    context = """
    Convert the provided bridge visual JSON into valid LDtk-like level JSON.
    The bridge uses characters:
    . empty, # solid, ^ hazard, S spawn, G goal, C coin, E enemy, M moving platform.

    Requirements:
    - Return valid JSON only.
    - Include a sensible LDtk-style structure with levels, IntGrid values, and entities.
    - Map solid/hazard into IntGrid values and entity symbols into Entities.
    """
    request_content.append(context)
    request_content.append(f"Bridge Visual JSON:\n{bridge_visual_json}")

    try:
        json_text = _generate_json_response(model, request_content)
        parsed = json.loads(json_text)
        return json.dumps(parsed, ensure_ascii=True, indent=2)
    except Exception as e:
        return f"API Error: {e}"





def analyze_multimodal_content(user_request, api_key, content_pairs, model_name="gemini-2.5-flash"):
    """
    Sends multiple image and text pairs to Gemini in a single request.
    
    Args:
        api_key (str): Your Google Gemini API Key.
        content_pairs (list): A list of tuples, e.g., [(image_path1, text1), (image_path2, text2)].
                              You can pass None for text if you just want to stack images.
        model_name (str): The model version to use.
    
    Returns:
        str: The generated text response.
    """
    
    # 1. Configure the API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # 2. Build the request content list
    request_content = []


    context = "The follow is a set of image and json pairs"
    request_content.append(context)


    for index, (img_path, text_path) in enumerate(content_pairs):
        exacple_i = f"\n##Example {index + 1}\n"
        request_content.append(exacple_i)

        # Load the image if a path is provided
        if img_path:
            try:
                img = PIL.Image.open(img_path)
                request_content.append(img)
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                continue
        
        # Append text if provided
        text = _read_text_file(text_path)
        if text:
            request_content.append(text)
    
    prompt = f"\nGiven the examples above, generate the appropriate JSON content for the following request:\n```{user_request}```"
    request_content.append(prompt)
    
    # 3. Send to Gemini
    # The 'generate_content' method handles mixed lists of strings and images automatically
    try:
        response = model.generate_content(request_content)
        return response.text
    except Exception as e:
        return f"API Error: {e}"


def agent_language_to_ldtk_with_internal_sketch(agent_language_json: str, api_key, content_pairs, model_name="gemini-2.5-flash") -> str:
    """
    Uses an internal sketch image + agent-language JSON to produce LDtk JSON.
    """
    parsed_agent_language = _try_parse_agent_language_json(agent_language_json)
    if not parsed_agent_language:
        return "API Error: Invalid agent-language JSON provided to LDtk conversion."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    request_content = []

    request_content.append(
        "The following are image and LDtk JSON examples. Then you will receive an internally generated sketch image "
        "plus a structured agent-language JSON. Convert that input into valid LDtk JSON."
    )

    for index, (img_path, text_path) in enumerate(content_pairs):
        request_content.append(f"\n##Example {index + 1}\n")
        if img_path:
            try:
                request_content.append(PIL.Image.open(img_path))
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                continue
        text = _read_text_file(text_path)
        if text:
            request_content.append(text)

    internal_sketch = _build_internal_sketch_image(parsed_agent_language)
    request_content.append("\n##Target Input (internal sketch + agent language)\n")
    request_content.append(internal_sketch)
    request_content.append(json.dumps(parsed_agent_language, ensure_ascii=True, indent=2))
    request_content.append(
        """
Return only a valid JSON object for LDtk.
Requirements:
- Preserve level order and major section intent.
- Use IntGrid values consistent with tile_value_map.
- Place entities for spawn/goal and relevant gameplay entities when implied.
- Do not include markdown or explanation text.
"""
    )

    try:
        response = model.generate_content(
            request_content,
            generation_config={"response_mime_type": "application/json"},
        )
        raw_text = (response.text or "").strip()
        json_text = _extract_json_object(raw_text)
        if not json_text:
            return f"API Error: Model response did not contain a JSON object. Raw: {raw_text[:500]}"
        parsed = json.loads(json_text)
        return json.dumps(parsed, ensure_ascii=True, indent=2)
    except TypeError:
        try:
            response = model.generate_content(request_content)
            raw_text = (response.text or "").strip()
            json_text = _extract_json_object(raw_text)
            if not json_text:
                return f"API Error: Model response did not contain a JSON object. Raw: {raw_text[:500]}"
            parsed = json.loads(json_text)
            return json.dumps(parsed, ensure_ascii=True, indent=2)
        except Exception as e:
            return f"API Error: {e}"
    except Exception as e:
        return f"API Error: {e}"


def text_to_agent_language(user_request, api_key, content_pairs, model_name="gemini-2.5-flash") -> str:
    """
    Gets plan and converts to agent lanugage that will be converted to ldtk json file later.
    Args:
        api_key (str): Your Google Gemini API Key.
        content_pairs (list): A list of tuples, e.g., [(text1Before, text1After), (text2Before, text2After)].
        model_name (str): The model version to use.
    
    Returns:
        str: The generated text response.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    request_content = []
    examples = _collect_text_examples(content_pairs)
    context = """
    You are converting broad level-design plans into STRICT JSON that will be compiled into LDtk JSON.
    The output must be concrete, non-broad, and machine-readable.

    Allowed section_type values:
    ["start_zone","jump_tutorial","platform_sequence","gap_sequence","moving_platform_tutorial","hazard_zone","branch","timed_challenge_sequence","exploration_zone","end_zone"]

    Branch section requirements:
    - Must include "paths" with at least 2 entries.
    - Each path must include:
      "path_name", "difficulty", "features", "requires", "reward"

    Controlled vocabulary for intent/challenge words:
    - safety: ["high","medium","low"]
    - challenge: ["basic","precision_timing","hazard_avoidance","timing_pressure","complex_hazard_navigation","final_skill_test"]
    - flow: ["smooth","rhythmic","variable"]
    - risk_reward: ["low","medium","high","extreme"]

    Translation rules:
    - Replace vague wording with explicit parameters (counts, ranges, widths, heights, gaps, speeds).
    - Use numeric ranges where relevant (example: "gap":[1,2], "height_variation":[0,1]).
    - Include deterministic placement keys in each section parameters:
      "length_tiles", "start_x_policy", "base_y".
    - Use "count" consistently (not "platform_count").
    - Keep speed in "speed_range": [min,max].
    - Keep "gap" and "height_variation" within player constraints.
    - Keep values feasible for platformers and compatible with LDtk tile/grid placement.
    - Do not output explanations, markdown, code fences, or extra text.
    - Output valid JSON only.
    """
    request_content.append(context)
    for index, (text_before, text_after) in enumerate(examples):
        exacple_i = f"\n##Example {index + 1}\n"
        request_content.append(exacple_i)
        request_content.append(f"Example Input {index + 1}:\n{text_before}\n")
        request_content.append( f"Example Output {index + 1}:\n{text_after}\n")
    prompt = (
        "\nConvert the following request into strict agent-language JSON for LDtk conversion.\n"
        f"Request:\n{user_request}\n"
        "Return ONLY a valid JSON object using the required schema."
    )
    request_content.append(prompt)
    output_format = """Required output schema (JSON object only):
    {
      "globals": {
        "grid_size": 8,
        "rng_seed": <int>,
        "player_constraints": {
          "max_jump_distance_tiles": <int>,
          "max_jump_height_tiles": <int>,
          "double_jump": <bool>
        },
        "tile_value_map": {"empty":0,"solid":1,"hazard":2},
        "entity_types": {
          "player_spawn":"PlayerSpawn",
          "goal":"Goal",
          "enemy_patrol":"EnemyPatrol",
          "coin":"Coin",
          "powerup":"Powerup",
          "hazard_spike":"HazardSpike"
        }
      },
      "levels": [
        {
          "level": <int>,
          "difficulty": <float 1-10>,
          "sections": [
            {
              "type": "<section_type>",
              "target_layer": "IntGrid_layer|Entities",
              "parameters": { ... },
              "intent": { ... },
              "requires": [ ... ]
            }
          ]
        }
      ]
    }
"""
    request_content.append(output_format)

    #


    try:
        json_text = _generate_json_response(model, request_content)
        parsed = json.loads(json_text)
        normalized = _normalize_agent_language_schema(parsed)
        return json.dumps(normalized, ensure_ascii=True, indent=2)
    except Exception as e:
        return f"API Error: {e}"
def LDTKGenerator(image_path: str) -> str:
    # Accept image paths directly or embedded in surrounding text.
    extracted_image_path = _extract_existing_image_path(image_path)
    if extracted_image_path:
        ldtk_json = image_to_ldtk_with_examples(
            target_image_path=extracted_image_path,
            api_key=API_KEY,
            content_pairs=ef.my_data,
            model_name="gemini-2.5-flash",
        )
    else:
        # Otherwise convert request to agent language and process each level image separately.
        parsed_direct = _try_parse_agent_language_json(image_path)
        if parsed_direct:
            agent_language_json = json.dumps(
                _normalize_agent_language_schema(parsed_direct),
                ensure_ascii=True,
                indent=2,
            )
        else:
            agent_language_json = convert_to_agent_language(image_path)
            if isinstance(agent_language_json, str) and agent_language_json.startswith("API Error:"):
                return agent_language_json

        ldtk_json = _agent_language_to_ldtk_by_level_images(
            agent_language_json=agent_language_json,
            api_key=API_KEY,
            content_pairs=ef.my_data,
            model_name="gemini-2.5-flash",
        )
    if isinstance(ldtk_json, str) and ldtk_json.startswith("API Error:"):
        return ldtk_json

    try:
        zip_path = _write_ldtk_zip(ldtk_json)
        return f"LDtk zip created at: {zip_path}"
    except Exception as e:
        return f"API Error: Failed to write LDtk zip: {e}"
    

def convert_to_agent_language(game_level_description: str) -> str:
    return text_to_agent_language(user_request=game_level_description, api_key=API_KEY, content_pairs=ef.wordy_agentLanguage, model_name="gemini-2.5-flash")


def convert_to_bridge_visual(game_level_description: str) -> str:
    return language_to_bridge_visual(
        user_request=game_level_description,
        api_key=API_KEY,
        content_pairs=ef.bridge_data,
        model_name="gemini-2.5-flash",
    )

def AgentLanguageConverter(game_level_description: str) -> str:
    """
    Converts a wordy level design request into concise agent language.
    This tool can be called directly for testing without running the full workflow.
    """
    return convert_to_agent_language(game_level_description)


def BridgeDataConverter(game_level_description: str) -> str:
    """
    Converts input into agent-language, renders a bridge image, and returns the image path.
    """
    parsed_direct = _try_parse_agent_language_json(game_level_description)
    if parsed_direct:
        agent_language_json = json.dumps(
            _normalize_agent_language_schema(parsed_direct),
            ensure_ascii=True,
            indent=2,
        )
    else:
        agent_language_json = convert_to_agent_language(game_level_description)
        if isinstance(agent_language_json, str) and agent_language_json.startswith("API Error:"):
            return agent_language_json

    try:
        image_paths = _write_bridge_images_from_agent_language(agent_language_json)
        return "Bridge images created at:\n" + "\n".join(image_paths)
    except Exception as e:
        return f"API Error: Failed to create bridge image: {e}"

