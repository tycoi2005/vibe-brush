import json
import base64
import struct
import argparse
import os

def convert_json_to_obj(input_json: str, output_obj: str):
    """Converts Open Brush raw JSON export into a standard OBJ 3D model."""
    print(f"Reading {input_json}...")
    with open(input_json, "r") as f:
        data = json.load(f)

    if "strokes" not in data:
        print("Error: 'strokes' key not found in JSON. Are you sure this is an Open Brush raw JSON export?")
        return

    strokes = data["strokes"]
    print(f"Found {len(strokes)} strokes.")

    # OBJ indices are 1-based and cumulative across the entire file
    vertex_offset = 1
    total_vertices = 0
    total_faces = 0

    with open(output_obj, "w") as out:
        out.write("# Open Brush JSON to OBJ Converter\n")
        out.write(f"# Source: {os.path.basename(input_json)}\n\n")

        for stroke_idx, stroke in enumerate(strokes):
            out.write(f"o Stroke_{stroke_idx}\n")
            
            # --- Vertices & Colors ---
            if "v" not in stroke:
                print(f"  Warning: Stroke {stroke_idx} has no 'v' (vertices), skipping.")
                continue
                
            v_raw = base64.b64decode(stroke["v"])
            num_verts = len(v_raw) // 12  # 3 floats (x,y,z) * 4 bytes = 12 bytes per vertex
            verts_floats = struct.unpack(f"<{num_verts * 3}f", v_raw)
            
            # Extract colors if available (Open Brush stores 4 bytes RGBA per vertex)
            colors = []
            if "c" in stroke:
                c_raw = base64.b64decode(stroke["c"])
                if len(c_raw) == num_verts * 4:
                    c_bytes = struct.unpack(f"<{num_verts * 4}B", c_raw)
                    for i in range(num_verts):
                        r = c_bytes[i*4] / 255.0
                        g = c_bytes[i*4+1] / 255.0
                        b = c_bytes[i*4+2] / 255.0
                        colors.append((r, g, b))

            # Write vertices
            for i in range(num_verts):
                x = verts_floats[i*3]
                y = verts_floats[i*3 + 1]
                z = verts_floats[i*3 + 2]
                
                # Convert from Unity's Left-Handed coordinates to standard Right-Handed coordinates
                # by flipping the Z axis:
                z = -z
                
                if colors:
                    r, g, b = colors[i]
                    out.write(f"v {x:.6f} {y:.6f} {z:.6f} {r:.3f} {g:.3f} {b:.3f}\n")
                else:
                    out.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")

            total_vertices += num_verts

            # --- Triangles (Faces) ---
            if "tri" in stroke:
                tri_raw = base64.b64decode(stroke["tri"])
                
                # Check whether indices are 16-bit or 32-bit
                if len(tri_raw) % 4 == 0:
                    num_indices = len(tri_raw) // 4
                    indices = struct.unpack(f"<{num_indices}I", tri_raw)
                elif len(tri_raw) % 2 == 0:
                    num_indices = len(tri_raw) // 2
                    indices = struct.unpack(f"<{num_indices}H", tri_raw)
                else:
                    print(f"  Warning: Stroke {stroke_idx} triangle buffer has invalid length, skipping faces.")
                    indices = []
                
                # Write faces. Because we flipped the Z axis, we must also reverse the triangle 
                # winding order (idx1, idx3, idx2) so polygons face the correct way out.
                for i in range(0, len(indices), 3):
                    idx1 = indices[i] + vertex_offset
                    idx2 = indices[i+1] + vertex_offset
                    idx3 = indices[i+2] + vertex_offset
                    
                    out.write(f"f {idx1} {idx3} {idx2}\n")
                    total_faces += 1
            
            # Increase the global vertex index offset for the next stroke
            vertex_offset += num_verts
            out.write("\n")

    print(f"Success! Wrote {total_vertices} vertices and {total_faces} faces to {output_obj}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Open Brush .json to .obj")
    parser.add_argument("input", help="Path to the Open Brush .json file")
    parser.add_argument("output", help="Path to save the resulting .obj file", nargs="?")
    args = parser.parse_args()

    out_path = args.output
    if not out_path:
        out_path = os.path.splitext(args.input)[0] + ".obj"

    convert_json_to_obj(args.input, out_path)
