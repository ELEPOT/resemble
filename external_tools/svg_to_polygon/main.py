import pathlib
import os

from svgelements import SVG, Path, Shape, Line, Move, Close, PathSegment, Arc
import numpy as np


class PolyObject:
    points: np.typing.NDArray = []
    closed: bool = False


ALLOW_CURVATURE = 5e-4
SAMPLE_DETAIL = 2

def normalize(arr):
    return arr / np.linalg.norm(arr)

def format_tscn_properties(value):
    if isinstance(value, int | float):
        return str(float(value))
    return value

def svg_to_tscn_snippet(svg_path: pathlib.Path | str, extra_properties: dict = {}) -> str:
    result: SVG = SVG.parse(pathlib.Path(svg_path))

    poly_objects: list[PolyObject] = []

    for element in result.elements():
        if not isinstance(element, Path | Shape):
            continue

        svg_path = Path(element)

        curr_poly: PolyObject | None = None

        for segment in svg_path.segments():
            # print(segment, type(segment))
            if isinstance(segment, Move):
                curr_poly = PolyObject()
                poly_objects.append(curr_poly)
                curr_poly.points = np.array([segment.end])

            elif isinstance(segment, Close):
                if (curr_poly.points[0] == curr_poly.points[-1]).all():
                    curr_poly.points = curr_poly.points[:-1]
                curr_poly.closed = True

            elif isinstance(segment, Line):
                curr_poly.points = np.append(
                    curr_poly.points, np.array([segment.end]), axis=0
                )

            elif isinstance(segment, PathSegment):
                sampled_points = np.array([segment.start])
                curr_sample_x = 0
                min_detail = SAMPLE_DETAIL / segment.length()

                while 1 - curr_sample_x > 1e-5:
                    detail = min(min_detail, 1 - curr_sample_x)
                    while True:
                        a = segment.point(curr_sample_x + detail / 2)
                        b = segment.point(curr_sample_x + detail)


                        if 1 - np.dot(normalize(a - sampled_points[-1]), normalize(b - a)) < ALLOW_CURVATURE:
                            break

                        detail /= 1.5

                    sampled_points = np.append(sampled_points, np.array([segment.point(curr_sample_x + detail)]), axis=0)
                    curr_sample_x += detail

                curr_poly.points = np.append(curr_poly.points, sampled_points[1:], axis=0)

    formatted_properties = "".join([f"{key} = {format_tscn_properties(value)}\n" for key, value in extra_properties.items()])

    return "".join([
        f"""[node name="Segment{"" if i == 0 else i + 1}" type="Line2D" parent="Node2D"]\n"""
        f"""points = PackedVector2Array({', '.join(map(str, obj.points.flatten().tolist()))})\n"""
        f"""{"closed = true" if obj.closed else ""}\n"""
        + formatted_properties
        for i, obj in enumerate(poly_objects)])


if __name__ == "__main__":
    input_dir = pathlib.Path("svg_src")
    output_dir = pathlib.Path("output")

    header = (
        """[gd_scene format=3 uid="uid://yo3cb6lo0jqa"]\n\n"""
        """[node name="Circle" type="Node2D" unique_id=1663784699]\n\n"""
    )

    extra_properties = {
        "width": 1.0
    }

    if not output_dir.exists():
        output_dir.mkdir()

    for filename in os.listdir("svg_src"):
        in_path = pathlib.Path(input_dir / filename)
        out_path = pathlib.Path(output_dir / filename).with_suffix(".tscn")
        if in_path.suffix != '.svg':
            continue

        with open(out_path, "w") as out_file:
            print(out_path)
            out_file.write(header + svg_to_tscn_snippet(in_path, extra_properties))

